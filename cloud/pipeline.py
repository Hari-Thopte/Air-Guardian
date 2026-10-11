"""Scheduled ingestion, durable current state/history, forecast snapshots and outbox."""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from backend.functions.air_engine import timestamp, iso
from cloud import providers
from cloud.contracts import local_day
from cloud.policy import plan
from cloud.planning_tools import stabilize
from cloud.store import DynamoStore, change, Conflict, public


def emit_changes(store, school_id, event, now):
    pk = 'SCHOOL#' + school_id
    event_key = f"EVENT#{int(event['time'] * 1000):013d}#{event['id']}"
    return [change(pk, event_key, event, expires=now + 90 * 86400),
            change('OUTBOX', school_id + '#' + event['id'], {'school': school_id, 'event': event,
                    'queued': False, 'createdAt': now}, expires=now + 2 * 86400)]


def ingest(store, readings, school, air, now=None, morning=False):
    now = time.time() if now is None else now
    pk = 'SCHOOL#' + school['id']
    latest = store.get(pk, 'CURRENT')
    observed = timestamp(air.get('observedAt'))
    old_observed = timestamp((latest or {}).get('air', {}).get('observedAt'))
    # Failed refresh changes health, not the observation time. Old data becomes stale on every read.
    if observed is None and latest:
        air = dict(latest['air'], stale=True, cached=True, providers=air.get('providers', []), lastAttemptAt=iso(now))
    elif observed is not None and old_observed is not None and observed < old_observed:
        return {'status': 'ignored-older-observation'}
    result = plan(air, school, now=now)
    stability=stabilize((latest or {}).get('stability'),result['flag'],observed,air.get('pm25'))
    oid = providers.observation_id(air)
    if observed and air.get('retentionApproved') and not air.get('stale'):
        day = datetime.fromtimestamp(observed, timezone.utc).date().isoformat()
        rpk, rsk = pk + '#' + day, f'READING#{int(observed):010d}#{oid}'
        if not readings.get(rpk, rsk):
            try:
                readings.commit([change(rpk, rsk, {'id': oid, 'school': school['id'], 'observedAt': air['observedAt'],
                   'source': air['source'], 'pm25': air['pm25'], 'pm10': air.get('pm10'), 'standard': air['standard'],
                   'kind': 'model' if all(s.get('kind') == 'model' for s in air['stations']) else 'station-estimate',
                   'unit': 'µg/m³', 'policyVersion': result['policyVersion'], 'retrievedAt': air['fetchedAt']}, expires=now + 90 * 86400)])
            except Conflict:
                pass
    state = store.get(pk, 'ALERTSTATE')
    day = local_day(school, now)
    count = (state or {}).get('count', 0) if (state or {}).get('day') == day else 0
    flag = stability['flag']
    event = None
    if flag != 'unknown' and count < 4 and ((morning and (state or {}).get('morningDay') != day) or
                                           (not morning and flag != (state or {}).get('flag'))):
        # A current-plan morning digest, not a fabricated forecast alert.
        eid = f"{int(now * 1000)}-{oid}"
        event = {'id': eid, 'school': school['id'], 'time': now, 'flag': flag, 'mode': 'live',
                 'kind': 'morning-plan' if morning else 'threshold-change', 'reasons': result['reasons'],
                 'expiresAt': now + 3600, 'policyVersion': result['policyVersion']}
    changes = [change(pk, 'CURRENT', {'air': air, 'planning': result, 'stability':stability, 'lastAttemptAt': now,
                 'lastSuccessfulAt': now if not air.get('stale') else (latest or {}).get('lastSuccessfulAt')}, latest)]
    if event:
        changes.extend(emit_changes(store, school['id'], event, now))
        changes.append(change(pk, 'ALERTSTATE', {'flag': flag, 'day': day, 'count': count + 1,
                      'morningDay': day if morning else (state or {}).get('morningDay')}, state))
    store.commit(changes)
    # Store issued/retrieved forecast separately for later evaluation. Do not call retrieval time issue time.
    if air.get('forecast') and air.get('retentionApproved'):
        fkey = 'FORECAST#' + datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H')
        if not readings.get(pk, fkey):
            try:
                readings.commit([change(pk, fkey, {'retrievedAt': iso(now), 'issuedAt': None,
                    'source': air['forecastSource'], 'points': air['forecast']}, expires=now + 30 * 86400)])
            except Conflict:
                pass
    return {'status': 'updated', 'flag': flag, 'eventId': event['id'] if event else None}


