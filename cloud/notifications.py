"""At-least-once delivery with durable per-device receipts, leases, caps and preference checks."""
import json
import os
import time
from cloud.contracts import DEFAULT_PREFS, local_day, quiet
from cloud.store import DynamoStore, change, Conflict
from cloud.messages import role_message
from cloud.channels import send_sms, send_whatsapp, enabled_channels


def send_push(subscription, message):
    from pywebpush import webpush, WebPushException
    import boto3
    path = os.environ.get('VAPID_PRIVATE_PARAMETER')
    if not path:
        return 'not-configured'
    key = boto3.client('ssm').get_parameter(Name=path, WithDecryption=True)['Parameter']['Value']
    try:
        webpush(subscription_info=subscription, data=json.dumps({'title': 'Air Guardian school update',
                'body': message, 'url': '/cloud.html'}), vapid_private_key=key,
                vapid_claims={'sub': os.environ['VAPID_SUBJECT']}, ttl=1800, timeout=10)
        return 'accepted-by-push-service'
    except WebPushException as error:
        if error.response is not None and error.response.status_code in (404, 410):
            return 'subscription-expired'
        raise RuntimeError('Push service did not accept this request') from None


def send_email(address, message):
    import boto3
    sender = os.environ.get('SES_FROM')
    if not sender:
        return 'not-configured'
    result = boto3.client('sesv2').send_email(FromEmailAddress=sender, Destination={'ToAddresses': [address]},
        **({'ConfigurationSetName': os.environ['SES_CONFIG_SET']} if os.environ.get('SES_CONFIG_SET') else {}),
        Content={'Simple': {'Subject': {'Data': 'Air Guardian school update'},
                           'Body': {'Text': {'Data': message + '\nOpen your school workspace to review the current plan.'}}}})
    return {'status': 'accepted-by-email-service', 'providerId': result['MessageId']}


def deliver(store, event, push=send_push, email=send_email, now=None, subject=None):
    now = time.time() if now is None else now
    sid = event['school']; pk = 'SCHOOL#' + sid
    school = store.get(pk, 'CONFIG')
    if not school or not school.get('active') or event['expiresAt'] <= now:
        return
    if event['kind'] in ('admin-announcement','plan-reminder'):
        latest = store.get(pk, 'NOTICE')
        if not latest or latest['id'] != event.get('planId',event['id']):
            return
    memberships = [store.get(pk, 'MEMBER#' + subject)] if subject else store.query(pk, 'MEMBER#', limit=500)
    for membership in memberships:
        if not membership:
            continue
        if not membership['active'] or membership['role']=='kid':
            continue
        if event.get('audience') is not None and membership['sub'] not in {p['sub'] for p in event['audience']}:
            continue
        sub = membership['sub']; upk = 'USER#' + sub
        if store.get('ACCOUNT_ERASURE', sub):
            continue
        prefs = {**DEFAULT_PREFS, **(store.get(upk, 'PREFERENCES') or {})}
        message = role_message(event, membership['role'], prefs['language'])
        for channel in prefs['channels']:
            if channel not in enabled_channels():
                continue
            # Re-read immediately before dispatch so revoked memberships are not acted on from a stale list.
            current_member = store.get(pk, 'MEMBER#' + sub)
            if not current_member or not current_member['active'] or store.get('ACCOUNT_ERASURE', sub):
                continue
            targets = [('in-app', None)] if channel == 'in-app' else []
            if channel == 'push':
                targets = [(r['_sk'], r) for r in store.query(upk, 'PUSH#', limit=5)]
            if channel == 'email':
                contact = store.get(upk, 'CONTACT')
                targets = [('email', contact)] if contact and contact.get('email') and not contact.get('emailSuppressed') else []
            if channel in ('sms', 'whatsapp'):
                contact = store.get(upk, 'CONTACT')
                targets = [(channel, contact)] if contact and contact.get('phone') else []
            for target, target_data in targets:
                key = f"DELIVERY#{sid}#{event['time']:016.3f}#{event['id']}#{channel}#{target}"
                old = store.get(upk, key)
                if old and old['status'] not in ('pending', 'failed'):
                    continue
                if old and old.get('leaseUntil', 0) > now:
                    raise RuntimeError('Delivery is leased by another attempt')
                status = 'pending'
                if channel != 'in-app' and quiet(prefs, school, now):
                    status = 'suppressed-quiet-hours'
                if event['kind'] == 'morning-plan' and not prefs['morning']:
                    status = 'suppressed-preference'
                capkey = f'CAP#{sid}#{local_day(school, now)}#{channel}'
                cap = store.get(upk, capkey)
                count = (cap or {}).get('count', 0)
                quota_key = f"QUOTA#{sid}#{local_day(school, now)}#{event['id']}#{channel}"
                reserved = store.get(upk, quota_key)
                if count >= prefs['dailyCap'] and not reserved:
                    status = 'suppressed-daily-cap'
                value = {'eventId': event['id'], 'school': sid, 'channel': channel, 'status': status,
                         'language':prefs['language'], 'audienceRole':membership['role'],
                         'createdAt': now, 'leaseUntil': now + 150, 'attempts': (old or {}).get('attempts', 0) + 1}
                if value['attempts'] > 5:
                    raise RuntimeError('Delivery retry limit reached; inspect dead-letter queue')
                changes = [change(upk, key, value, old, now + 30 * 86400)]
                if status == 'pending' and not reserved:
                    changes.append(change(upk, capkey, {'count': count + 1}, cap, now + 3 * 86400))
                    changes.append(change(upk, quota_key, {'eventId': event['id']}, expires=now + 3 * 86400))
                store.commit(changes)
                if status != 'pending':
                    continue
                try:
                    if channel == 'in-app':
                        accepted = 'in-app'
                    elif channel == 'push':
                        accepted = push(target_data['subscription'], message)
                    elif channel == 'email':
                        accepted = email(target_data['email'], message)
                    elif channel == 'sms':
                        accepted = send_sms(target_data['phone'], event)
                    else:
                        accepted = send_whatsapp(target_data['phone'], event)
                    status = accepted['status'] if isinstance(accepted, dict) else accepted
                except Exception:
                    current = store.get(upk, key)
                    store.commit([change(upk, key, dict(current, status='failed', leaseUntil=0), current, now + 30 * 86400)])
                    raise RuntimeError('A notification channel failed; delivery will retry') from None
                current = store.get(upk, key)
                changes = [change(upk, key, dict(current, status=status, leaseUntil=0), current, now + 30 * 86400)]
                if isinstance(accepted, dict) and accepted.get('providerId'):
                    changes[0]['value']['providerId'] = accepted['providerId']
                    changes.append(change('PROVIDER_MESSAGES', channel + '#' + accepted['providerId'],
                                          {'pk': upk, 'sk': key}, expires=now + 30 * 86400))
                if status == 'subscription-expired':
                    changes.append(change(upk, target, None, target_data))
                store.commit(changes)


from cloud.observability import observed


@observed
def handler(event, context):
    store = DynamoStore()
    failures = []
    for record in event.get('Records', []):
        try:
            payload = json.loads(record['body'])
            deliver(store, payload['event'], subject=payload['sub'])
        except Exception as error:
            print(json.dumps({'event': 'delivery-failed', 'type': type(error).__name__}))
            failures.append({'itemIdentifier': record['messageId']})
    return {'batchItemFailures': failures}
