"""Cookie-authenticated local school workspace. Seeded accounts contain fictional data."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from http.cookies import SimpleCookie
from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, ForbiddenError, UnauthorizedError
from backend.functions.guardian_store import connection,configured_school
from backend.functions.air_engine import SCHOOLS,fetch_air,finite
from backend.functions.guardian_rules import child_risk,recommendations,AGE_GROUPS,FLAGS
from backend.functions.alert_engine import DEFAULT_PREFS,evaluate,role_message,local_time,planning_risk,persist_event,dispatch_push,push_configured
from backend.functions.route_engine import route_exposure

router=Router()


def payload():
    try:data=router.current_event.json_body
    except (ValueError,TypeError):raise BadRequestError('A valid JSON object is required.')
    if not isinstance(data,dict):raise BadRequestError('A JSON object is required.')
    return data


def session_token():
    cookie=SimpleCookie()
    try:cookie.load(router.current_event.headers.get('cookie',''))
    except Exception:return ''
    return cookie['guardian_session'].value if 'guardian_session' in cookie else ''


def current_user(roles=None,required=True):
    token=session_token()
    with connection() as db:
        row=db.execute('SELECT u.id,u.role,u.school,u.class_id FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',
                       (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone() if token else None
    if not row:
        if required:raise UnauthorizedError('Sign in to your school workspace.')
        return None
    user=dict(row)
    if roles and user['role'] not in roles:raise ForbiddenError('This action is not available to your role.')
    return user


def audit(db,user,action,body):
    db.execute('INSERT INTO history VALUES (?,?,?,?,?,?)',(secrets.token_hex(12),user['school'],user['id'],action,time.time(),json.dumps(body)))


@router.get('/session')
def session():return {'user':current_user(required=False),'localDemo':True}


@router.post('/login')
def login():
    data=payload();name=data.get('username');password=data.get('password')
    if not isinstance(name,str) or not isinstance(password,str) or len(name)>50 or len(password)>128:
        raise BadRequestError('Enter your account and password.')
    with connection() as db:
        attempt=db.execute('SELECT * FROM login_attempts WHERE user_id=?',(name,)).fetchone()
        if attempt and attempt['count']>=8 and time.time()-attempt['updated']<900:
            raise ForbiddenError('Too many attempts. Wait fifteen minutes.')
        user=db.execute('SELECT * FROM users WHERE id=?',(name,)).fetchone()
        salt=bytes.fromhex(user['salt']) if user else b'guardian-dummy-salt'
        digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,200000).hex()
        valid=user and hmac.compare_digest(digest,user['password'])
        if not valid:
            count=attempt['count']+1 if attempt and time.time()-attempt['updated']<900 else 1
            db.execute('INSERT INTO login_attempts VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET count=excluded.count,updated=excluded.updated',(name,count,time.time()))
            db.commit()
            raise UnauthorizedError('Account or password is incorrect.')
        db.execute('DELETE FROM login_attempts WHERE user_id=?',(name,))
        token=secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),name,time.time()+28800))
        public={key:user[key] for key in ('id','role','school','class_id')}
    return Response(status_code=200,content_type='application/json',body=json.dumps({'user':public}),
                    headers={'Set-Cookie':f'guardian_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})


@router.post('/logout')
def logout():
    token=session_token()
    with connection() as db:db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))
    return Response(status_code=200,content_type='application/json',body='{"user":null}',
                    headers={'Set-Cookie':'guardian_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})


def school_context(user):
    with connection() as db:state=dict(db.execute('SELECT * FROM school_state WHERE school=?',(user['school'],)).fetchone())
    air=fetch_air(configured_school(user['school']),state['mode'],bool(state['polluted']))
    risk=child_risk(air,'5-8')
    air.update(overrideFlag=state['override'],overrideUntil=state['override_until'],overrideReason=state['override_reason'])
    effective=planning_risk(air)
    return state,air,risk,effective


@router.get('/workspace')
def workspace():
    user=current_user();state,air,risk,effective=school_context(user)
    evaluate(user['school'],air)
    with connection() as db:
        today=local_time(time.time()).date().isoformat()
        prefs=db.execute('SELECT body FROM preferences WHERE user_id=?',(user['id'],)).fetchone()
        children=[];classes=[]
        if user['role']=='parent':
            for row in db.execute('SELECT id,alias,age_group,caution,budget,class_id FROM children WHERE parent_id=?',(user['id'],)):
                child=dict(row)
                child['exposure']=[dict(e) for e in db.execute('SELECT id,context,minutes,concentration FROM exposure WHERE child_id=? AND day=?',(child['id'],today))]
                child['exposureTotal']=round(sum(e['minutes']*e['concentration'] for e in child['exposure']),2)
                checkin=db.execute('SELECT signal FROM checkins WHERE child_id=? AND day=? ORDER BY created DESC LIMIT 1',(child['id'],today)).fetchone()
                child['checkin']=bool(checkin[0]) if checkin else None
                child['risk']=child_risk(air,child['age_group'],bool(child['caution']) or child['checkin'] is True);children.append(child)
        elif user['role']=='teacher':
            children=[{'id':r['id'],'alias':r['alias'],'extraCaution':bool(r['caution'])} for r in db.execute('SELECT id,alias,caution FROM children WHERE class_id=? AND school=?',(user['class_id'],user['school']))]
            classes=[dict(r) for r in db.execute('SELECT * FROM classes WHERE id=?',(user['class_id'],))]
        elif user['role']=='admin':classes=[dict(r) for r in db.execute('SELECT * FROM classes WHERE school=?',(user['school'],))]
        events=[json.loads(r['body']) for r in db.execute('SELECT body FROM events WHERE school=? ORDER BY created DESC LIMIT 20',(user['school'],))]
        notice_row=db.execute('SELECT body FROM events WHERE school=? AND kind=? ORDER BY created DESC LIMIT 1',(user['school'],'admin-announcement')).fetchone()
        school_notice=json.loads(notice_row['body']) if notice_row else None
        deliveries=[dict(r) for r in db.execute('SELECT d.* FROM deliveries d JOIN events e ON e.id=d.event_id WHERE d.user_id=? ORDER BY e.created DESC LIMIT 30',(user['id'],))]
        latest_notice=school_notice['id'] if school_notice else None
        acks=[dict(r) for r in db.execute('SELECT a.class_id,a.created,c.label FROM acknowledgments a JOIN classes c ON c.id=a.class_id WHERE a.event_id=?',(latest_notice,))] if latest_notice else []
        reviewed=db.execute('SELECT created FROM plan_reviews WHERE event_id=? AND user_id=?',(latest_notice,user['id'])).fetchone() if latest_notice else None
        review_count=db.execute('SELECT COUNT(*) FROM plan_reviews r JOIN users u ON u.id=r.user_id WHERE r.event_id=? AND u.school=? AND u.role=?',(latest_notice,user['school'],'parent')).fetchone()[0] if latest_notice and user['role']=='admin' else None
        parent_count=db.execute('SELECT COUNT(*) FROM users WHERE school=? AND role=?',(user['school'],'parent')).fetchone()[0] if user['role']=='admin' else None
        class_count=db.execute('''SELECT COUNT(DISTINCT c.id) FROM classes c JOIN users u ON u.class_id=c.id
            WHERE c.school=? AND u.role=?''',(user['school'],'teacher')).fetchone()[0] if user['role']=='admin' else None
        ack_times=[r['created'] for r in acks]
        review_times=[r[0] for r in db.execute('SELECT r.created FROM plan_reviews r JOIN users u ON u.id=r.user_id WHERE r.event_id=? AND u.school=? AND u.role=?',(latest_notice,user['school'],'parent'))] if latest_notice and user['role']=='admin' else []
        history=[dict(r) for r in db.execute('SELECT action,created,body FROM history WHERE school=? AND created>=? ORDER BY created DESC',(user['school'],time.time()-7*86400))] if user['role']=='admin' else []
        moved=db.execute('SELECT COALESCE(SUM(s.minutes),0) FROM schedule_changes s JOIN classes c ON c.id=s.class_id WHERE c.school=? AND s.day>=?',
                         (user['school'],local_time(time.time()-30*86400).date().isoformat())).fetchone()[0] if user['role']=='admin' else 0
        moved_today=db.execute('SELECT COALESCE(SUM(s.minutes),0) FROM schedule_changes s JOIN classes c ON c.id=s.class_id WHERE c.school=? AND s.day=?',(user['school'],today)).fetchone()[0] if user['role']=='admin' else 0
        week_start=time.time()-7*86400
        week_start_day=local_time(week_start).date().isoformat()
        moved_week=db.execute('SELECT COALESCE(SUM(s.minutes),0) FROM schedule_changes s JOIN classes c ON c.id=s.class_id WHERE c.school=? AND s.day>=?',(user['school'],week_start_day)).fetchone()[0] if user['role']=='admin' else 0
        weekly_notice_rows=[{'day':r['day'],'event':json.loads(r['body'])} for r in db.execute('SELECT day,body FROM events WHERE school=? AND kind=? AND created>=?',(user['school'],'admin-announcement',week_start))] if user['role']=='admin' else []
        weekly_indoor_days={row['day'] for row in weekly_notice_rows if row['event'].get('planType')=='indoor-pe'}
        weekly_event_ids=[row['event']['id'] for row in weekly_notice_rows]
        weekly_reviews=sum(db.execute('SELECT COUNT(*) FROM plan_reviews WHERE event_id=?',(event_id,)).fetchone()[0] for event_id in weekly_event_ids) if user['role']=='admin' else 0
        reports=[dict(r) for r in db.execute('SELECT r.id,r.category,r.note,r.created,u.role FROM reports r JOIN users u ON u.id=r.user_id WHERE r.school=? ORDER BY r.created DESC LIMIT 10',(user['school'],))]
        sensors=[dict(r) for r in db.execute('SELECT class_id,pm25,observed,source FROM sensor_readings WHERE school=? ORDER BY observed DESC LIMIT 6',(user['school'],))]
        if user['role']=='teacher':sensors=[s for s in sensors if s['class_id']==user['class_id']]
        if user['role']=='parent':sensors=[s for s in sensors if s['class_id'] in [c['class_id'] for c in children]]
        if user['role']=='staff':sensors=[]
        sensors=[dict(s,stale=time.time()-s['observed']>3600) for s in sensors]
        push_subscribed=bool(db.execute('SELECT 1 FROM push_subscriptions WHERE user_id=?',(user['id'],)).fetchone())
    prefs={**DEFAULT_PREFS,**(json.loads(prefs[0]) if prefs else {})}
    return {'user':user,'school':configured_school(user['school']),'state':state,'air':air,'risk':risk,'schoolFlag':effective,
            'actions':recommendations(air,effective,user['role'],next((v['pm25'] for v in sensors if not v['stale']),None)),'children':children,'classes':classes,'preferences':prefs,
            'events':[dict(e,message=role_message(e,user['role'],prefs['language'])) for e in events],
            'currentMessage':role_message({'flag':effective['flag']},user['role'],prefs['language']),'deliveries':deliveries,'acknowledgments':acks,'history':history,'reports':reports,'sensors':sensors,
            'planReview':{'reviewedAt':reviewed[0] if reviewed else None,'count':review_count,'parentAccounts':parent_count,'eventId':latest_notice},
            'schoolNotice':school_notice,
            'push':{'configured':push_configured(),'subscribed':push_subscribed,
                    'publicKey':os.environ.get('VAPID_PUBLIC_KEY') if push_configured() else None,
                    'receiptMeaning':'Accepted means the push service accepted the request; device display is not confirmed.'},
            'pilot':{'publishedAt':school_notice['time'] if school_notice else None,
                     'teacher':{'completed':len(acks),'eligible':class_count,'rate':round(len(acks)/class_count*100) if class_count else 0,
                                'medianMinutes':round(sorted([(v-school_notice['time'])/60 for v in ack_times])[len(ack_times)//2],1) if ack_times and school_notice else None},
                     'parent':{'completed':review_count,'eligible':parent_count,'rate':round(review_count/parent_count*100) if parent_count else 0,
                               'medianMinutes':round(sorted([(v-school_notice['time'])/60 for v in review_times])[len(review_times)//2],1) if review_times and school_notice else None},
                     'complete':bool(school_notice and class_count and len(acks)==class_count and parent_count and review_count==parent_count)} if user['role']=='admin' else None,
            'impact':{'minutesMovedToday':moved_today,'classHoursMovedIndoors':round(moved/60,2),
                      'weeklyIndoorNotices':len(weekly_indoor_days),'weeklyClassHoursMovedIndoors':round(moved_week/60,2),
                      'weeklyParentReviewRate':round(weekly_reviews/(len(weekly_event_ids)*parent_count)*100) if weekly_event_ids and parent_count else 0,
                      'meaning':'Teacher-recorded timetable changes and review receipts, not measured pollution reduction'},'localDemo':True}


def shared_token_row(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{20,80}',token):raise BadRequestError('This school-plan link is invalid.')
    digest=hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        row=db.execute('''SELECT t.token_hash,t.event_id,t.user_id,t.expires,t.used,e.body,s.name school_name
            FROM plan_share_tokens t JOIN events e ON e.id=t.event_id JOIN users u ON u.id=t.user_id JOIN schools s ON s.id=u.school
            WHERE t.token_hash=?''',(digest,)).fetchone()
    if not row or row['expires']<time.time():raise BadRequestError('This school-plan link has expired. Ask the school for a new link.')
    return dict(row)


@router.post('/share-plan')
def share_plan():
    user=current_user(['parent'])
    with connection() as db:
        latest=db.execute('SELECT id FROM events WHERE school=? AND kind=? ORDER BY created DESC LIMIT 1',(user['school'],'admin-announcement')).fetchone()
        if not latest:raise BadRequestError('No school plan published for today.')
        token=secrets.token_urlsafe(24);digest=hashlib.sha256(token.encode()).hexdigest()
        db.execute('DELETE FROM plan_share_tokens WHERE user_id=? OR expires<?',(user['id'],time.time()))
        db.execute('INSERT INTO plan_share_tokens VALUES (?,?,?,?,?)',(digest,latest[0],user['id'],time.time()+48*3600,None))
    return {'path':f'/?share={token}','expiresInHours':48}


@router.get('/shared-plan/<token>')
def shared_plan(token):
    row=shared_token_row(token);event=json.loads(row['body'])
    return {'school':row['school_name'],'flag':event['flag'],'notice':' '.join(event.get('reasons',[])),
            'publishedAt':event['time'],'reviewed':bool(row['used']),'expiresAt':row['expires']}


@router.post('/shared-plan/<token>/review')
def shared_plan_review(token):
    row=shared_token_row(token)
    with connection() as db:
        db.execute('INSERT INTO plan_reviews VALUES (?,?,?) ON CONFLICT(event_id,user_id) DO NOTHING',(row['event_id'],row['user_id'],time.time()))
        db.execute('UPDATE plan_share_tokens SET used=? WHERE token_hash=?',(time.time(),row['token_hash']))
    return {'reviewed':True}


@router.post('/profiles/<child_id>')
def profile(child_id):
    user=current_user(['parent']);data=payload()
    alias=data.get('alias');age=data.get('ageGroup');caution=data.get('caution')
    budget=data.get('budget')
    if not isinstance(alias,str) or not 1<=len(alias.strip())<=30 or age not in AGE_GROUPS or not isinstance(caution,bool):
        raise BadRequestError('Use a short alias, a supported age group and a caution choice.')
    if budget is not None and (not finite(budget) or not 100<=budget<=300000):raise BadRequestError('Use a planning budget from 100 to 300000 µg·min/m³.')
    with connection() as db:
        if not db.execute('SELECT 1 FROM children WHERE id=? AND parent_id=?',(child_id,user['id'])).fetchone():raise ForbiddenError('This child profile is not linked to your account.')
        db.execute('UPDATE children SET alias=?,age_group=?,caution=? WHERE id=?',(alias.strip(),age,int(caution),child_id))
        if budget is not None:db.execute('UPDATE children SET budget=? WHERE id=?',(budget,child_id))
    return {'saved':True}


@router.post('/exposure')
def exposure_entry():
    user=current_user(['parent']);data=payload()
    child_id=data.get('childId');minutes=data.get('minutes');concentration=data.get('concentration');context=data.get('context')
    if not isinstance(minutes,int) or isinstance(minutes,bool) or not 1<=minutes<=720 or not finite(concentration) or not 0<=concentration<=2000 or context not in ('commute','outdoor','indoor'):
        raise BadRequestError('Use commute/outdoor/indoor, 1–720 minutes and a PM2.5 concentration from 0 to 2000 µg/m³.')
    today=local_time(time.time()).date().isoformat()
    with connection() as db:
        if not db.execute('SELECT 1 FROM children WHERE id=? AND parent_id=?',(child_id,user['id'])).fetchone():raise ForbiddenError('This child is not linked to your account.')
        used=db.execute('SELECT COALESCE(SUM(minutes),0) FROM exposure WHERE child_id=? AND day=?',(child_id,today)).fetchone()[0]
        if used+minutes>1440:raise BadRequestError('A day cannot contain more than 1440 recorded minutes.')
        db.execute('INSERT INTO exposure VALUES (?,?,?,?,?,?,?)',(secrets.token_hex(12),child_id,today,context,minutes,concentration,time.time()))
    return {'saved':True}


@router.delete('/exposure/<entry_id>')
def delete_exposure(entry_id):
    user=current_user(['parent'])
    with connection() as db:
        if not db.execute('SELECT 1 FROM exposure e JOIN children c ON c.id=e.child_id WHERE e.id=? AND c.parent_id=?',(entry_id,user['id'])).fetchone():raise ForbiddenError('This record is not linked to your account.')
        db.execute('DELETE FROM exposure WHERE id=?',(entry_id,))
    return {'deleted':True}


@router.post('/routes')
def compare_routes():
    user=current_user(['parent','admin']);data=payload();state,air,risk,effective=school_context(user)
    if not isinstance(data.get('routes'),list) or len(data['routes'])!=2:raise BadRequestError('Enter two routes.')
    results=[]
    for route in data['routes']:
        if not isinstance(route,dict):raise BadRequestError('Use a route object.')
        try:results.append(route_exposure(configured_school(user['school']),air['stations'],route.get('path'),route.get('minutes')))
        except ValueError as error:raise BadRequestError(str(error))
    lower=None
    if all(r['available'] for r in results):lower=0 if results[0]['proxy']<results[1]['proxy'] else 1 if results[1]['proxy']<results[0]['proxy'] else None
    return {'routes':results,'lowerProxyIndex':lower,'mode':state['mode'],'stations':air['stations'],'school':air['school']}


@router.post('/checkin')
def checkin():
    user=current_user(['parent']);data=payload()
    if not isinstance(data.get('signal'),bool):raise BadRequestError('Choose yes or no.')
    with connection() as db:
        if not db.execute('SELECT 1 FROM children WHERE id=? AND parent_id=?',(data.get('childId'),user['id'])).fetchone():raise ForbiddenError('This child is not linked to your account.')
        day=local_time(time.time()).date().isoformat()
        db.execute('DELETE FROM checkins WHERE child_id=? AND day=?',(data['childId'],day))
        db.execute('INSERT INTO checkins VALUES (?,?,?,?,?)',(secrets.token_hex(12),data['childId'],day,int(data['signal']),time.time()))
        db.execute('DELETE FROM checkins WHERE created<?',(time.time()-30*86400,))
    return {'saved':True}


@router.post('/observations')
def observation():
    user=current_user();data=payload();note=data.get('note');category=data.get('category')
    if not isinstance(note,str) or not 1<=len(note.strip())<=240 or category not in ('smoke','dust','traffic','indoor'):
        raise BadRequestError('Choose a category and enter 1–240 characters. Do not include personal information.')
    with connection() as db:db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)',(secrets.token_hex(12),user['school'],user['id'],category,note.strip(),time.time()))
    return {'saved':True}


@router.post('/sensor')
def sensor_demo():
    user=current_user(['admin']);data=payload()
    if not finite(data.get('pm25')) or not 0<=data['pm25']<=2000:raise BadRequestError('Use a valid PM2.5 concentration.')
    with connection() as db:
        if not db.execute('SELECT 1 FROM classes WHERE id=? AND school=?',(data.get('classId'),user['school'])).fetchone():raise ForbiddenError('Choose a class in your school.')
        db.execute('INSERT INTO sensor_readings VALUES (?,?,?,?,?,?)',(secrets.token_hex(12),user['school'],data['classId'],data['pm25'],time.time(),'Manual demo sensor fixture'))
    return {'saved':True}


@router.post('/preferences')
def preferences():
    user=current_user();data=payload()
    if data.get('language') not in ('en','hi','mr') or not isinstance(data.get('channels'),list) or not data['channels'] or len(data['channels'])>4 or any(c not in ('in-app','push','sms','whatsapp') for c in data['channels']):
        raise BadRequestError('Choose a language and at least one supported channel.')
    if any(not isinstance(data.get(k),str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',data[k]) for k in ('quietStart','quietEnd')):
        raise BadRequestError('Use valid quiet-hour times.')
    if not isinstance(data.get('dailyCap'),int) or isinstance(data['dailyCap'],bool) or not 1<=data['dailyCap']<=10 or not isinstance(data.get('morning'),bool):
        raise BadRequestError('Choose a cap from 1 to 10 and a morning preference.')
    clean={key:data[key] for key in DEFAULT_PREFS};clean['channels']=list(dict.fromkeys(clean['channels']))
    with connection() as db:db.execute('INSERT INTO preferences VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body',(user['id'],json.dumps(clean)))
    return {'saved':True}


@router.post('/push-subscription')
def push_subscription():
    user=current_user();data=payload();subscription=data.get('subscription')
    if subscription is None:
        with connection() as db:db.execute('DELETE FROM push_subscriptions WHERE user_id=?',(user['id'],))
        return {'subscribed':False}
    endpoint=subscription.get('endpoint') if isinstance(subscription,dict) else None
    keys=subscription.get('keys') if isinstance(subscription,dict) else None
    p256dh=keys.get('p256dh') if isinstance(keys,dict) else None
    auth=keys.get('auth') if isinstance(keys,dict) else None
    if not push_configured():raise BadRequestError('Web Push is not configured on the server.')
    if not isinstance(endpoint,str) or not endpoint.startswith('https://') or len(endpoint)>2048 or not all(isinstance(v,str) and 8<=len(v)<=512 and re.fullmatch(r'[A-Za-z0-9_-]+',v) for v in (p256dh,auth)):
        raise BadRequestError('The browser returned an invalid push subscription.')
    with connection() as db:
        db.execute('INSERT INTO push_subscriptions VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET endpoint=excluded.endpoint,p256dh=excluded.p256dh,auth=excluded.auth,created=excluded.created',(user['id'],endpoint,p256dh,auth,time.time()))
    return {'subscribed':True}


@router.post('/school')
def school_control():
    user=current_user(['admin']);data=payload()
    mode=data.get('mode');polluted=data.get('polluted')
    if mode not in ('demo','live') or not isinstance(polluted,bool):raise BadRequestError('Choose a data mode and a simulation setting.')
    lat=data.get('lat');lon=data.get('lon')
    if lat is not None or lon is not None:
        if not finite(lat) or not finite(lon) or abs(lat)>90 or abs(lon)>180:raise BadRequestError('Use valid campus coordinates.')
    with connection() as db:
        if lat is not None:db.execute('UPDATE schools SET lat=?,lon=? WHERE id=?',(lat,lon,user['school']))
        db.execute('UPDATE school_state SET mode=?,polluted=?,updated=? WHERE school=?',(mode,int(polluted),time.time(),user['school']))
        audit(db,user,'school-data-setting',{'mode':mode,'polluted':polluted})
    state,air,risk,effective=school_context(user);event=evaluate(user['school'],air)
    return {'saved':True,'event':event}


@router.post('/override')
def override():
    user=current_user(['admin']);data=payload();flag=data.get('flag');reason=data.get('reason','').strip() if isinstance(data.get('reason',''),str) else ''
    if flag not in FLAGS+['automatic'] or (flag!='automatic' and not 5<=len(reason)<=200):raise BadRequestError('Choose a flag and explain the change in 5–200 characters.')
    state,air,risk,effective=school_context(user)
    if flag!='automatic' and (risk['flag']=='unknown' or FLAGS.index(flag)<FLAGS.index(risk['flag'])):
        raise BadRequestError('Overrides may raise the planning flag, not lower the current automatic recommendation.')
    with connection() as db:
        db.execute('UPDATE school_state SET override=?,override_reason=?,override_until=? WHERE school=?',(None if flag=='automatic' else flag,reason,None if flag=='automatic' else time.time()+14400,user['school']))
        audit(db,user,'flag-override',{'flag':flag,'reason':reason,'expiresInHours':4})
    _,air,_,_=school_context(user);evaluate(user['school'],air)
    return {'saved':True}


@router.post('/announce')
def announce():
    user=current_user(['admin']);data=payload();note=data.get('note','')
    plan_type=data.get('planType','indoor-pe')
    if plan_type not in ('indoor-pe','custom') or not isinstance(note,str) or not 1<=len(note.strip())<=300:raise BadRequestError('Choose a notice type and enter a short announcement.')
    state,air,risk,effective=school_context(user)
    evaluate(user['school'],air)
    if effective['flag']=='unknown':raise BadRequestError('Verify conditions before announcing a flag.')
    now=time.time();event={'id':secrets.token_hex(12),'school':user['school'],'flag':effective['flag'],'kind':'admin-announcement','planType':plan_type,'time':now,'reasons':[note.strip()],'mode':state['mode']}
    with connection() as db:
        persist_event(db,event)
        audit(db,user,'announcement',{'eventId':event['id'],'note':note.strip()})
    dispatch_push(event)
    return {'event':event}


@router.post('/acknowledge')
def acknowledge():
    user=current_user(['teacher']);data=payload();event_id=data.get('eventId')
    if not isinstance(data.get('checks'),list) or len(data['checks'])!=3 or not all(v is True for v in data['checks']) or not isinstance(data.get('minutesMoved'),int) or isinstance(data['minutesMoved'],bool) or not 0<=data['minutesMoved']<=240:
        raise BadRequestError('Complete the class checklist and enter 0–240 minutes moved indoors.')
    with connection() as db:
        latest=db.execute('SELECT id FROM events WHERE school=? AND kind=? ORDER BY created DESC LIMIT 1',(user['school'],'admin-announcement')).fetchone()
        if not latest or latest[0]!=event_id:raise BadRequestError('Refresh and acknowledge the latest published school notice.')
        db.execute('INSERT OR REPLACE INTO acknowledgments VALUES (?,?,?,?)',(event_id,user['class_id'],user['id'],time.time()))
        db.execute('INSERT INTO schedule_changes VALUES (?,?,?,?) ON CONFLICT(class_id,day) DO UPDATE SET minutes=MAX(minutes,excluded.minutes),event_id=excluded.event_id',
                   (user['class_id'],local_time(time.time()).date().isoformat(),data['minutesMoved'],event_id))
        audit(db,user,'class-acknowledged',{'eventId':event_id,'classId':user['class_id']})
    return {'saved':True}


@router.post('/review-plan')
def review_plan():
    user=current_user(['parent']);data=payload();event_id=data.get('eventId')
    with connection() as db:
        latest=db.execute('SELECT id FROM events WHERE school=? AND kind=? ORDER BY created DESC LIMIT 1',(user['school'],'admin-announcement')).fetchone()
        if not latest or latest[0]!=event_id:
            raise BadRequestError('The school plan has changed. Refresh and review the latest notice.')
        db.execute('INSERT INTO plan_reviews VALUES (?,?,?) ON CONFLICT(event_id,user_id) DO NOTHING',(event_id,user['id'],time.time()))
    return {'reviewed':True}
