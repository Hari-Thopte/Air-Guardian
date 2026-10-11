"""HTTP API v2 application. Cognito authenticates identity; database memberships authorize access."""
import base64
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlsplit
from backend.functions.air_engine import estimate, timestamp, particle_index
from backend.functions.guardian_rules import AGE_GROUPS
from cloud.contracts import Problem, DEFAULT_PREFS, ROLES, text, identifier, number, integer, preferences, school as validate_school, local_day, quiet
from cloud.store import DynamoStore, change, public, Conflict
from cloud.policy import plan
from cloud.pipeline import emit_changes, history
from cloud.channels import enabled_channels
from cloud.planning_tools import cleanest_windows, kid_workspace
from cloud.privacy import erase_private
from cloud.dayplan import presentation, receipt_summary, health, morning_brief, outdoor_summary, reminder_state


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def member(store, school_id, subject, roles=None):
    row = store.get('SCHOOL#' + identifier(school_id), 'MEMBER#' + subject)
    if not row or not row.get('active') or (roles and row['role'] not in roles):
        raise Problem('You do not have access to this school or action.', 403)
    return row


def verified_contact(token):
    import boto3
    attributes = {a['Name']: a['Value'] for a in boto3.client('cognito-idp').get_user(AccessToken=token)['UserAttributes']}
    if attributes.get('email_verified') != 'true' or not attributes.get('email'):
        raise Problem('Verify your email address before enrollment or email alerts.', 403)
    return attributes['email'].strip().lower()


def verified_phone(token):
    import boto3
    import re
    attrs = {a['Name']: a['Value'] for a in boto3.client('cognito-idp').get_user(AccessToken=token)['UserAttributes']}
    phone = attrs.get('phone_number', '')
    if attrs.get('phone_number_verified') != 'true' or not re.fullmatch(r'\+[1-9]\d{7,14}', phone):
        raise Problem('Verify a phone number in Cognito before enabling phone notifications.', 403)
    return phone


def validate_push(value):
    if not isinstance(value, dict):
        raise Problem('Invalid push subscription.')
    endpoint = text(value.get('endpoint'), 'Push endpoint', 2048)
    url = urlsplit(endpoint)
    host = url.hostname or ''
    allowed = host in ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com') or host.endswith('.notify.windows.com')
    if url.scheme != 'https' or not allowed or url.username or url.password or url.port not in (None, 443):
        raise Problem('Unsupported browser push service.')
    keys = value.get('keys')
    if not isinstance(keys, dict):
        raise Problem('Invalid push keys.')
    try:
        p256dh = base64.urlsafe_b64decode(keys['p256dh'] + '=' * (-len(keys['p256dh']) % 4))
        auth = base64.urlsafe_b64decode(keys['auth'] + '=' * (-len(keys['auth']) % 4))
        if len(p256dh) != 65 or p256dh[0] != 4 or len(auth) != 16:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise Problem('Invalid push key encoding.')
    return {'endpoint': endpoint, 'keys': {'p256dh': keys['p256dh'], 'auth': keys['auth']}}


