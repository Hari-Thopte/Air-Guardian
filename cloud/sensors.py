"""IoT-rule-only entry point. deviceId comes from topic(2), not an HTTP request."""
import hashlib
import os
import time
from backend.functions.air_engine import timestamp
from cloud.contracts import identifier, number, integer, Problem
from cloud.policy import sensor_quality
from cloud.store import DynamoStore, change, Conflict


def ingest_sensor(store, readings, data, now=None):
    now = time.time() if now is None else now
    device = store.get('DEVICES', identifier(data.get('deviceId')))
    if not device or not device['active']:
        raise Problem('Device is not registered or active.', 403)
    observed = timestamp(data.get('observedAt'))
    if observed is None or not -60 <= now - observed <= 86400:
        raise Problem('Telemetry timestamp is outside the one-day replay window.')
    pm = number(data.get('pm25'), 'PM2.5', 0, 2000)
    humidity = number(data.get('humidity'), 'Humidity', 0, 100)
    samples = integer(data.get('sampleCount'), 'Sample count', 1, 100000)
    sequence = integer(data.get('sequence'), 'Sequence', 0, 2147483647)
    pk = 'SCHOOL#' + device['school']; key = 'SENSOR#' + device['id']
    previous = store.get(pk, key)
    reading = {'deviceId': device['id'], 'school': device['school'], 'location': device['location'],
               'room_id': device['room_id'], 'observedAt': data['observedAt'], 'pm25': pm, 'humidity': humidity,
               'sampleCount': samples, 'sequence': sequence, 'lastSeen': now, 'source': 'Experimental school sensor'}
    reading.update(sensor_quality(reading, previous, now))
    same_since = previous.get('sameSince', now) if previous and previous.get('pm25') == pm else now
    reading['sameSince'] = same_since
    if now - same_since > 6 * 3600:
        reading['quality'] = 'review'; reading['qualityReasons'].append('PM2.5 unchanged for more than six hours')
    rid = hashlib.sha256(f"{device['id']}:{observed}:{sequence}".encode()).hexdigest()
    rpk = pk + '#SENSOR#' + device['id']
    if not readings.get(rpk, rid):
        try:
            readings.commit([change(rpk, rid, reading, expires=now + 30 * 86400)])
        except Conflict:
            pass
    if previous and observed <= timestamp(previous['observedAt']):
        return {'status': 'duplicate-or-buffered', 'quality': reading['quality']}
    store.commit([change(pk, key, reading, previous)])
    return {'status': 'received', 'quality': reading['quality']}


def handler(event, context):
    return ingest_sensor(DynamoStore(), DynamoStore(os.environ['READINGS_TABLE']), event)
