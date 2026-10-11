"""Conservative stateful alert stabilization and forecast planning comparisons."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.functions.air_engine import finite, timestamp
from backend.functions.guardian_rules import FLAGS


def stabilize(previous, flag, observed, pm25, escalation=None, recovery=None):
    """One vote per observed UTC hour; missing hours break persistence.

    Never delay showing the raw worse flag. Persistence gates recovery/alerts;
    the hourly running mean is supporting context, not a replacement observation.
    """
    escalation = max(1, int(escalation or os.getenv('FLAG_ESCALATION_HOURS', '1')))
    recovery = max(1, int(recovery or os.getenv('FLAG_RECOVERY_HOURS', '2')))
    prior = dict(previous or {})
    if flag not in FLAGS or observed is None:
        return {'flag': 'unknown', 'hour': None, 'candidate': None, 'count': 0, 'meanPm25': None}
    hour = int(observed // 3600)
    if prior.get('hour') == hour:
        # Repeated retrievals never vote as additional hours. Escalation stays immediate.
        return dict(prior, flag=max([prior.get('flag', flag), flag], key=FLAGS.index))
    stable = prior.get('flag') if prior.get('flag') in FLAGS else flag
    consecutive = prior.get('hour') == hour - 1
    count = prior.get('count', 0) + 1 if consecutive and prior.get('candidate') == flag else 1
    need = escalation if FLAGS.index(flag) > FLAGS.index(stable) else recovery
    if flag == stable or count >= need:
        stable = flag
    samples = list(prior.get('samples', []))[-2:] if consecutive else []
    if finite(pm25) and pm25 >= 0:
        samples.append(pm25)
    return {'flag': stable, 'hour': hour, 'candidate': flag, 'count': count,
            'samples': samples, 'meanPm25': round(sum(samples) / len(samples), 2) if samples else None}


def cleanest_windows(air, school, now):
    """Compare complete forecast-covered slots, same day, within school hours.

    Do not bridge missing hours or treat a stale forecast as an opportunity.
    """
    from cloud.dayplan import health, DEFAULT_BLOCKS
    if health(air, now)['status'] not in ('Fresh', 'Getting old'):
        return []
    zone = ZoneInfo(school.get('timezone', 'Asia/Kolkata'))
    date = datetime.fromtimestamp(now, zone).date()
    points = {int(timestamp(p['time'])): p for p in air.get('forecast', [])
              if timestamp(p.get('time')) is not None and finite(p.get('pm25')) and p['pm25'] >= 0}

    def concentration(start, minutes):
        end, cursor, total = start + minutes * 60, start, 0
        while cursor < end:
            available = [(t, p) for t, p in points.items() if t <= cursor < t + 3600]
            if not available:
                return None
            t, point = max(available, key=lambda item: item[0])
            stop = min(end, t + 3600)
            total += point['pm25'] * (stop - cursor)
            cursor = stop
        return total / (minutes * 60)

    result = []
    for block in school.get('timetable', DEFAULT_BLOCKS):
        if not block.get('outdoors') or block['name'].lower() not in ('pe', 'assembly'):
            continue
        start = datetime.combine(date, datetime.strptime(block['start'], '%H:%M').time(), zone).timestamp()
        finish = datetime.combine(date, datetime.strptime(block['end'], '%H:%M').time(), zone).timestamp()
        minutes = int((finish - start) / 60)
        current = concentration(start, minutes)
        candidates = []
        for hour in range(8, 16):
            candidate = datetime.combine(date, datetime.strptime(f'{hour:02d}:00', '%H:%M').time(), zone).timestamp()
            if candidate < now or candidate + minutes * 60 > datetime.combine(date, datetime.strptime('16:00', '%H:%M').time(), zone).timestamp():
                continue
            value = concentration(candidate, minutes)
            if value is not None:
                candidates.append((value, candidate))
        if not candidates or current is None:
            continue
        best, candidate = min(candidates)
        if best >= current or candidate == start:
            continue
        result.append({'block': block['name'], 'original': block['start'],
                       'suggested': datetime.fromtimestamp(candidate, zone).strftime('%H:%M'),
                       'minutes': minutes, 'originalPm25': round(current, 1), 'suggestedPm25': round(best, 1),
                       'label': 'Planning estimate; check timetable conflicts and recheck before the activity.'})
    return result


def kid_workspace(config, planning, notice, now, example=False):
    """An explicit allowlist; arbitrary adult wording never enters the kid response."""
    published = bool(notice and notice['expiresAt'] > now and notice['flag'] == planning['flag'])
    flag = notice['flag'] if published else planning['flag'] if example else 'unknown'
    code = 'indoor-pe' if flag in ('orange', 'red') else 'gentle' if flag == 'yellow' else 'usual' if flag == 'green' else 'verify'
    return {'school': {'id': config['id'], 'name': config['name']}, 'membership': {'role': 'kid'},
            'kid': {'flag': flag, 'published': published, 'actionCode': code,
                    'questionCode': 'kid.question', 'noticeTime': notice['time'] if published else None}}
