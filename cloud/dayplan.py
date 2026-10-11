"""School-day presentation derived from the existing policy, never activity clearance."""
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from backend.functions.air_engine import timestamp, finite, particle_index, iso, MAX_AGE
from backend.functions.guardian_rules import POLICY
from cloud.contracts import Problem, clock, text

FRESH_SECONDS = MAX_AGE // 2
STALE_SECONDS = MAX_AGE  # Same constant as the planning engine.


def reminder_state(store, school_id, config, notice, receipts, now=None):
    from cloud.contracts import DEFAULT_PREFS, quiet, local_day
    now=time.time() if now is None else now
    if not notice or notice['expiresAt']<=now: return {'allowed':False,'reason':'Publish a current school plan first.'}
    pending=[p for p in receipt_summary(notice,receipts,[])['people'] if not p['confirmed']]
    if not pending: return {'allowed':False,'reason':'Everyone has confirmed.'}
    for person in pending:
        prefs={**DEFAULT_PREFS,**(store.get('USER#'+person['sub'],'PREFERENCES') or {})}
        if quiet(prefs,config,now): return {'allowed':False,'reason':'A pending recipient is in quiet hours.'}
        for channel in prefs['channels']:
            cap=store.get('USER#'+person['sub'],f"CAP#{school_id}#{local_day(config,now)}#{channel}") or {}
            if cap.get('count',0)>=prefs['dailyCap']: return {'allowed':False,'reason':'A pending recipient has reached the daily cap.'}
    return {'allowed':True,'reason':'Preferences are checked again at dispatch.'}


def health(air, now=None):
    now = time.time() if now is None else now
    observed = timestamp(air.get('observedAt'))
    age = now-observed if observed is not None else None
    status = 'Unavailable' if age is None or age < -300 or not finite(air.get('pm25')) else 'Stale' if air.get('stale') or age > STALE_SECONDS else 'Getting old' if age > FRESH_SECONDS else 'Fresh'
    return {'status':status, 'ageMinutes':round(age/60) if age is not None else None,
            'freshSeconds':FRESH_SECONDS,'staleSeconds':STALE_SECONDS}


def morning_brief(air, config, now=None):
    from cloud.policy import plan
    now = time.time() if now is None else now
    zone=ZoneInfo(config['timezone'])
    tomorrow=(datetime.fromtimestamp(now,zone)+timedelta(days=1)).date()
    source_fresh=health(air,now)['status'] in ('Fresh','Getting old')
    candidates=[p for p in air.get('forecast',[]) if source_fresh and timestamp(p.get('time')) is not None
                and datetime.fromtimestamp(timestamp(p['time']),zone).date()==tomorrow
                and 6<=datetime.fromtimestamp(timestamp(p['time']),zone).hour<12
                and finite(p.get('pm25')) and p['pm25']>=0]
    if candidates:
        point=max(candidates,key=lambda p:p['pm25'])
        context=dict(air,pm25=point['pm25'],aqi=particle_index(point['pm25']),observedAt=iso(now),stale=False,forecast=[],stabilizedFlag=None)
        planning=plan(context,config,now=now)
        return {'available':True,'label':'Demo forecast' if air.get('mode')=='demo' else 'Regional provider forecast',
                'flag':planning['flag'],'pm25':point['pm25'],'validAt':point['time'], 'source':point.get('source',air.get('forecastSource')),
                'headline':planning['actions'][0]['text'],'reason':planning['actions'][0]['why'], 'retrievedAt':point.get('retrievedAt',air.get('fetchedAt'))}
    planning=plan(air,config,now=now)
    return {'available':False,'label':'Forecast not connected for tomorrow morning. Current reading only.',
            'flag':planning['flag'],'pm25':air.get('pm25'),'headline':planning['actions'][0]['text'],
            'reason':planning['actions'][0]['why']}