def workspace(store, school_id, who):
    pk = 'SCHOOL#' + school_id
    config = store.get(pk, 'CONFIG')
    if not config:
        raise Problem('School configuration unavailable.', 404)
    current = store.get(pk, 'CURRENT') or {}
    air = current.get('air') or dict(estimate(config, []), source='Awaiting scheduled ingestion', forecast=[], providers=[], mode='live', stale=True)
    planning = plan(air, config, role=who['role'])
    stability = current.get('stability') or {}
    if not air.get('demoScenario') and stability.get('flag') in ('green', 'yellow', 'orange', 'red'):
        air = dict(air, stabilizedFlag=stability['flag'])
        planning = plan(air, config, role=who['role'])
    if who['role']=='kid':
        return kid_workspace(config,planning,store.get(pk,'NOTICE'),time.time(), example=bool(air.get('demoScenario')))
    children = store.query(pk, 'CHILD#', limit=500) if who['role'] in ('parent', 'teacher') else []
    if who['role'] == 'parent':
        parent_children = []
        for c in children:
            if who['sub'] not in c['guardians']:
                continue
            checkin = store.get('USER#' + who['sub'], f"CHECKIN#{school_id}#{c['id']}#{local_day(config)}")
            exposure = store.get('USER#' + who['sub'], f"EXPOSURE#{school_id}#{c['id']}#{local_day(config)}")
            parent_children.append(dict(c, checkin=checkin, exposure=exposure,
                planning=plan(air, config, c['age_group'], c.get('caution', False) or bool(checkin and checkin['signal']))))
        children = parent_children
        children = [{k: v for k, v in c.items() if k != 'guardians'} for c in children]
    elif who['role'] == 'teacher':
        children = [{'id': c['id'], 'alias': c['alias'], 'extraCaution': c.get('caution', False)} for c in children if c['class_id'] == who.get('class_id')]
    notice = store.get(pk, 'NOTICE')
    receipts = store.query(pk, 'RECEIPT#' + notice['id'] + '#', limit=1000) if notice else []
    if who['role'] not in ('admin', 'teacher'):
        receipts = [r for r in receipts if r['sub'] == who['sub']]
    elif who['role'] == 'teacher':
        receipts = [r for r in receipts if r.get('class_id') == who.get('class_id')]
    members = store.query(pk, 'MEMBER#', limit=500) if who['role'] == 'admin' else []
    prefs = store.get('USER#' + who['sub'], 'PREFERENCES') or DEFAULT_PREFS
    events = store.query(pk, 'EVENT#', reverse=True, limit=20)
    if who['role'] != 'admin':
        notice = {k: v for k, v in notice.items() if k != 'audience'} if notice else None
        events = [{k: v for k, v in e.items() if k != 'audience'} for e in events]
    sensors = store.query(pk, 'SENSOR#', limit=100) if who['role'] == 'admin' else []
    for sensor in sensors:
        sensor['online'] = time.time() - sensor.get('lastSeen', 0) <= 900
        if not sensor['online']:
            sensor['quality'] = 'stale'
    return public({'school': config, 'membership': who, 'air': air, 'planning': planning, 'children': children,
                   'dataHealth': health(air), 'cleanestWindows':cleanest_windows(air,config,time.time()), 'stability':current.get('stability'), 'morningBrief':morning_brief(air,config),
                   'outdoorSummary':outdoor_summary(config,planning,air),
                   'notificationUsage': {'channels': {c: (store.get('USER#'+who['sub'], f"CAP#{school_id}#{local_day(config)}#{c}") or {}).get('count',0) for c in prefs.get('channels',DEFAULT_PREFS['channels'])}, 'quietNow':quiet({**DEFAULT_PREFS,**prefs},config,time.time())},
                   'checklist': notice.get('checklist',[]) if notice else [],
                   'completions': [r for r in (store.query(pk,'TASK#'+notice['id']+'#') if notice else []) if who['role']=='admin' or r['sub']==who['sub']],
                   'dayPlan': presentation(config, planning),
                   'deadlineNudge':store.get(pk,'AUTO_NUDGE#'+local_day(config)) if who['role']=='admin' else None,
                   'reminderState':reminder_state(store,school_id,config,notice,receipts) if who['role']=='admin' else None,
                   'receiptSummary': receipt_summary(notice, receipts, members) if who['role'] == 'admin' else None,
                   'notice': notice, 'receipts': receipts, 'preferences': prefs, 'events': events,
                   'members': members, 'sensors': sensors, 'lastSuccessfulIngestion': current.get('lastSuccessfulAt'),
                   'devices':store.query(pk,'DEVICE#',limit=100) if who['role']=='admin' else [],
                   'classes': store.query(pk, 'CLASS#', limit=100) if who['role'] in ('teacher', 'admin') else [],
                   'rooms': store.query(pk, 'ROOM#', limit=100),
                   'pushPublicKey': os.environ.get('VAPID_PUBLIC_KEY', ''),
                   'enabledChannels': enabled_channels(),
                   'deliveries': store.query('USER#' + who['sub'], 'DELIVERY#' + school_id + '#', reverse=True, limit=30)})


