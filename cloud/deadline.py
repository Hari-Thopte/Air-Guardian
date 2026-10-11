"""One daily reminder window; dispatch still enforces consent/quiet hours/caps."""
from datetime import datetime
from zoneinfo import ZoneInfo
from cloud.contracts import local_day
from cloud.store import change


def nudge_changes(store, school, planning, now):
    from cloud.pipeline import emit_changes
    from cloud.dayplan import DEFAULT_BLOCKS
    pk='SCHOOL#'+school['id']
    notice=store.get(pk,'NOTICE')
    if not notice or notice['expiresAt']<=now or notice['flag']!=planning['flag'] or planning['flag']=='unknown':
        return []
    assembly=next((b for b in school.get('timetable',DEFAULT_BLOCKS) if b['name'].lower()=='assembly'),None)
    if not assembly:
        return []
    local=datetime.fromtimestamp(now,ZoneInfo(school['timezone']))
    hour,minute=map(int,assembly['start'].split(':'))
    remaining=hour*60+minute-15-(local.hour*60+local.minute)
    if not 0<=remaining<=15:
        return []
    day=local_day(school,now);key='AUTO_NUDGE#'+day
    if store.get(pk,key):
        return []
    reviewed={r['sub'] for r in store.query(pk,'RECEIPT#'+notice['id']+'#')}
    targets=[p for p in notice.get('audience',[]) if p['sub'] not in reviewed and p.get('role')!='kid']
    if not targets:
        return []
    event=dict(notice,id='deadline-'+day,planId=notice['id'],time=now,kind='plan-reminder',audience=targets)
    return emit_changes(store,school['id'],event,now)+[change(pk,key,{'time':now,'count':len(targets),'label':'Reminder queued; delivery preferences still apply'},expires=now+2*86400)]
