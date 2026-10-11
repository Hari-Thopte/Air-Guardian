"""Provider adapters and conservative station interpolation. No browser secrets."""
import copy
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CACHE = {}
TTL = 300
MAX_AGE = 7200
SCHOOLS = {
    'riverdale': {'id': 'riverdale', 'name': 'Delhi school campus', 'lat': 28.6139, 'lon': 77.209},
    'greenwood': {'id': 'greenwood', 'name': 'Mumbai school campus', 'lat': 19.076, 'lon': 72.8777},
    'horizon': {'id': 'horizon', 'name': 'South Delhi campus', 'lat': 28.5245, 'lon': 77.2066},
}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    try:
        if finite(value):
            return float(value)
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def gmt_timestamp(value):
    """Open-Meteo's requested GMT time may omit its UTC suffix."""
    observed = timestamp(value)
    if observed is None and isinstance(value, str):
        observed = timestamp(value + 'Z')
    return observed


def valid_forecast(rows, now=None):
    """Keep only usable, future concentration inputs in the requested 48h window."""
    now = time.time() if now is None else now
    valid = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        observed, pm25 = timestamp(row.get('time')), row.get('pm25')
        if observed is not None and now < observed <= now + 48 * 3600 and finite(pm25) and pm25 >= 0:
            valid.append(dict(row, time=iso(observed)))
    return sorted(valid, key=lambda row: row['time'])


def distance(a, b):
    lat1, lat2 = math.radians(a['lat']), math.radians(b['lat'])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(b['lon'] - a['lon'])
    h = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def particle_index(value, pollutant='pm25'):
    """India particle breakpoints; instantaneous inputs are an estimate, not official AQI."""
    if not finite(value) or value < 0:
        return None
    concentrations = [0, 30, 60, 90, 120, 250, 500] if pollutant == 'pm25' else [0, 50, 100, 250, 350, 430, 600]
    indexes = [0, 50, 100, 200, 300, 400, 500]
    for i in range(1, len(concentrations)):
        if value <= concentrations[i]:
            fraction = (value - concentrations[i-1]) / (concentrations[i] - concentrations[i-1])
            return round(indexes[i-1] + fraction * (indexes[i] - indexes[i-1]))
    return 500


def interpolate(school, stations, pollutant='pm25', now=None):
    now = now or time.time()
    eligible = []
    for station in stations:
        observed = timestamp(station.get('observedAt'))
        value = station.get(pollutant)
        if not finite(value) or value < 0 or observed is None or not -300 <= now - observed <= MAX_AGE:
            continue
        if not finite(station.get('lat')) or not finite(station.get('lon')) or abs(station['lat'])>90 or abs(station['lon'])>180:
            continue
        km = distance(school, station)
        if km <= 25:
            eligible.append((station, km))
    if not eligible:
        return None, []
    colocated = [s[pollutant] for s, km in eligible if km < .02]
    if colocated:
        return round(sum(colocated) / len(colocated), 2), eligible
    weights = [1 / max(km, .05) ** 2 for _, km in eligible]
    return round(sum(s[pollutant] * w for (s, _), w in zip(eligible, weights)) / sum(weights), 2), eligible


