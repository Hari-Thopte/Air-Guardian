"""Provider boundary: independent indices never enter concentration interpolation.

Retention must be explicitly enabled for keyed providers after reviewing their terms.
CAMS is the default non-commercial pilot feed. Secrets are fetched from SSM.
"""
import hashlib
import json
import os
import time
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from backend.functions import air_engine as engine
from cloud.store import change
from cloud.contracts import Problem


def reserve_requests(store, provider, cost=1, limit=2000):
    """Conservative request reservation; failed calls still consume the budget."""
    day = datetime.now(ZoneInfo('UTC')).date().isoformat()
    key = provider + '#' + day
    previous = store.get('PROVIDER_QUOTAS', key)
    count = (previous or {}).get('count', 0)
    if count + cost > limit:
        raise Problem('Provider daily request budget reached.', 429)
    store.commit([change('PROVIDER_QUOTAS', key, {'count': count + cost}, previous, time.time() + 3 * 86400)])


def secrets():
    names = json.loads(os.environ.get('PROVIDER_PARAMETERS', '{}'))
    if not names:
        return {}
    import boto3
    result = boto3.client('ssm').get_parameters(Names=list(names.values()), WithDecryption=True)
    values = {r['Name']: r['Value'] for r in result['Parameters']}
    return {key: values[path] for key, path in names.items() if path in values}


def iqair(school, key):
    response = engine.request_json('https://api.airvisual.com/v2/nearest_city?' + urlencode(
        {'lat': school['lat'], 'lon': school['lon'], 'key': key}))
    if response.get('status') != 'success':
        raise ValueError('IQAir unavailable')
    data = response['data']; pollution = data.get('current', {}).get('pollution', {})
    value, when = pollution.get('aqius'), engine.timestamp(pollution.get('ts'))
    indices = []
    if engine.finite(value) and value >= 0 and when is not None and -300 <= time.time() - when <= 7200:
        indices.append({'source': 'IQAir', 'name': data.get('city', 'Nearest city'),
                        'aqi': value, 'standard': 'US', 'observedAt': engine.iso(when)})
    return {'stations': [], 'indices': indices, 'forecast': []}


def cpcb(school, key):
    # Resource ID and city are configuration, never a client-controlled URL.
    resource = os.environ.get('CPCB_RESOURCE_ID', '')
    import re
    if not re.fullmatch(r'[a-fA-F0-9-]{36}', resource) or school.get('cpcb_city') in (None, '', 'unconfigured'):
        raise ValueError('Configure CPCB resource ID and school cpcb_city')
    records = []
    for offset in range(0, 1000, 100):
        query = urlencode({'api-key': key, 'format': 'json', 'limit': 100, 'offset': offset,
                           'filters[city]': school['cpcb_city']})
        page = engine.request_json(f'https://api.data.gov.in/resource/{resource}?' + query).get('records', [])
        records.extend(page)
        if len(page) < 100:
            break
    stations = {}
    for row in records:
        # Do not reinterpret pollutant_avg as concentration unless explicit mass units exist.
        unit = str(row.get('pollutant_unit', '')).replace('μ', 'µ')
        if unit not in ('µg/m³', 'ug/m3', 'µg/m3'):
            continue
        name = str(row.get('pollutant_id', '')).lower().replace('.', '')
        if name not in ('pm25', 'pm10'):
            continue
        try:
            value = float(row['pollutant_avg'])
            when = datetime.strptime(row['last_update'], '%d-%m-%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Kolkata')).timestamp()
            lat, lon = float(row['latitude']), float(row['longitude'])
        except (ValueError, TypeError, KeyError):
            continue
        if not engine.finite(value) or value < 0:
            continue
        name_id = str(row.get('station', ''))
        identity = hashlib.sha256(name_id.encode()).hexdigest()[:20]
        station = stations.setdefault(identity, {'id': 'cpcb-' + identity, 'upstreamStationId': name_id,
                         'name': name_id, 'source': 'CPCB / OGD', 'kind': 'station', 'lat': lat, 'lon': lon,
                         'averagingPeriod': 'source-defined; not verified for official AQI', 'observedAt': engine.iso(when)})
        station[name] = value
        station['observedAt'] = engine.iso(min(when, engine.timestamp(station['observedAt'])))
    return {'stations': list(stations.values()), 'indices': [], 'forecast': []}


