"""Delivery events from an AWS-authenticated SNS invocation; no public webhook endpoint."""
import json
import os
import time
from cloud.store import DynamoStore, change


def parse(payload):
    kind = payload.get('eventType', payload.get('notificationType', ''))
    if payload.get('mail', {}).get('messageId'):
        mapping = {'Delivery': 'delivered', 'Bounce': 'bounced', 'Complaint': 'complaint',
                   'DELIVERY': 'delivered', 'BOUNCE': 'bounced', 'COMPLAINT': 'complaint'}
        if kind in mapping:
            return [('email', payload['mail']['messageId'], mapping[kind])]
    if payload.get('messageId') and kind.startswith('TEXT_'):
        mapping = {'TEXT_DELIVERED': 'delivered', 'TEXT_SENT': 'sent',
                   'TEXT_QUEUED': 'sent', 'TEXT_PENDING': 'sent',
                   'TEXT_INVALID': 'provider-failed', 'TEXT_INVALID_MESSAGE': 'provider-failed',
                   'TEXT_UNREACHABLE': 'provider-failed', 'TEXT_CARRIER_UNREACHABLE': 'provider-failed',
                   'TEXT_BLOCKED': 'provider-failed', 'TEXT_CARRIER_BLOCKED': 'provider-failed',
                   'TEXT_SPAM': 'provider-failed', 'TEXT_TTL_EXPIRED': 'provider-failed',
                   'TEXT_UNKNOWN': 'provider-failed'}
        return [('sms', payload['messageId'], mapping[kind])] if kind in mapping else []
    raw = payload.get('whatsAppWebhookEntry')
    if raw:
        body = json.loads(raw) if isinstance(raw, str) else raw
        results = []
        for entry in body.get('entry', [body]):
            for item in entry.get('changes', []):
                for status in item.get('value', {}).get('statuses', []):
                    if status.get('status') in ('sent', 'delivered', 'read', 'failed'):
                        results.append(('whatsapp', status['id'], 'provider-failed' if status['status'] == 'failed' else status['status']))
        return results
    return []


def apply_feedback(store, channel, provider_id, status):
    link = store.get('PROVIDER_MESSAGES', channel + '#' + provider_id)
    if not link:
        # A very fast callback may precede saving the provider ID; let SNS retry.
        raise RuntimeError('Delivery mapping is not available yet')
    row = store.get(link['pk'], link['sk'])
    if not row:
        return
    rank = {'sent': 2, 'delivered': 3, 'read': 4, 'provider-failed': 2, 'bounced': 5, 'complaint': 6}
    if rank.get(row['status'], 1) >= rank[status]:
        return
    now = time.time()
    changes = [change(link['pk'], link['sk'], dict(row, status=status, receiptAt=now), row, now + 30 * 86400)]
    if channel == 'email' and status in ('bounced', 'complaint'):
        contact = store.get(link['pk'], 'CONTACT')
        if contact:
            changes.append(change(link['pk'], 'CONTACT', dict(contact, emailSuppressed=True), contact))
    store.commit(changes)


def handler(event, context):
    store = DynamoStore()
    for record in event.get('Records', []):
        sns = record.get('Sns', {})
        if sns.get('TopicArn') != os.environ['FEEDBACK_TOPIC']:
            raise ValueError('Unexpected feedback source')
        for channel, provider_id, status in parse(json.loads(sns['Message'])):
            apply_feedback(store, channel, provider_id, status)
    return {'processed': True}