def held_out(stations, now=None):
    errors = []
    now=now or time.time()
    for i, station in enumerate(stations):
        observed=timestamp(station.get('observedAt'))
        if observed is None or not -300<=now-observed<=MAX_AGE or not finite(station.get('pm25')) or station['pm25']<0 or not finite(station.get('lat')) or not finite(station.get('lon')) or abs(station['lat'])>90 or abs(station['lon'])>180:
            continue
        prediction, used = interpolate(station, stations[:i] + stations[i+1:], now=now)
        if prediction is not None and used and finite(station.get('pm25')):
            errors.append({'station': station['name'], 'observed': station['pm25'], 'predicted': prediction,
                           'absoluteError': round(abs(prediction - station['pm25']), 2),
                           'aqiAbsoluteError': abs(particle_index(prediction)-particle_index(station['pm25']))})
    return {'count': len(errors), 'mae': round(sum(e['absoluteError'] for e in errors) / len(errors), 2) if errors else None,
            'aqiMae': round(sum(e['aqiAbsoluteError'] for e in errors)/len(errors),2) if errors else None,
            'unit': 'µg/m³ PM2.5', 'rows': errors, 'generatedAt': iso(now),
            'maxInputAgeMinutes': MAX_AGE // 60, 'maxDistanceKm': 25,
            'method': 'Leave one station out, then predict it from the remaining fresh stations using inverse-distance-squared weighting.',
            'note': 'Stations are comparison points, not independent ground truth at the school. This does not prove school-gate accuracy.'}


def request_json(url, headers=None):
    with urlopen(Request(url, headers={'Accept': 'application/json', **(headers or {})}), timeout=5) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Provider response too large')
        return json.loads(raw)


def openaq(school, key):
    headers = {'X-API-Key': key}
    query = urlencode({'coordinates': f"{school['lat']},{school['lon']}", 'radius': 25000, 'limit': 4})
    locations = request_json('https://api.openaq.org/v3/locations?' + query, headers).get('results', [])

    def location_reading(location):
        sensors = {s['id']: s.get('parameter', {}) for s in location.get('sensors', []) if 'id' in s}
        latest = request_json(f"https://api.openaq.org/v3/locations/{int(location['id'])}/latest", headers)
        coords = location.get('coordinates') or {}
        station = {'id': f"openaq-{location['id']}", 'name': location.get('name', 'OpenAQ station'),
                   'lat': coords.get('latitude'), 'lon': coords.get('longitude'), 'source': 'OpenAQ', 'kind': 'station'}
        times = []
        for measurement in latest.get('results', []):
            parameter = sensors.get(measurement.get('sensorsId'), {})
            name = parameter.get('name', '').replace('.', '').replace('_', '')
            units = parameter.get('units', '').replace('μ', 'µ')
            observed = timestamp((measurement.get('datetime') or {}).get('utc'))
            value = measurement.get('value')
            if name in ('pm25', 'pm10') and units in ('µg/m³', 'ug/m3', 'µg/m3') and finite(value) and value >= 0 and observed:
                station[name] = value
                times.append(observed)
        if times:
            station['observedAt'] = iso(min(times))
        return station

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(location_reading, location) for location in locations]
        stations = []
        for future in futures:
            try:
                stations.append(future.result())
            except Exception:
                pass
    return {'stations': stations, 'forecast': [], 'indices': []}


def waqi(school, key):
    url = f"https://api.waqi.info/feed/geo:{school['lat']};{school['lon']}/?" + urlencode({'token': key})
    response = request_json(url)
    if response.get('status') != 'ok':
        raise ValueError('WAQI unavailable')
    data = response.get('data', {})
    observed = timestamp(data.get('time', {}).get('iso') or data.get('time', {}).get('v'))
    # iaqi.pm25 is an INDEX, never treat it as concentration or combine it with OpenAQ PM mass.
    indices = []
    if finite(data.get('aqi')) and data['aqi'] >= 0 and observed is not None and -300 <= time.time() - observed <= MAX_AGE:
        indices.append({'source': 'WAQI', 'name': data.get('city', {}).get('name', 'WAQI'),
                        'aqi': data['aqi'], 'standard': 'US', 'observedAt': iso(observed)})
    return {'stations': [], 'forecast': [], 'indices': indices}