def fetch(school, credentials=None, now=None, store=None):
    now = time.time() if now is None else now
    credentials = secrets() if credentials is None else credentials
    approved = set(os.environ.get('RETAIN_PROVIDERS', 'Open-Meteo / CAMS').split(','))
    adapters = [('OpenAQ', 'openaq', engine.openaq), ('CPCB / OGD', 'cpcb', cpcb),
                ('OpenWeather', 'openweather', engine.openweather)]
    candidates, forecasts, statuses = [], [], []
    for name, key, adapter in adapters:
        if key not in credentials:
            statuses.append({'name': name, 'status': 'Credential not configured'})
            continue
        if name not in approved:
            statuses.append({'name': name, 'status': 'Disabled pending retention/license review'})
            continue
        try:
            if store:
                reserve_requests(store, name, {'OpenAQ': 5, 'CPCB / OGD': 10, 'OpenWeather': 2}[name])
            data = adapter(school, credentials[key])
            # Select one provider series; unknown averaging windows are never mixed across providers.
            unique = {str(s.get('upstreamStationId') or s['id']): s for s in data['stations']}
            estimate = engine.estimate(school, list(unique.values()))
            if estimate['pm25'] is not None:
                candidates.append((name, estimate))
            if data.get('forecast'):
                forecasts.append((name, data['forecast']))
            statuses.append({'name': name, 'status': 'Usable concentration' if estimate['pm25'] is not None else 'No usable mass concentration'})
        except Exception:
            statuses.append({'name': name, 'status': 'Unavailable or invalid response'})
    if not candidates or not forecasts:
        try:
            if 'Open-Meteo / CAMS' not in approved:
                raise ValueError('Retention not approved')
            if store:
                reserve_requests(store, 'Open-Meteo / CAMS')
            data = engine.openmeteo(school)
            if not candidates:
                candidates.append(('Open-Meteo / CAMS', engine.estimate(school, data['stations'])))
            if not forecasts:
                forecasts.append(('Open-Meteo / CAMS', data['forecast']))
            statuses.append({'name': 'Open-Meteo / CAMS', 'status': 'Regional model; approximately 45 km grid'})
        except Exception:
            statuses.append({'name': 'Open-Meteo / CAMS', 'status': 'Unavailable or not approved'})
    # Measured candidates precede modeled candidates. No multi-source average of unlike values.
    selected = next(((name, air) for name, air in candidates if any(s.get('kind') == 'station' for s in air['stations'])),
                    candidates[0] if candidates else ('Unavailable', engine.estimate(school, [])))
    source, result = selected
    forecast_source, rows = forecasts[0] if forecasts else ('Unavailable', [])
    result.update(source=source, mode='live', fetchedAt=engine.iso(now), providers=statuses, indices=[],
                  forecast=[dict(p, retrievedAt=engine.iso(now), issuedAt=None,
                                 issueTimeMeaning='Provider issue time not supplied') for p in engine.valid_forecast(rows, now)],
                  forecastSource=forecast_source, history=[], stale=result['pm25'] is None,
                  selectionPolicy='Prefer one measured source; otherwise one regional model. No cross-provider averaging.',
                  standard='India particle estimate', retentionApproved=source in approved)
    return result


def separate_indices(store, school):
    """On-demand comparison only. Provider indices are never persisted or archived."""
    credentials = secrets()
    result = []
    for name, key, adapter in [('WAQI / AQICN', 'waqi', engine.waqi), ('IQAir', 'iqair', iqair)]:
        if key not in credentials:
            result.append({'name': name, 'status': 'Credential not configured', 'indices': []})
            continue
        try:
            reserve_requests(store, name, limit=250)
            data = adapter(school, credentials[key])
            result.append({'name': name, 'status': 'Live index-only comparison; no concentration conversion', 'indices': data['indices']})
        except Exception:
            result.append({'name': name, 'status': 'Unavailable, invalid response or quota reached', 'indices': []})
    return {'providers': result, 'notice': 'WAQI and AQICN are one source. These US indices are separate from India particle estimates and are not archived.'}


def weather(school, store=None):
    if store:
        reserve_requests(store, 'Open-Meteo weather')
    query = urlencode({'latitude': school['lat'], 'longitude': school['lon'], 'timezone': 'GMT',
                       'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m'})
    data = engine.request_json('https://api.open-meteo.com/v1/forecast?' + query)
    row = data.get('current', {})
    observed = engine.gmt_timestamp(row.get('time'))
    if observed is None or not -300 <= time.time() - observed <= 7200:
        raise ValueError('Weather is stale')
    return {'observedAt': engine.iso(observed), 'temperature': row.get('temperature_2m'),
            'humidity': row.get('relative_humidity_2m'), 'wind': row.get('wind_speed_10m'),
            'units': data.get('current_units', {}), 'source': 'Open-Meteo weather model'}


def observation_id(air):
    evidence = [(s.get('id'), s.get('observedAt'), s.get('pm25'), s.get('pm10')) for s in air.get('stations', [])]
    return hashlib.sha256(json.dumps([air.get('source'), sorted(evidence, key=str)], sort_keys=True).encode()).hexdigest()[:24]