def application(store, readings, method, path, data, query, subject, contact=None, phone=None):
    """Pure request boundary; subject must come from trusted gateway claims, never JSON."""
    upk = 'USER#' + subject
    if method == 'GET' and path == '/v1/session':
        memberships = []
        for link in store.query(upk, 'SCHOOL#', limit=100):
            row = store.get('SCHOOL#' + link['school'], 'MEMBER#' + subject)
            if row and row.get('active'):
                memberships.append(row)
        return {'sub': subject, 'memberships': public(memberships)}
    if method == 'POST' and path == '/v1/enroll':
        for link in store.query(upk, 'SCHOOL#', limit=100):
            linked = store.get('SCHOOL#' + link['school'], 'MEMBER#' + subject)
            if linked and linked.get('active') and linked.get('role') == 'kid':
                raise Problem('Kid accounts are read-only.', 403)
        token = text(data.get('token'), 'Invitation token', 100, 20)
        invite = store.get('INVITES', digest(token))
        if not invite or invite.get('used') or invite['expiresAt'] <= time.time():
            raise Problem('Invitation is invalid or expired.', 403)
        if not contact or digest(contact.lower()) != invite['emailHash']:
            raise Problem('Sign in using the verified email invited by your school.', 403)
        pk = 'SCHOOL#' + invite['school']
        if store.get('ERASURE', invite['school'] + '#' + subject):
            raise Problem('Previous school unlink cleanup is still running. Retry shortly.', 409)
        issuer = store.get(pk, 'MEMBER#' + invite['issuer'])
        if not issuer or not issuer['active'] or issuer['role'] != 'admin':
            raise Problem('Invitation issuer is no longer an active administrator.', 403)
        existing = store.get(pk, 'MEMBER#' + subject)
        if existing:
            raise Problem('This account already has a membership. Ask the administrator to update it.', 409)
        row = {'sub': subject, 'school': invite['school'], 'role': invite['role'], 'class_id': invite.get('class_id'), 'active': True}
        changes = [change(pk, 'MEMBER#' + subject, row), change(upk, pk, {'school': invite['school']}),
                   change('INVITES', digest(token), dict(invite, used=True), invite, invite['expiresAt'])]
        for cid in invite.get('children', []):
            child = store.get(pk, 'CHILD#' + cid)
            if not child:
                raise Problem('Invitation child no longer exists.', 409)
            changes.append(change(pk, 'CHILD#' + cid, dict(child, guardians=sorted(set(child['guardians'] + [subject]))), child))
        store.commit(changes)
        return {'enrolled': True, 'school': invite['school']}
    parts = path.strip('/').split('/')
    if len(parts) < 4 or parts[:2] != ['v1', 'schools']:
        raise Problem('Route not found.', 404)
    sid, action = identifier(parts[2]), '/'.join(parts[3:])
    pk = 'SCHOOL#' + sid
    who = member(store, sid, subject)
    config = store.get(pk, 'CONFIG')
    if who['role']=='kid' and (method!='GET' or action!='workspace'):
        raise Problem('The Air Explorer view is read-only.',403)
    now = time.time()
    def require(*roles):
        if who['role'] not in roles:
            raise Problem('This action is not available to your role.', 403)
    def save(sk, value, previous=None, expires=None):
        changes=[change(pk, sk, value, previous, expires)]
        if who['role']=='admin':
            changes.append(change(pk,f'AUDIT#{int(now*1000):013d}#{secrets.token_hex(4)}',
                                  {'role':'admin','action':'Saved '+sk.split('#')[0].lower(),'time':now},expires=now+90*86400))
        store.commit(changes)
    if method=='POST' and action=='schedule-decision':
        require('admin')
        reason=text(data.get('reason'),'Decision reason',300,10)
        if data.get('decision')!='keep-outdoors':raise Problem('Unsupported schedule decision.')
        save('DECISION#'+secrets.token_hex(8),{'decision':'keep-outdoors','reason':reason,'time':now,'role':'admin'},expires=now+90*86400)
        return {'recorded':True,'note':'Decision recorded. Review and publish the school instruction.'}
    if method == 'GET':
        if action == 'health':
            current=store.get(pk,'CURRENT') or {}
            return {'health':health(current.get('air') or {}),'lastSuccessfulRetrieval':current.get('lastSuccessfulAt')}
        if action == 'workspace':
            return workspace(store, sid, who)
        if action == 'history':
            days = 30 if query.get('days') == '30' else 1 if query.get('days')=='1' else 7
            return history(readings, sid, days)
        if action == 'operations':
            require('admin')
            from statistics import median
            plans=[]
            review_delays=[]
            for row in store.query(pk,'PUBLICATION#',limit=100):
                event=row['event']; completed=store.query(pk,'RECEIPT#'+event['id']+'#',limit=1000)
                plans.append(dict(event,receiptSummary=receipt_summary(event,completed,[])))
                if event['time']>=now-7*86400:
                    unique={r['sub']:min(c['createdAt'] for c in completed if c['sub']==r['sub']) for r in completed}
                    review_delays.extend(max(0,t-event['time']) for t in unique.values())
            plans.sort(key=lambda e:e['time'],reverse=True)
            members=store.query(pk,'MEMBER#',limit=500)
            delivery=[dict(d,audienceRole=m['role']) for m in members for d in store.query('USER#'+m['sub'],'DELIVERY#'+sid+'#',limit=50)]
            week=[p for p in plans if p['time']>=now-7*86400]
            by_day={}
            from backend.functions.guardian_rules import FLAGS
            for row in history(readings,sid,7)['readings']:
                value=plan({'pm25':row['pm25'],'aqi':particle_index(row['pm25']),
                            'observedAt':row['observedAt'],'standard':row['standard']},config,now=timestamp(row['observedAt']))['flag']
                day=row['observedAt'][:10]
                if value!='unknown' and (day not in by_day or FLAGS.index(value)>FLAGS.index(by_day[day])): by_day[day]=value
            total=sum(p['receiptSummary']['total'] for p in week)
            confirmed=sum(p['receiptSummary']['confirmed'] for p in week)
            return public({'plans':plans,'weekly':{'daysByFlag':{f:list(by_day.values()).count(f) for f in FLAGS},
                        'plans':len(week),'medianSecondsToReview':median(review_delays) if review_delays else None,
                        'confirmedShare':confirmed/total if total else None},'log':store.query(pk,'AUDIT#',reverse=True,limit=100),
                           'deliveries':sorted(delivery,key=lambda d:d['createdAt'],reverse=True),
                           'children':[{'id':c['id'],'alias':c['alias'],'class_id':c['class_id'],'guardians':c['guardians']} for c in store.query(pk,'CHILD#',limit=500)]})
        if action == 'indices':
            require('admin')
            from cloud.providers import separate_indices
            return separate_indices(store, config)
        if action == 'export':
            require('parent')
            children = [c for c in store.query(pk, 'CHILD#') if subject in c['guardians']]
            return public({'school': sid, 'membership': who, 'preferences': store.get(upk, 'PREFERENCES'),
                           'children': [{k: v for k, v in c.items() if k != 'guardians'} for c in children],
                           'activityRecords': store.query(upk, 'EXPOSURE#' + sid + '#'),
                           'checkins': store.query(upk, 'CHECKIN#' + sid + '#')})
        raise Problem('Route not found.', 404)
    if method == 'DELETE' and action == 'membership':
        require('parent', 'teacher', 'staff')
        link = store.get(upk, pk)
        changes = [change(pk, 'MEMBER#' + subject, None, who)]
        erasure = {'school': sid, 'sub': subject, 'createdAt': now}
        changes.append(change('ERASURE', sid + '#' + subject, erasure))
        if link:
            changes.append(change(upk, pk, None, link))
        for child in store.query(pk, 'CHILD#'):
            if subject in child['guardians']:
                updated = dict(child, guardians=[s for s in child['guardians'] if s != subject])
                changes.append(change(pk, child['_sk'], updated, child))
        if len(changes) > 90:
            raise Problem('Contact the school administrator for assisted unlinking.', 409)
        store.commit(changes)
        # A crash after access revocation is recoverable by the scheduled erasure sweep.
        erase_private(store, erasure)
        return {'unlinked': True, 'note': 'School operational receipts follow school retention. Cognito account deletion is a separate administrator procedure.'}
    if method != 'POST':
        raise Problem('Method not supported.', 405)
    if action == 'preferences':
        value = preferences(data)
        if any(c not in enabled_channels() for c in value['channels']):
            raise Problem('A selected channel has not been configured by the operator.')
        old = store.get(upk, 'PREFERENCES')
        changes = [change(upk, 'PREFERENCES', value, old)]
        previous = store.get(upk, 'CONTACT')
        contacts = {'consentedAt': now}
        if 'email' in value['channels']:
            if not contact:
                raise Problem('Verified email is required.', 403)
            contacts['email'] = contact
            if previous and previous.get('email') == contact and previous.get('emailSuppressed'):
                contacts['emailSuppressed'] = True
        if any(c in value['channels'] for c in ('sms', 'whatsapp')):
            if not phone:
                raise Problem('A verified phone number is required.', 403)
            contacts['phone'] = phone
        if len(contacts) > 1:
            changes.append(change(upk, 'CONTACT', contacts, previous))
        elif previous:
            changes.append(change(upk, 'CONTACT', None, previous))
        store.commit(changes)
        return {'saved': True}
    if action == 'push':
        if data.get('subscription') is None:
            for row in store.query(upk, 'PUSH#', limit=20):
                store.commit([change(upk, row['_sk'], None, row)])
            return {'subscribed': False}
        subscription = validate_push(data['subscription'])
        key = 'PUSH#' + digest(subscription['endpoint'])
        previous = store.get(upk, key)
        if not previous and len(store.query(upk, 'PUSH#', limit=10)) >= 5:
            raise Problem('Remove old subscriptions before adding another device.')
        store.commit([change(upk, key, {'subscription': subscription, 'consentedAt': now}, previous)])
        return {'subscribed': True}
    if action == 'school':
        require('admin')
        value = validate_school({**config, **data, 'id': sid})
        if data.get('cpcb_city'):
            value['cpcb_city'] = text(data['cpcb_city'], 'CPCB city')
        save('CONFIG', value, config)
        return {'saved': True}
    if action == 'class':
        require('admin')
        cid = identifier(data.get('id'))
        save('CLASS#' + cid, {'id': cid, 'label': text(data.get('label'), 'Class label', 50)}, store.get(pk, 'CLASS#' + cid))
        return {'saved': True}
    if action == 'room':
        require('admin')
        rid = identifier(data.get('id'))
        value = {'id': rid, 'label': text(data.get('label'), 'Room name'),
                 'building_type': text(data.get('building_type', 'unknown'), 'Building type', 30),
                 'ventilation': text(data.get('ventilation', 'unknown'), 'Ventilation', 200),
                 'filtration': text(data.get('filtration', 'unknown'), 'Filtration', 200), 'assessedAt': now}
        save('ROOM#' + rid, value, store.get(pk, 'ROOM#' + rid))
        return {'saved': True}
    if action == 'child':
        require('admin')
        cid = identifier(data.get('id')); class_id = identifier(data.get('class_id'))
        if not store.get(pk, 'CLASS#' + class_id):
            raise Problem('Create the class first.')
        if data.get('age_group') not in AGE_GROUPS:
            raise Problem('Choose a supported age group.')
        if store.get(pk, 'CHILD#' + cid):
            raise Problem('Child ID already exists.', 409)
        save('CHILD#' + cid, {'id': cid, 'alias': text(data.get('alias'), 'Child alias', 30),
              'class_id': class_id, 'age_group': data['age_group'], 'guardians': [], 'caution': False})
        return {'saved': True}
    if action == 'invite':
        require('admin')
        role = data.get('role')
        if role not in ROLES:
            raise Problem('Choose a valid role.')
        email = text(data.get('email'), 'Email', 254).lower()
        if '@' not in email:
            raise Problem('Enter an email address.')
        cid = data.get('class_id') or None
        if role == 'teacher' and (not cid or not store.get(pk, 'CLASS#' + identifier(cid))):
            raise Problem('Assign an existing class to the teacher.')
        children = data.get('children', [])
        if not isinstance(children, list) or len(children) > 10 or (children and role != 'parent'):
            raise Problem('Only parents can be linked to up to ten children per invitation.')
        for child_id in children:
            if not store.get(pk, 'CHILD#' + identifier(child_id)):
                raise Problem('Choose children in this school.')
        token = secrets.token_urlsafe(32)
        store.commit([change('INVITES', digest(token), {'school': sid, 'issuer': subject, 'emailHash': digest(email),
             'role': role, 'class_id': cid if role == 'teacher' else None, 'children': sorted(set(children)),
             'expiresAt': now + 86400, 'used': False}, expires=now + 86400),
             change(pk,f'AUDIT#{int(now*1000):013d}#{secrets.token_hex(4)}',{'role':'admin','action':'Created private adult invitation','time':now},expires=now+90*86400)])
        return {'token': token, 'expiresInHours': 24, 'note': 'Share this code privately with the invited adult; no message has been sent.'}
    if action == 'revoke':
        require('admin')
        target = identifier(data.get('sub'))
        if target == subject:
            raise Problem('An administrator cannot revoke their own access here.')
        old = store.get(pk, 'MEMBER#' + target)
        if not old:
            raise Problem('Membership not found.', 404)
        save('MEMBER#' + target, dict(old, active=False, revokedAt=now), old)
        return {'revoked': True}
    if action == 'guardian-link':
        require('admin')
        target = identifier(data.get('sub'))
        guardian = member(store, sid, target, ['parent'])
        cid = identifier(data.get('childId'))
        child = store.get(pk, 'CHILD#' + cid)
        if not child:
            raise Problem('Child not found in this school.', 404)
        save('CHILD#' + cid, dict(child, guardians=sorted(set(child['guardians'] + [guardian['sub']]))), child)
        return {'linked': True}
    if action == 'announce':
        require('admin')
        current = store.get(pk, 'CURRENT') or {}
        risk = plan(dict(current.get('air', {}), stabilizedFlag=(current.get('stability') or {}).get('flag')), config)
        if risk['flag'] == 'unknown':
            raise Problem('Verify fresh air conditions before publishing a planning flag.')
        # UI-generated idempotency key makes a retried publication the same operation.
        request_id = identifier(data.get('requestId'))
        existing = store.get(pk, 'PUBLICATION#' + request_id)
        if existing:
            return {'event': existing['event']}
        event = {'id': request_id, 'school': sid, 'time': now, 'flag': risk['flag'], 'kind': 'admin-announcement',
                 'mode': current.get('air', {}).get('mode', 'live'), 'reasons': [text(data.get('note'), 'Notice', 300)], 'expiresAt': now + 86400,
                 'authorRole': 'admin', 'checklist':[{'id':a['id'],'text':a['text'],'role':'staff' if a['id'] in ('pickup','rotate') else 'teacher' if a['id']=='indoor-pe' else 'parent'} for a in risk['actions']],
                 'audience': [{'sub': m['sub'], 'role': m['role'], 'class_id': m.get('class_id')}
                    for m in store.query(pk, 'MEMBER#', limit=500) if m['active'] and m['role']!='kid']}
        notice = store.get(pk, 'NOTICE')
        changes = emit_changes(store, sid, event, now)
        changes.extend([change(pk, 'NOTICE', event, notice),
                        change(pk,f'AUDIT#{int(now*1000):013d}#{request_id}',{'role':who['role'],'action':'Published school plan','time':now},expires=now+90*86400),
                        change(pk, 'PUBLICATION#' + request_id, {'event': event}, expires=now + 90 * 86400)])
        store.commit(changes)
        return {'event': event}
    if action in ('remind','test-notification'):
        from cloud.notifications import deliver
        notice=store.get(pk,'NOTICE')
        if not notice or notice['expiresAt']<=now:
            raise Problem('Publish a current school plan first.',409)
        if action=='remind':
            require('admin')
            summary=receipt_summary(notice,store.query(pk,'RECEIPT#'+notice['id']+'#'),[])
            targets=[p['sub'] for p in summary['people'] if not p['confirmed']]
            if data.get('recipient'):
                target=identifier(data['recipient'])
                if target not in targets:raise Problem('Choose a pending reviewer of this plan.',403)
                targets=[target]
        else:
            targets=[subject]
        if not targets:
            return {'queued':0,'note':'Everyone has confirmed.'}
        # Preflight every pending recipient. Delivery repeats the checks at dispatch.
        for target in targets:
            pref={**DEFAULT_PREFS,**(store.get('USER#'+target,'PREFERENCES') or {})}
            if quiet(pref,config,now): raise Problem('Quiet hours are active for a recipient. Try later.',409)
            for channel in pref['channels']:
                if (store.get('USER#'+target,f'CAP#{sid}#{local_day(config,now)}#{channel}') or {}).get('count',0)>=pref['dailyCap']:
                    raise Problem('A recipient has reached the daily cap. Try tomorrow.',409)
        eid=identifier(data.get('requestId'))
        if store.get(pk,'REMINDER#'+eid): return {'queued':len(targets),'note':'Already queued.'}
        event=dict(notice,id=eid,planId=notice['id'],time=now,kind='plan-reminder',audience=[{'sub':s} for s in targets])
        changes=emit_changes(store,sid,event,now)
        changes.extend([change(pk,'REMINDER#'+eid,{'eventId':eid},expires=now+86400),change(pk,'NOTICE',notice,notice)])
        store.commit(changes)
        return {'queued':len(targets),'note':'Queued. Recipient preferences are checked again before delivery.'}
    if action=='checklist':
        notice=store.get(pk,'NOTICE')
        if not notice or notice['id']!=data.get('eventId') or notice['expiresAt']<=now: raise Problem('Review the latest plan.',409)
        task=next((t for t in notice.get('checklist',[]) if t['id']==data.get('taskId')),None)
        if not task or task['role']!=who['role']: raise Problem('This task is not assigned to your role.',403)
        key=f"TASK#{notice['id']}#{task['id']}#{subject}"
        old=store.get(pk,key)
        if not old:
            store.commit([change(pk,key,{'sub':subject,'role':who['role'],'taskId':task['id'],'createdAt':now},expires=now+90*86400),change(pk,'NOTICE',notice,notice)])
        return {'saved':True}
    if action in ('acknowledge', 'review'):
        require(*(['teacher'] if action == 'acknowledge' else ['parent', 'teacher', 'staff', 'admin']))
        notice = store.get(pk, 'NOTICE')
        if not notice or notice['id'] != data.get('eventId') or notice['expiresAt'] <= now:
            raise Problem('Refresh and review the latest unexpired school notice.', 409)
        if action == 'acknowledge':
            if data.get('checks') != [True, True, True] or any(type(c) is not bool for c in data['checks']):
                raise Problem('Complete all three class checks.')
            minutes = integer(data.get('minutesMoved'), 'Minutes moved indoors', 0, 240)
        else:
            minutes = 0
        target = who.get('class_id') if action == 'acknowledge' else subject
        key = f"RECEIPT#{notice['id']}#{action}#{target}"
        if not store.get(pk, key):
            # Include NOTICE CAS to reject concurrent superseding publication.
            store.commit([change(pk, key, {'sub': subject, 'class_id': who.get('class_id'), 'kind': action,
                'eventId': notice['id'], 'createdAt': now, 'minutesMoved': minutes}, expires=now + 90 * 86400),
                change(pk, 'NOTICE', notice, notice)])
        return {'saved': True}
    if action in ('profile', 'checkin', 'exposure'):
        require('parent')
        cid = identifier(data.get('childId'))
        child = store.get(pk, 'CHILD#' + cid)
        if not child or subject not in child['guardians']:
            raise Problem('This child is not linked to your account.', 403)
        if action == 'profile':
            if data.get('age_group') not in AGE_GROUPS or not isinstance(data.get('caution'), bool):
                raise Problem('Choose an age group and caution setting.')
            save('CHILD#' + cid, dict(child, alias=text(data.get('alias'), 'Alias', 30),
                age_group=data['age_group'], caution=data['caution']), child)
        elif action == 'checkin':
            if not isinstance(data.get('signal'), bool):
                raise Problem('Check-in must be yes or no.')
            key = f'CHECKIN#{sid}#{cid}#{local_day(config)}'
            old = store.get(upk, key)
            store.commit([change(upk, key, {'childId': cid, 'signal': data['signal'], 'createdAt': now}, old, now + 30 * 86400)])
        else:
            minutes = integer(data.get('minutes'), 'Minutes', 1, 720)
            concentration = number(data.get('concentration'), 'PM2.5', 0, 2000)
            if data.get('context') not in ('indoor', 'outdoor', 'commute'):
                raise Problem('Choose indoor, outdoor or commute.')
            key = f'EXPOSURE#{sid}#{cid}#{local_day(config)}'
            old = store.get(upk, key) or None
            rows = (old or {}).get('entries', [])
            request_id = identifier(data.get('requestId'))
            if any(r['id'] == request_id for r in rows):
                return {'saved': True}
            if sum(r['minutes'] for r in rows) + minutes > 1440:
                raise Problem('Recorded time exceeds one day.')
            rows = rows + [{'id': request_id, 'minutes': minutes, 'concentration': concentration, 'context': data['context']}]
            store.commit([change(upk, key, {'childId': cid, 'entries': rows, 'createdAt': now}, old, now + 30 * 86400)])
        return {'saved': True}
    if action == 'activity-plan':
        current = store.get(pk, 'CURRENT') or {}
        return plan(current.get('air', {}), config, activity=data)
    if action == 'device':
        require('admin')
        device_id = identifier(data.get('id'))
        if store.get('DEVICES', device_id):
            raise Problem('Device already registered.', 409)
        location = data.get('location')
        if location not in ('gate', 'indoor'):
            raise Problem('Choose gate or indoor location.')
        store.commit([change('DEVICES', device_id, {'id': device_id, 'school': sid, 'location': location,
                      'room_id': text(data.get('room_id', 'unassigned'), 'Room', 100), 'active': True}),
                      change(pk,'DEVICE#'+device_id,{'id':device_id,'location':location,'status':'not-installed','registeredAt':now})])
        return {'registered': True, 'note': 'Device telemetry still requires an IoT certificate and restricted topic policy.'}
    raise Problem('Route not found.', 404)


