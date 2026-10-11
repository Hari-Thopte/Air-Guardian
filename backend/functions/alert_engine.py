"""One alert event, multiple role templates. No outbound messages in local demo."""
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from backend.functions.guardian_store import connection
from backend.functions.guardian_rules import child_risk, FLAGS
from backend.functions.air_engine import timestamp, finite

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_PREFS={'language':'en','channels':['in-app'],'quietStart':'21:00','quietEnd':'06:00','dailyCap':4,'morning':True}


def push_configured():
    return all(os.environ.get(name) for name in ('VAPID_PUBLIC_KEY','VAPID_PRIVATE_KEY','VAPID_SUBJECT'))


def dispatch_push(event):
    """Send queued Web Push messages. Acceptance is not a device delivery receipt."""
    with connection() as db:
        rows=[dict(row) for row in db.execute('''SELECT d.user_id,d.body,s.endpoint,s.p256dh,s.auth
            FROM deliveries d JOIN push_subscriptions s ON s.user_id=d.user_id
            WHERE d.event_id=? AND d.channel='push' AND d.status='push-pending' ''',(event['id'],))]
    if not rows:
        return
    try:
        from pywebpush import webpush
    except ImportError:
        with connection() as db:
            db.execute("UPDATE deliveries SET status='push-dependency-missing' WHERE event_id=? AND channel='push' AND status='push-pending'",(event['id'],))
        return
    for row in rows:
        status='accepted-by-push-service'
        try:
            webpush(subscription_info={'endpoint':row['endpoint'],'keys':{'p256dh':row['p256dh'],'auth':row['auth']}},
                    data=json.dumps({'title':'Air Guardian school instruction','body':row['body'],'url':'/?page=guardian'}),
                    vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],vapid_claims={'sub':os.environ['VAPID_SUBJECT']},ttl=3600)
        except Exception:
            status='push-send-failed'
        with connection() as db:
            db.execute('UPDATE deliveries SET status=? WHERE event_id=? AND user_id=? AND channel=?',(status,event['id'],row['user_id'],'push'))


def local_time(now):
    return datetime.fromtimestamp(now,IST)


def in_quiet(now, start, end):
    current=local_time(now).strftime('%H:%M')
    return start <= current < end if start < end else current >= start or current < end if start != end else False


def _legacy_role_message(event,role,language='en'):
    flag=event['flag']
    instruction={'green':'Check the usual school plan.','yellow':'Keep outdoor activities gentle.','orange':'Review indoor PE and reduce waiting at the gate.','red':'Use the reviewed indoor plan and rotate outdoor duties.','unknown':'Ask staff to verify current air conditions.'}[flag]
    if language=='hi':
        instruction={'green':'स्कूल की सामान्य योजना देखें।','yellow':'बाहर की गतिविधियाँ हल्की रखें।','orange':'इनडोर खेल की योजना देखें और गेट पर इंतजार कम करें।','red':'स्वीकृत इनडोर योजना अपनाएँ और बाहरी ड्यूटी बदलें।','unknown':'हवा की स्थिति की पुष्टि करें।'}[flag]
    elif language=='mr':
        instruction={'green':'शाळेची नेहमीची योजना तपासा.','yellow':'मैदानी उपक्रम हलके ठेवा.','orange':'वर्गातील खेळाची योजना तपासा आणि गेटवरील थांबा कमी करा.','red':'मान्य केलेली वर्गातील योजना पाळा आणि बाहेरील ड्युटी बदलत राहा.','unknown':'हवेच्या स्थितीची खात्री करा.'}[flag]
    role_suffix={'parent':'Review this with your child before departure.','teacher':'Review your class checklist and acknowledge the plan.','staff':'Ask your supervisor about mask suitability and duty rotation.','admin':'Review the schedule and class acknowledgments.'}.get(role,'')
    if language!='en':role_suffix=''
    prefix='स्कूल संकेत' if language=='hi' else 'शाळेचा इशारा' if language=='mr' else 'School flag'
    return f"{prefix}: {flag.upper()}. {instruction} {role_suffix}".strip()


def role_message(event,role,language='en'):
    flag=event['flag']
    copy={
        'en':{
            'prefix':'School flag','green':'Check the usual school plan.','yellow':'Keep outdoor activities gentle.',
            'orange':'Review indoor PE and reduce waiting at the gate.','red':'Use the reviewed indoor plan and rotate outdoor duties.',
            'unknown':'Ask staff to verify current air conditions.',
            'parent':'Review this with your child before departure.','teacher':'Review your class checklist and acknowledge the plan.',
            'staff':'Ask your supervisor about mask suitability and duty rotation.','admin':'Review the schedule and class acknowledgments.'},
        'hi':{
            'prefix':'स्कूल संकेत','green':'स्कूल की सामान्य योजना देखें।','yellow':'बाहर की गतिविधियाँ हल्की रखें।',
            'orange':'इनडोर खेल की योजना देखें और गेट पर इंतज़ार कम करें।','red':'स्वीकृत इनडोर योजना अपनाएँ और बाहरी ड्यूटी बदलें।',
            'unknown':'कर्मचारियों से हवा की मौजूदा स्थिति की पुष्टि कराएँ।',
            'parent':'घर से निकलने से पहले बच्चे के साथ इसकी समीक्षा करें।','teacher':'कक्षा की सूची पूरी करके योजना की पुष्टि करें।',
            'staff':'मास्क की उपयुक्तता और ड्यूटी बदलने के बारे में पर्यवेक्षक से पूछें।','admin':'समय-सारणी और कक्षाओं की पुष्टि देखें।'},
        'mr':{
            'prefix':'शाळेचा इशारा','green':'शाळेची नेहमीची योजना तपासा.','yellow':'मैदानी उपक्रम हलके ठेवा.',
            'orange':'वर्गातील खेळाची योजना तपासा आणि गेटवरील थांबा कमी करा.','red':'मान्य केलेली वर्गातील योजना पाळा आणि बाहेरील ड्युटी बदलत राहा.',
            'unknown':'कर्मचाऱ्यांकडून हवेच्या सध्याच्या स्थितीची खात्री करा.',
            'parent':'घरातून निघण्यापूर्वी मुलासोबत याचा आढावा घ्या.','teacher':'वर्गाची यादी पूर्ण करून योजना मान्य करा.',
            'staff':'मास्कची योग्यता आणि ड्युटी बदलाबद्दल पर्यवेक्षकांना विचारा.','admin':'वेळापत्रक आणि वर्गांच्या पुष्टी तपासा.'}}
    language_copy=copy.get(language,copy['en'])
    return f"{language_copy['prefix']}: {flag.upper()}. {language_copy[flag]} {language_copy.get(role,'')}".strip()


