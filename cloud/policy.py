"""Explainable school policy. Weather/building context does not manufacture clean air."""
import time
from backend.functions.air_engine import timestamp, particle_index, finite, MAX_AGE
from backend.functions.guardian_rules import child_risk, recommendations
from cloud.contracts import POLICY_VERSION, number, Problem


def plan(air, school, age='5-8', caution=False, activity=None, indoor=None, now=None, role='parent'):
    now = time.time() if now is None else now
    observed = timestamp(air.get('observedAt'))
    stale = observed is None or not -300 <= now - observed <= MAX_AGE or air.get('stale', False)
    context = dict(air, stale=stale)
    result = child_risk(context, age, caution)
    ranks = ['green', 'yellow', 'orange', 'red']
    stable = air.get('stabilizedFlag')
    if result['flag'] in ranks and stable in ranks and ranks.index(stable) > ranks.index(result['flag']):
        result['flag'] = stable
        result['reasons'].append('A more cautious flag is held until consecutive hourly recovery observations are available.')
    result.update(policyVersion=POLICY_VERSION, inputObservedAt=air.get('observedAt'),
                  expiresAt=min(now + 900, observed + MAX_AGE) if observed and not stale else now,
                  evidenceQuality=air.get('confidence', {'label': 'Unavailable'}), indoor={'status': 'unknown'})
    result['reasons'] = list(result['reasons'])
    result['reasons'].append(f"Building: {school.get('building_type', 'unknown')}; AC alone does not establish cleaner indoor air.")
    if indoor:
        when = timestamp(indoor.get('observedAt'))
        if indoor.get('quality') == 'usable' and when and 0 <= now - when <= 900 and finite(indoor.get('pm25')):
            result['indoor'] = {'status': 'measured', 'pm25': indoor['pm25'], 'observedAt': indoor['observedAt'],
                                'label': 'Experimental indoor PM2.5 measurement; not activity clearance'}
    if activity:
        minutes = number(activity.get('minutes'), 'Activity minutes', 1, 720)
        start = timestamp(activity.get('start'))
        if start is None:
            raise Problem('Activity start must include a timezone.')
        peaks = [p for p in air.get('forecast', []) if timestamp(p.get('time')) is not None
                 and start <= timestamp(p['time']) < start + minutes * 60 and finite(p.get('pm25'))]
        result['activity'] = {'minutes': minutes, 'start': activity['start'],
                              'forecastPm25': max((p['pm25'] for p in peaks), default=None),
                              'label': 'Provider forecast for this activity window; regional, not gate-level'}
        if peaks:
            pm = result['activity']['forecastPm25']
            result['activity']['planning'] = child_risk({'aqi': particle_index(pm), 'pm25': pm, 'standard': 'India particle estimate'}, age, caution)
        result['reasons'].append('Activity time selects the forecast window; no arbitrary time-of-day risk multiplier is applied.')
    result['actions'] = recommendations(context, result, role, result['indoor'].get('pm25'))
    return result


def sensor_quality(reading, previous=None, now=None):
    now = time.time() if now is None else now
    reasons = []
    observed = timestamp(reading.get('observedAt'))
    if observed is None or not -60 <= now - observed <= 900:
        reasons.append('Reading missing, stale or future dated')
    if not finite(reading.get('pm25')) or not 0 <= reading['pm25'] <= 2000:
        reasons.append('Invalid PM2.5 concentration')
    if reading.get('sampleCount', 0) < 3:
        reasons.append('Insufficient samples')
    if finite(reading.get('humidity')) and reading['humidity'] >= 85:
        reasons.append('High humidity: optical PM reading needs review')
    if previous and finite(reading.get('pm25')) and finite(previous.get('pm25')):
        if abs(reading['pm25'] - previous['pm25']) > 300:
            reasons.append('Abrupt change: inspect before automatic use')
    return {'quality': 'review' if reasons else 'usable', 'qualityReasons': reasons,
            'confidenceLabel': 'Experimental; calibration required', 'evaluatedAt': now}
