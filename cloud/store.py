"""Explicit document operations with optimistic transactions. JSON payloads avoid float conversion.

No table scans: memberships, schools, history and outbox have explicit partitions.
MemoryStore is dependency-injected only in tests; deployed handlers always use DynamoDB.
"""
import copy
import json
import os
import time


class Conflict(Exception):
    pass


def change(pk, sk, value, previous=None, expires=None):
    return {'pk': pk, 'sk': sk, 'value': value, 'revision': previous['_rev'] if previous else 0, 'expires': expires}


class DynamoStore:
    def __init__(self, table=None):
        import boto3
        self.client = boto3.client('dynamodb')
        self.table = table or os.environ['APP_TABLE']

    @staticmethod
    def decode(item):
        if not item or int(item.get('expires', {'N': '9999999999'})['N']) <= time.time():
            return None
        return {**json.loads(item['payload']['S']), '_rev': int(item['revision']['N'])}

    def get(self, pk, sk):
        return self.decode(self.client.get_item(TableName=self.table, Key={'pk': {'S': pk}, 'sk': {'S': sk}}, ConsistentRead=True).get('Item'))

    def query(self, pk, prefix='', reverse=False, limit=1000):
        args = {'TableName': self.table, 'KeyConditionExpression': 'pk = :pk AND begins_with(sk, :prefix)',
                'ExpressionAttributeValues': {':pk': {'S': pk}, ':prefix': {'S': prefix}},
                'ConsistentRead': True, 'ScanIndexForward': not reverse, 'Limit': min(limit, 1000)}
        if not prefix:
            args['KeyConditionExpression'] = 'pk = :pk'
            del args['ExpressionAttributeValues'][':prefix']
        result = []
        while True:
            page = self.client.query(**args)
            for item in page.get('Items', []):
                value = self.decode(item)
                if value is not None:
                    result.append(dict(value, _sk=item['sk']['S']))
                    if len(result) >= limit:
                        return result
            if not page.get('LastEvaluatedKey'):
                return result
            args['ExclusiveStartKey'] = page['LastEvaluatedKey']

    def commit(self, changes):
        items = []
        for c in changes:
            base = {'TableName': self.table, 'ConditionExpression': 'attribute_not_exists(pk)' if c['revision'] == 0 else 'revision = :r'}
            if c['revision']:
                base['ExpressionAttributeValues'] = {':r': {'N': str(c['revision'])}}
            if c['value'] is None:
                items.append({'Delete': {**base, 'Key': {'pk': {'S': c['pk']}, 'sk': {'S': c['sk']}}}})
            else:
                payload = {k: v for k, v in c['value'].items() if not k.startswith('_')}
                item = {'pk': {'S': c['pk']}, 'sk': {'S': c['sk']}, 'revision': {'N': str(c['revision'] + 1)},
                        'payload': {'S': json.dumps(payload, allow_nan=False, separators=(',', ':'))}}
                if c.get('expires'):
                    item['expires'] = {'N': str(int(c['expires']))}
                items.append({'Put': {**base, 'Item': item}})
        if not items:
            return
        try:
            self.client.transact_write_items(TransactItems=items)
        except self.client.exceptions.TransactionCanceledException as error:
            if any(r.get('Code') == 'ConditionalCheckFailed' for r in error.response.get('CancellationReasons', [])):
                raise Conflict('Record changed; refresh and retry.') from None
            raise


class MemoryStore:
    def __init__(self):
        self.rows = {}

    def get(self, pk, sk):
        row = self.rows.get((pk, sk))
        return copy.deepcopy(row[0]) if row and (not row[1] or row[1] > time.time()) else None

    def query(self, pk, prefix='', reverse=False, limit=1000):
        values = []
        for p, s in sorted(self.rows, reverse=reverse):
            if p == pk and s.startswith(prefix):
                value = self.get(p, s)
                if value is not None:
                    values.append(dict(value, _sk=s))
        return values[:limit]

    def commit(self, changes):
        if len({(c['pk'], c['sk']) for c in changes}) != len(changes):
            raise ValueError('Duplicate transaction keys')
        for c in changes:
            # Match DynamoDB: expired rows remain until deletion and still participate in CAS.
            old = self.rows.get((c['pk'], c['sk']))
            if (old[0]['_rev'] if old else 0) != c['revision']:
                raise Conflict('Record changed; refresh and retry.')
        for c in changes:
            key = (c['pk'], c['sk'])
            if c['value'] is None:
                self.rows.pop(key, None)
            else:
                self.rows[key] = ({**copy.deepcopy(c['value']), '_rev': c['revision'] + 1}, c.get('expires'))


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if not k.startswith('_')}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value