def planning_risk(air, now=None):
    risk=child_risk(air,'5-8')
    flag=air.get('overrideFlag')
    if risk['flag'] in FLAGS and flag in FLAGS and (air.get('overrideUntil') or 0)>(now or time.time()) and FLAGS.index(flag)>=FLAGS.index(risk['flag']):
        risk=dict(risk,flag=flag,reasons=risk['reasons']+[f"Administrator raised the flag: {air.get('overrideReason','')}"])
    return risk


def persist_event(db,event):
    now=event['time'];day=local_time(now).date().isoformat();school=event['school']
    db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',(event['id'],school,event['flag'],event['kind'],day,now,json.dumps(event)))
    for user in db.execute('SELECT id,role FROM users WHERE school=?',(school,)).fetchall():
        saved=db.execute('SELECT body FROM preferences WHERE user_id=?',(user['id'],)).fetchone()
        prefs={**DEFAULT_PREFS,**(json.loads(saved[0]) if saved else {})}
        message=role_message(event,user['role'],prefs['language'])
        for channel in prefs['channels']:
            if in_quiet(now,prefs['quietStart'],prefs['quietEnd']):
                status='suppressed-quiet-hours'
            elif channel=='in-app':
                status='in-app'
            elif channel=='push':
                subscribed=db.execute('SELECT 1 FROM push_subscriptions WHERE user_id=?',(user['id'],)).fetchone()
                status='push-pending' if push_configured() and subscribed else 'push-not-subscribed' if push_configured() else 'push-not-configured'
            else:
                status='mock-not-sent'
            today=db.execute('SELECT COUNT(*) FROM deliveries d JOIN events e ON e.id=d.event_id WHERE d.user_id=? AND e.day=? AND d.channel=? AND d.status NOT LIKE "suppressed%"',(user['id'],day,channel)).fetchone()[0]
            if today>=prefs['dailyCap']:status='suppressed-daily-cap'
            if event["kind"]=="morning-forecast" and not prefs['morning']:status='suppressed-preference'
            db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?)',(event['id'],user['id'],channel,status,message))


def evaluate(school,air,now=None,morning=False):
    now=now or time.time()
    local=local_time(now);day=local.date().isoformat()
    risk=planning_risk(air,now)
    if morning:
        upcoming=[p for p in air.get('forecast',[]) if timestamp(p.get('time')) is not None and 0 < timestamp(p['time'])-now <= 3*3600 and finite(p.get('pm25')) and p['pm25']>=0]
        if not upcoming:return None
        from backend.functions.air_engine import particle_index
        concentration=max(p['pm25'] for p in upcoming)
        risk=planning_risk(dict(air,aqi=particle_index(concentration),pm25=concentration,stale=False),now)
    if risk['flag']=='unknown':return None
    with connection() as db:
        row=db.execute('SELECT * FROM alert_state WHERE school=?',(school,)).fetchone()
        if row and ((morning and row['morning_day']==day) or (not morning and row['flag']==risk['flag'])):return None
        count=db.execute('SELECT COUNT(*) FROM events WHERE school=? AND day=? AND kind!=?',(school,day,'admin-announcement')).fetchone()[0]
        if count>=4:return None
        event={'id':secrets.token_hex(12),'school':school,'flag':risk['flag'],'kind':'morning-forecast' if morning else 'threshold-change',
               'time':now,'reasons':risk['reasons'],'mode':air.get('mode','unknown')}
        persist_event(db,event)
        db.execute('INSERT INTO alert_state VALUES (?,?,?) ON CONFLICT(school) DO UPDATE SET flag=excluded.flag,morning_day=excluded.morning_day',
                   (school,risk['flag'],day if morning else row['morning_day'] if row else None))
    dispatch_push(event)
    return event


def morning_due(now=None):
    current=local_time(now or time.time())
    return current.hour==6 and 30<=current.minute<40


def monitor_tick():
    from backend.functions.air_engine import fetch_air
    from backend.functions.guardian_store import configured_school
    with connection() as db:states=[dict(r) for r in db.execute('SELECT * FROM school_state')]
    for state in states:
        air=fetch_air(configured_school(state['school']),state['mode'],bool(state['polluted']))
        air.update(overrideFlag=state['override'],overrideUntil=state['override_until'],overrideReason=state['override_reason'])
        evaluate(state['school'],air,morning=morning_due())