def openweather(school, key):
    query = urlencode({'lat': school['lat'], 'lon': school['lon'], 'appid': key})
    current = request_json('https://api.openweathermap.org/data/2.5/air_pollution?' + query)
    row = (current.get('list') or [{}])[0]
    station = {'id': 'openweather-model', 'name': 'OpenWeather model at campus', 'lat': school['lat'], 'lon': school['lon'],
               'kind': 'model', 'source': 'OpenWeather', 'observedAt': iso(row['dt']) if finite(row.get('dt')) else None,
               'pm25': row.get('components', {}).get('pm2_5'), 'pm10': row.get('components', {}).get('pm10')}
    if not finite(station['pm10']) or station['pm10'] < 0:
        station['pm10'] = None
    forecast = []
    try:
        data = request_json('https://api.openweathermap.org/data/2.5/air_pollution/forecast?' + query)
        now = time.time()
        forecast = valid_forecast([
            {'time': iso(r['dt']), 'pm25': (r.get('components') or {}).get('pm2_5'), 'source': 'OpenWeather forecast'}
            for r in data.get('list', [])
            if isinstance(r, dict) and finite(r.get('dt')) and now < r['dt'] <= now + 48 * 3600
        ], now)
    except Exception:
        pass
    return {'stations': [station], 'forecast': forecast, 'indices': []}


def openmeteo(school):
    """Keyless CAMS regional model. It is not a station or school-gate sensor."""
    query = urlencode({'latitude': school['lat'], 'longitude': school['lon'], 'timezone': 'GMT',
                       'domains': 'cams_global', 'current': 'pm2_5,pm10,us_aqi',
                       'hourly': 'pm2_5,us_aqi', 'past_days': 1, 'forecast_days': 2})
    data = request_json('https://air-quality-api.open-meteo.com/v1/air-quality?' + query)
    if not isinstance(data, dict) or data.get('utc_offset_seconds', 0) != 0:
        raise ValueError('Expected a GMT model response')
    current, units = data.get('current') or {}, data.get('current_units') or {}
    observed = gmt_timestamp(current.get('time'))
    if observed is None or not -300 <= time.time()-observed <= MAX_AGE:
        raise ValueError('Current model timestamp invalid or stale')
    for key in ('pm2_5', 'pm10'):
        if units.get(key, '').replace('μ', 'µ') not in ('µg/m³', 'ug/m3', 'µg/m3'):
            raise ValueError('Unrecognized model units')
    if not finite(current.get('pm2_5')) or current['pm2_5'] < 0:
        raise ValueError('Current model concentration missing')
    model = {'id': 'cams-global-model', 'name': 'CAMS regional estimate at selected coordinates',
             'lat': school['lat'], 'lon': school['lon'], 'kind': 'model', 'source': 'Open-Meteo / CAMS',
             'observedAt': iso(observed), 'pm25': current['pm2_5'],
             'pm10': current['pm10'] if finite(current.get('pm10')) and current['pm10'] >= 0 else None,
             'resolutionKm': 45}
    hourly, history, forecast = data.get('hourly') or {}, [], []
    values = hourly.get('pm2_5') or []
    if values and (data.get('hourly_units') or {}).get('pm2_5', '').replace('μ', 'µ') not in ('µg/m³', 'ug/m3', 'µg/m3'):
        raise ValueError('Unrecognized forecast units')
    for i, value in enumerate(hourly.get('time') or []):
        stamp = gmt_timestamp(value);pm = values[i] if i < len(values) else None
        if stamp is None or not finite(pm) or pm < 0:continue
        row = {'time': iso(stamp), 'pm25': pm, 'source': 'CAMS regional model'}
        if observed-86400 <= stamp <= observed:history.append(row)
        elif observed < stamp <= observed+172800:forecast.append(row)
    indices = [{'source': 'Open-Meteo / CAMS', 'name': 'Provider-reported US AQI',
                'aqi': current['us_aqi'], 'standard': 'US', 'observedAt': iso(observed)}] if finite(current.get('us_aqi')) and current['us_aqi'] >= 0 else []
    return {'stations': [model], 'forecast': forecast, 'indices': indices, 'history': history}


