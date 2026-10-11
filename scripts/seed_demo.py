"""Idempotent fictional MemoryStore fixtures. Never seeds an AWS account."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.functions.air_engine import iso, particle_index
from cloud.contracts import DEFAULT_PREFS
from cloud.policy import plan
from cloud.store import change, MemoryStore
from cloud.dayplan import DEFAULT_BLOCKS


def seed(store,readings,config,now=None):
    now=time.time() if now is None else now
    pk='SCHOOL#'+config['id'];created=0
    def put(repository,partition,key,value,expires=None):
        nonlocal created
        if not repository.get(partition,key):
            repository.commit([change(partition,key,value,expires=expires)])
            created+=1
    for i,cid in enumerate(['class-a','class-b','class-c']):
        put(store,pk,'CLASS#'+cid,{'id':cid,'label':['Class 3 A','Class 4 B','Class 5 C'][i],'room_id':'room-'+str(i+1)})
        put(store,pk,'ROOM#room-'+str(i+1),{'id':'room-'+str(i+1),'label':'Room '+str(i+1),'ventilation':'unknown','filtration':'unknown'})
        put(store,pk,'CHILD#alias-'+str(i+1),{'id':'alias-'+str(i+1),'alias':'Explorer '+str(i+1),'age_group':'5-8','class_id':cid,'guardians':['parent'],'caution':i==1})
        if i:
            sub='teacher-'+str(i+1)
            put(store,pk,'MEMBER#'+sub,{'sub':sub,'school':config['id'],'role':'teacher','class_id':cid,'active':True})
    adults=[{'sub':m['sub'],'role':m['role'],'class_id':m.get('class_id')} for m in store.query(pk,'MEMBER#') if m['active'] and m['role']!='kid']
    for person in adults: put(store,'USER#'+person['sub'],'PREFERENCES',DEFAULT_PREFS)
    # Hourly fixture history with deliberate missing hours, not interpolated observations.
    anchor=int(now//3600)*3600
    for hour in range(168):
        if hour%19==0: continue
        observed=anchor-hour*3600-1200;pm=[12,25,45,100,80,35,18][(hour//24)%7]+(hour%5)*2
        day=iso(observed)[:10]
        put(readings,pk+'#'+day,'READING#demo-'+str(hour),{'id':'demo-'+str(hour),'school':config['id'],
            'observedAt':iso(observed),'source':'Demo data · synthetic hourly fixtures','pm25':pm,'pm10':pm*1.8,
            'standard':'India particle estimate','kind':'synthetic','unit':'µg/m³','retrievedAt':iso(now),'mode':'demo'},now+90*86400)
    for i,seconds in enumerate([2*86400,3600]):
        eid='demo-past-'+str(i);published=now-seconds;pm=45 if i==0 else 100
        air={'aqi':particle_index(pm),'pm25':pm,'observedAt':iso(published),'standard':'India particle estimate'}
        planning=plan(air,config,now=published)
        event={'id':eid,'school':config['id'],'time':published,'flag':planning['flag'],'kind':'admin-announcement',
               'mode':'demo','reasons':[planning['actions'][0]['text']],'expiresAt':published+86400,'authorRole':'admin',
               'audience':adults,'checklist':[{'id':a['id'],'text':a['text'],'role':'teacher' if a['id']=='indoor-pe' else 'staff' if a['id']=='pickup' else 'parent'} for a in planning['actions']]}
        put(store,pk,'PUBLICATION#'+eid,{'event':event},now+90*86400)
        put(store,pk,f'EVENT#{int(published*1000):013d}#{eid}',event,now+90*86400)
        put(store,pk,f'AUDIT#{int(published*1000):013d}#{eid}',{'role':'admin','action':'Published demo school plan','time':published},now+90*86400)
        for person in adults[:3]:
            put(store,pk,'RECEIPT#'+eid+'#review#'+person['sub'],{'eventId':eid,'sub':person['sub'],'kind':'review','class_id':person['class_id'],'createdAt':published+180,'minutesMoved':0},now+90*86400)
        if i==1: put(store,pk,'NOTICE',event)
    for i,status in enumerate(['not-installed','review','usable']):
        put(store,pk,'SENSOR#demo-'+str(i),{'deviceId':'demo-'+str(i),'pm25':None if i==0 else 24+i*7,
            'quality':status,'qualityReasons':['Fictional sensor. Calibration and placement review required.'],
            'observedAt':None if i==0 else iso(now-60),'lastSeen':0 if i==0 else now-60,'mode':'demo'})
    # Refresh the explicitly fictional active sample when fixtures are reloaded.
    # Installed real sensors are never touched by this MemoryStore-only preview seed.
    active=store.get(pk,'SENSOR#demo-2')
    if active and active.get('mode')=='demo':
        store.commit([change(pk,'SENSOR#demo-2',dict(active,quality='usable',observedAt=iso(now-60),lastSeen=now-60),active)])
    for person in adults:
        put(store,'USER#'+person['sub'],f'DELIVERY#{config["id"]}#0000000000000000#demo-log#in-app#in-app',
            {'eventId':'demo-past-1','school':config['id'],'channel':'in-app','status':'demo-record-only',
             'language':'en','createdAt':now-1800},now+30*86400)
    return {'created':created,'label':'Demo data. No external messages sent.'}


if __name__=='__main__':
    from cloud.contracts import school
    config=school({'id':'preview','name':'Demo School','lat':28.6139,'lon':77.209})
    store,readings=MemoryStore(),MemoryStore()
    print(json.dumps(seed(store,readings,config)))
    print('The browser preview loads these same fixtures at startup. No persistent cloud data was modified.')