def outdoor_summary(config, planning, air=None, now=None):
    from cloud.policy import plan
    now = time.time() if now is None else now
    blocks=timetable(config,planning)
    regional=False
    for block in blocks:
        local=datetime.fromtimestamp(now,ZoneInfo(config['timezone'])).replace(hour=int(block['start'][:2]),minute=int(block['start'][3:]),second=0,microsecond=0)
        points=[p for p in (air or {}).get('forecast',[]) if health(air or {},now)['status'] in ('Fresh','Getting old') and timestamp(p.get('time')) is not None
                and abs(timestamp(p['time'])-local.timestamp())<=1800 and finite(p.get('pm25')) and p['pm25']>=0]
        if points:
            point=min(points,key=lambda p:abs(timestamp(p['time'])-local.timestamp()))
            context=dict(air,pm25=point['pm25'],aqi=particle_index(point['pm25']),observedAt=iso(now),stale=False,forecast=[],stabilizedFlag=None)
            block.update(timetable({'timetable':[block]},plan(context,config,now=now))[0]);regional=True
    before=sum(b['minutes'] for b in blocks if b['outdoors'] and b['flag'] in ('orange','red'))
    moved=sum(b['minutes'] for b in blocks if b['outdoors'] and b['actionId']=='indoor-pe')
    return {'available':planning['flag']!='unknown','before':before,'after':max(0,before-moved),'moved':moved,'blocks':blocks,
            'basis':'Available regional hourly forecast; unmatched blocks use current flag.' if regional else 'Current flag applied to the timetable; no matching hourly data.',
            'label':'Planning estimate. Not an exposure or health measurement.'}

DEFAULT_BLOCKS = [
    {'name': 'Assembly', 'start': '08:30', 'end': '08:50', 'outdoors': True},
    {'name': 'PE', 'start': '10:00', 'end': '10:30', 'outdoors': True},
    {'name': 'Break', 'start': '11:30', 'end': '11:45', 'outdoors': True},
    {'name': 'Pickup', 'start': '15:00', 'end': '15:20', 'outdoors': True}]


def validate_blocks(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 16:
        raise Problem('School day needs 1–16 blocks.')
    result = []
    for block in value:
        if not isinstance(block, dict) or type(block.get('outdoors')) is not bool:
            raise Problem('Each block needs an outdoor yes/no choice.')
        start, end = clock(block.get('start')), clock(block.get('end'))
        if end <= start:
            raise Problem('Each block must end after it starts on the same day.')
        result.append({'name': text(block.get('name'), 'Block name', 60), 'start': start,
                       'end': end, 'outdoors': block['outdoors']})
    result.sort(key=lambda b: b['start'])
    if any(b['start'] < a['end'] for a, b in zip(result, result[1:])):
        raise Problem('School day blocks must not overlap.')
    return result


def timetable(config, planning):
    actions = {a['id']: a for a in planning['actions']}
    result = []
    for b in config.get('timetable', DEFAULT_BLOCKS):
        key = 'pickup' if 'pickup' in b['name'].lower() else 'indoor-pe' if b['name'].lower() in ('pe', 'assembly') else 'gentle'
        if planning['flag']=='unknown': key='verify'
        action = actions.get(key) if b['outdoors'] else None
        start, end = [int(v[:2]) * 60 + int(v[3:]) for v in (b['start'], b['end'])]
        result.append(dict(b, minutes=end-start, flag=planning['flag'], action=action['text'] if action else 'No change',
                           actionId=action['id'] if action else None, why=action['why'] if action else 'No matching schedule change in the current policy.'))
    return result


def receipt_summary(notice, receipts, members):
    audience = (notice or {}).get('audience', [{'sub': m['sub'], 'role': m['role'], 'class_id': m.get('class_id')}
                for m in members if m['active'] and m['role']!='kid'])
    confirmed = {r['sub'] for r in receipts}
    rows = [dict(m, confirmed=m['sub'] in confirmed) for m in audience]
    return {'total': len(rows), 'confirmed': sum(r['confirmed'] for r in rows), 'people': rows}


def presentation(config, planning):
    return {'timetable': timetable(config, planning), 'particleBoundaries': POLICY[planning['ageGroup']][1]}