def demo(school, polluted=False):
    now = time.time()
    base = 110 if polluted else 38
    stations = [{'id': f'demo-{i}', 'name': f'Demo station {i+1}', 'lat': school['lat'] + dy, 'lon': school['lon'] + dx,
                 'pm25': base + offset, 'pm10': (base + offset) * 1.8, 'observedAt': iso(now - (i + 1) * 300),
                 'kind': 'station', 'source': 'Fictional demo station'}
                for i, (dy, dx, offset) in enumerate([(0.014, 0.018, -8), (-0.021, .016, 16), (.032, -.019, 4), (-.025, -.022, 9)])]
    result = estimate(school, stations, now)
    result.update({'mode': 'demo', 'source': 'Synthetic station fixtures — not measurements', 'cached': False,
                   'providers': [{'name': 'Demo fixtures', 'status': 'synthetic'}], 'indices': [],
                   'forecast': [{'time': iso(now + h * 3600), 'pm25': round(base + 10 * math.sin(h / 4) + (20 if h > 18 else 0), 1),
                                 'source': 'Synthetic forecast fixture'} for h in range(1, 49)]})
    return result


def estimate(school, stations, now=None):
    now = now or time.time()
    measured = [s for s in stations if s.get('kind') == 'station']
    pm25, used = interpolate(school, measured, now=now)
    method = 'Station IDW, power 2'
    if pm25 is None:
        model = [s for s in stations if s.get('kind') == 'model']
        pm25, used = interpolate(school, model, now=now)
        method = 'Regional model fallback (not station interpolation)'
    pm10, _ = interpolate(school, [s for s, _ in used], 'pm10', now)
    nearest = min((km for _, km in used), default=None)
    oldest = min((timestamp(s['observedAt']) for s, _ in used), default=None)
    newest = max((timestamp(s['observedAt']) for s, _ in used), default=None)
    score = 0 if not used else max(5, min(90, round(35 + min(len(used), 4) * 12 - (nearest or 0) * 3 - (now - oldest) / 300)))
    if 'fallback' in method:
        score = min(score, 30)
    indexes = [v for v in [particle_index(pm25), particle_index(pm10, 'pm10')] if v is not None]
    return {'school': school, 'pm25': pm25, 'pm10': pm10, 'aqi': max(indexes) if indexes else None,
            'estimateLabel': 'School-area estimate', 'claimScope': 'school-area',
            'standard': 'India particle estimate', 'method': method, 'stations': [dict(s, distanceKm=round(km, 2)) for s, km in used],
            'nearestKm': round(nearest, 2) if nearest is not None and 'fallback' not in method else None,
            'observedAt': iso(oldest) if oldest else None, 'latestAt': iso(newest) if newest else None,
            'confidence': {'score': score, 'label': 'Moderate' if score >= 55 else 'Low' if score else 'Unavailable',
                           'meaning': 'Heuristic coverage score, not a validated probability'},
            'validation': held_out(measured, now),
            'note': 'A spatial estimate at campus coordinates, not a school-gate measurement. Instantaneous particle inputs do not meet the full official AQI averaging and pollutant requirements.'}