from cloud.observability import observed


@observed
def handler(event, context):
    try:
        # Preflight exposes no records and must precede identity/store access.
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {'statusCode': 204, 'headers': {'Cache-Control': 'no-store'}, 'body': ''}
        claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
        subject = claims.get('sub')
        if not subject or claims.get('token_use') != 'access':
            raise Problem('Sign in with your school account.', 401)
        identifier(subject)
        method = event['requestContext']['http']['method']
        path = event.get('rawPath', '')
        raw = event.get('body') or '{}'
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw).decode('utf-8')
        if len(raw.encode('utf-8')) > 16384:
            raise Problem('Request is too large.', 413)
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise Problem('A valid JSON object is required.')
        if not isinstance(data, dict):
            raise Problem('A JSON object is required.')
        contact = phone = None
        if method == 'POST' and (path == '/v1/enroll' or (path.endswith('/preferences') and 'email' in data.get('channels', []))):
            authorization = event.get('headers', {}).get('authorization', '')
            if not authorization.startswith('Bearer '):
                raise Problem('Access token required.', 401)
            contact = verified_contact(authorization[7:])
        if method == 'POST' and path.endswith('/preferences') and any(c in data.get('channels', []) for c in ('sms', 'whatsapp')):
            authorization = event.get('headers', {}).get('authorization', '')
            if not authorization.startswith('Bearer '):
                raise Problem('Access token required.', 401)
            phone = verified_phone(authorization[7:])
        app_store = DynamoStore()
        if app_store.get('ACCOUNT_ERASURE', subject):
            raise Problem('This account has been closed.', 403)
        if path == '/v1/account' or path.startswith('/v1/account/'):
            from cloud.account import account
            authorization = event.get('headers', {}).get('authorization', '')
            token = authorization[7:] if authorization.startswith('Bearer ') else ''
            return response(200, account(app_store, subject, token, method, path, data))
        if method == 'POST' and (path == '/v1/enroll' or path.endswith(('/announce', '/remind', '/test-notification'))):
            from cloud.rate_limit import reserve
            reserve(app_store, subject, 'enroll' if path == '/v1/enroll' else 'notification')
        result = application(app_store, DynamoStore(os.environ['READINGS_TABLE']), method, path, data,
                             event.get('queryStringParameters') or {}, subject, contact, phone)
        return response(200, result)
    except Problem as error:
        return response(error.status, {'message': str(error)})
    except Conflict:
        return response(409, {'message': 'The record changed. Refresh and retry.'})
    except Exception as error:
        print(json.dumps({'event': 'api-error', 'type': type(error).__name__, 'requestId': getattr(context, 'aws_request_id', None)}))
        return response(500, {'message': 'The request could not be completed. Retry shortly.'})


def response(status, data):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json', 'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff'}, 'body': json.dumps(public(data), allow_nan=False)}