def history(readings, school_id, days=7, now=None):
    now = time.time() if now is None else now
    start = now - days * 86400
    today = datetime.fromtimestamp(now, timezone.utc).date()
    rows = []
    for n in range(days + 1):
        rows.extend(readings.query('SCHOOL#' + school_id + '#' + (today - timedelta(days=n)).isoformat(), 'READING#', limit=2000))
    rows = sorted((public(r) for r in rows if start <= timestamp(r['observedAt']) <= now), key=lambda r: r['observedAt'])
    # Separate by source and day; never make gaps or source switches look continuous.
    groups = {}
    for row in rows:
        key = (row['observedAt'][:10], row['source'])
        groups.setdefault(key, []).append(row)
    summaries = [{'day': day, 'source': source, 'samples': len(values),
                  'sampleMeanPm25': round(sum(v['pm25'] for v in values) / len(values), 2),
                  'hoursObserved': len({v['observedAt'][:13] for v in values}),
                  'label': 'Mean of available observations, not an official daily AQI'}
                 for (day, source), values in sorted(groups.items())]
    return {'days': days, 'readings': rows, 'daily': summaries, 'coverageMeaning': 'Missing hours are unknown. Series are separated by source.'}


from cloud.observability import observed


@observed
def handler(event, context):
    store, readings = DynamoStore(), DynamoStore(os.environ['READINGS_TABLE'])
    credentials = providers.secrets()
    failures = 0
    for registry in store.query('SCHOOLS', 'SCHOOL#', limit=50):
        school = store.get('SCHOOL#' + registry['id'], 'CONFIG')
        if not school or not school.get('active'):
            continue
        now = time.time()
        local = datetime.fromtimestamp(now, ZoneInfo(school['timezone']))
        try:
            air = providers.fetch(school, credentials, store=store)
            try:
                air['weather'] = providers.weather(school, store)
            except Exception:
                air['weather'] = {'source': 'Unavailable'}
            ingest(store, readings, school, air, now, morning=local.hour == 6 and 30 <= local.minute < 45)
            from cloud.deadline import nudge_changes
            nudges=nudge_changes(store,school,plan(air,school,now=now),now)
            if nudges:
                store.commit(nudges)
            if air.get('stale'):
                from cloud.observability import stale_metric
                stale_metric()
                failures += 1
        except Conflict:
            failures += 1
        except Exception:
            # No provider URLs, credentials, school names or child data in logs.
            failures += 1
    print(json.dumps({'event': 'ingestion-completed', 'failures': failures}))
    if failures:
        raise RuntimeError('One or more school ingestions failed; inspect current source health.')
    return {'ok': True}


def relay(event, context):
    import boto3
    store = DynamoStore()
    from cloud.privacy import erase_private
    for job in store.query('ERASURE', limit=50):
        erase_private(store, job)
    client = boto3.client('sqs')
    count = 0
    for row in store.query('OUTBOX', limit=500):
        if row.get('queued'):
            continue
        if row['event']['expiresAt'] <= time.time():
            store.commit([change('OUTBOX', row['_sk'], None, row)])
            continue
        for membership in store.query('SCHOOL#' + row['school'], 'MEMBER#', limit=500):
            audience=row['event'].get('audience')
            if membership['active'] and (audience is None or membership['sub'] in {p['sub'] for p in audience}):
                client.send_message(QueueUrl=os.environ['DELIVERY_QUEUE'], MessageBody=json.dumps(
                    {'school': row['school'], 'event': row['event'], 'sub': membership['sub']}))
        # Crash between send and mark can duplicate SQS work; worker deduplicates delivery records.
        try:
            store.commit([change('OUTBOX', row['_sk'], None, row)])
        except Conflict:
            pass
        count += 1
    return {'queued': count}