def fetch_air(school, mode='demo', polluted=False):
    if mode == 'demo':
        return demo(school, polluted)
    key = (school['lat'], school['lon'])
    cached = CACHE.get(key)
    now = time.time()
    cached_observed = timestamp(cached[1].get('observedAt')) if cached else None
    if cached and 0 <= now - cached[0] < TTL and cached_observed is not None and -300 <= now - cached_observed <= MAX_AGE:
        return dict(copy.deepcopy(cached[1]), cached=True)
    adapters = [('OpenAQ', 'OPENAQ_API_KEY', openaq), ('WAQI', 'WAQI_API_KEY', waqi), ('OpenWeather', 'OPENWEATHER_API_KEY', openweather)]
    stations, indices, forecast, statuses = [], [], [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [(name, pool.submit(adapter, school, os.environ[env])) for name, env, adapter in adapters if os.environ.get(env)]
        statuses += [{'name': name, 'status': 'Credential not configured', 'credential': 'not-configured'} for name, env, _ in adapters if not os.environ.get(env)]
        for name, job in jobs:
            try:
                data = job.result()
                stations.extend(data['stations']); indices.extend(data['indices']); forecast.extend(valid_forecast(data['forecast']))
                usable = len(data['stations']) + len(data['indices'])
                statuses.append({'name': name, 'status': f'Credential configured · {usable} usable current result(s)', 'credential': 'configured'})
            except Exception:
                # Never put provider URLs, API keys or exception strings in responses/logs.
                statuses.append({'name': name, 'status': 'Credential configured · unavailable or invalid response', 'credential': 'configured'})
    result = estimate(school, stations)
    history = []
    if result['pm25'] is None:
        try:
            regional = openmeteo(school)
            stations.extend(regional['stations']);indices.extend(regional['indices'])
            forecast = forecast or valid_forecast(regional['forecast']);history = regional['history']
            statuses.append({'name': 'Open-Meteo / CAMS', 'status': 'Keyless regional model received · ~45 km grid', 'credential': 'not-required'})
            result = estimate(school, stations)
        except Exception:
            statuses.append({'name': 'Open-Meteo / CAMS', 'status': 'Keyless regional model unavailable', 'credential': 'not-required'})
    result.update({'mode': 'live', 'source': ' / '.join(dict.fromkeys(s['source'] for s in result['stations'])) or 'No usable concentration source',
                   'providers': statuses, 'indices': indices, 'forecast': forecast, 'history': history, 'cached': False,
                   'fetchedAt': iso(time.time())})
    if any(s.get('source') == 'Open-Meteo / CAMS' for s in result['stations']):
        result['attribution'] = {'label': 'Open-Meteo and CAMS', 'url': 'https://open-meteo.com/en/docs/air-quality-api'}
    elif any(s.get('source') == 'OpenWeather' for s in result['stations']):
        result['attribution'] = {'label': 'OpenWeather', 'url': 'https://openweathermap.org/api/air-pollution'}
    elif any(s.get('source') == 'OpenAQ' for s in result['stations']):
        result['attribution'] = {'label': 'OpenAQ', 'url': 'https://openaq.org/'}
    if any(s.get('kind') == 'model' for s in result['stations']):
        coverage = ' CAMS global coverage is approximately 45 km.' if any(s.get('source') == 'Open-Meteo / CAMS' for s in result['stations']) else ''
        result['note'] = 'Regional modeled air, not a nearby station or school-gate measurement.' + coverage + ' The particle estimate and school planning flag use different thresholds from provider-reported US AQI.'
    observed = timestamp(result['observedAt'])
    candidates = [p for p in history if observed is not None and timestamp(p.get('time')) is not None
                  and finite(p.get('pm25')) and p['pm25'] >= 0 and abs(timestamp(p['time']) - (observed - 86400)) <= 1800]
    yesterday = min(candidates, key=lambda p: abs(timestamp(p['time']) - (observed - 86400)), default=None)
    result['change24h'] = {'pm25': round(result['pm25']-yesterday['pm25'], 1), 'previous': yesterday['pm25'], 'source': 'Regional modeled PM2.5'} if yesterday and finite(result['pm25']) else None
    if result['pm25'] is None and cached and 0 <= time.time() - cached[0] <= 3600:
        result = dict(copy.deepcopy(cached[1]), cached=True, stale=True, providers=statuses,
                      lastAttemptAt=iso(time.time()), change24h=None)
        result['confidence'] = {'score': 0, 'label': 'Stale', 'meaning': 'Current conditions unavailable'}
    elif result['pm25'] is not None:
        CACHE[key] = (time.time(), copy.deepcopy(result))
    return result
