"""Offline forecast evaluation against measured observations, grouped by source and horizon."""
from collections import defaultdict
from backend.functions.air_engine import timestamp, finite


def evaluate(forecasts, actuals, tolerance_seconds=1800):
    measured = [r for r in actuals if r.get('kind') in ('station', 'station-estimate', 'sensor') and finite(r.get('pm25'))]
    groups = defaultdict(list)
    seen = set()
    for run in forecasts:
        issued = timestamp(run.get('issuedAt') or run.get('retrievedAt'))
        if issued is None:
            continue
        for point in run.get('points', []):
            valid = timestamp(point.get('time'))
            if valid is None or valid <= issued or not finite(point.get('pm25')):
                continue
            candidates = [r for r in measured if timestamp(r.get('observedAt')) is not None and abs(timestamp(r['observedAt']) - valid) <= tolerance_seconds]
            if not candidates:
                continue
            actual = min(candidates, key=lambda r: abs(timestamp(r['observedAt']) - valid))
            key = (run.get('source'), issued, valid, actual['observedAt'])
            if key in seen:
                continue
            seen.add(key)
            horizon = int((valid - issued) // 3600)
            groups[(run.get('source'), horizon)].append(point['pm25'] - actual['pm25'])
    return [{'source': source, 'horizonHours': horizon, 'count': len(errors),
             'mae': round(sum(abs(e) for e in errors) / len(errors), 2),
             'bias': round(sum(errors) / len(errors), 2),
             'limitation': 'Station comparisons do not establish school-gate forecast accuracy.'}
            for (source, horizon), errors in sorted(groups.items())]


def persistence(last_reading, times):
    if not finite(last_reading.get('pm25')):
        return []
    return [{'time': t, 'pm25': last_reading['pm25'], 'source': 'Persistence baseline'} for t in times]
