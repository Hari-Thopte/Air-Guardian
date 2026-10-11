"""Loopback-only cloud workflow preview with fictional fixtures. NEVER deploy this server.

The same application/repository contracts run here with MemoryStore. Cognito and AWS
services are not simulated as verified; a visible banner identifies the preview.
No outbound notifications occur. A real regional provider is contacted only
when the administrator explicitly uses the live-source check in Demo tools.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit, parse_qs
import argparse
import json
import copy
import mimetypes
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for dependencies in [Path(__file__).resolve().parents[1] / '.test-output' / 'deps', Path(__file__).resolve().parents[1] / 'backend' / 'vendor']:
    if dependencies.exists(): sys.path.insert(0, str(dependencies))
from cloud.api import application
from cloud.contracts import school, Problem
from cloud.store import MemoryStore, change, Conflict
from cloud.pipeline import ingest
from backend.functions.air_engine import demo, openmeteo
from scripts.bootstrap_school import bootstrap
from scripts.seed_demo import seed
from cloud.notifications import deliver
from scripts.demo_scenario import select_scenario
from backend.functions.air_engine import estimate, iso

ROOT = Path(__file__).resolve().parents[1]
store, readings, lock = MemoryStore(), MemoryStore(), Lock()
config = school({'id': 'preview', 'name': 'Demo School', 'lat': 28.6139, 'lon': 77.209})
bootstrap(store, config, 'admin')
for role in ['parent', 'teacher', 'staff', 'kid']:
    store.commit([change('SCHOOL#preview', 'MEMBER#' + role, {'sub': role, 'school': 'preview', 'role': role,
         'class_id': 'class-a' if role == 'teacher' else None, 'active': True}),
         change('USER#' + role, 'SCHOOL#preview', {'school': 'preview'})])
store.commit([change('SCHOOL#preview', 'CLASS#class-a', {'id': 'class-a', 'label': 'Class 3 A'}),
    change('SCHOOL#preview', 'CHILD#alias-a', {'id': 'alias-a', 'alias': 'Child A', 'age_group': '5-8',
          'class_id': 'class-a', 'guardians': ['parent'], 'caution': False})])
air = demo(config, True)
air.update(source='Synthetic preview fixtures', retentionApproved=True, providers=[{'name': 'Fictional fixtures', 'status': 'Not live measurements'}],
           forecastSource='Synthetic fixture', fetchedAt=air.get('observedAt'))
ingest(store, readings, config, air)
seed(store, readings, config)
INITIAL_ROWS=copy.deepcopy(store.rows)
INITIAL_READINGS=copy.deepcopy(readings.rows)


def drain_demo_outbox():
    """No real sends: only consented in-app records. No provider calls."""
    for row in store.query('OUTBOX'):
        for person in store.query('SCHOOL#'+row['school'],'MEMBER#'):
            prefs=store.get('USER#'+person['sub'],'PREFERENCES') or {}
            if prefs.get('channels', ['in-app']) != ['in-app']:
                continue
            deliver(store,row['event'],subject=person['sub'])
        store.commit([change('OUTBOX',row['_sk'],None,row)])

AUTH = '''
const role = new URLSearchParams(location.search).get('role') || 'admin';
export const preview=true;
export const configured=()=>true;
export const completeLogin=async()=>true;
export const login=async()=>{};
export const logout=async()=>location.assign('/cloud.html?role=parent');
const banner=document.createElement('section');banner.className='preview-bar';
banner.innerHTML='<span class="preview-dot"></span><b>Demo workspace</b><span>Sample data · No messages sent</span>';
document.querySelector('main').prepend(banner);
import {resilientFetch} from '/assets/resilient-fetch.js';
export async function api(path,{method='GET',body}={}){
 const r=await resilientFetch(path,{method,headers:{'Content-Type':'application/json','X-Preview-Role':role},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json();if(!r.ok){const error=new Error(data.message);error.status=r.status;throw error;}return data;
}
'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def do_DELETE(self):
        self.route()

    def log_message(self, fmt, *args):
        pass

    def reply(self, status, raw, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers(); self.wfile.write(raw if isinstance(raw, bytes) else raw.encode())

    def route(self):
        expected_host = f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') != expected_host:
            self.reply(403, '{}'); return
        path = urlsplit(self.path).path
        if path.startswith('/v1/'):
            if self.command != 'GET' and self.headers.get('Origin') != 'http://' + expected_host:
                self.reply(403, '{}'); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 16384:
                    raise Problem('Invalid body length.')
                body = json.loads(self.rfile.read(length) or '{}')
                role = self.headers.get('X-Preview-Role', '')
                if role not in ('admin', 'teacher', 'parent', 'staff', 'kid'):
                    raise Problem('Choose a fictional preview role.', 401)
                query = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
                if path.endswith('/indices'):
                    self.reply(200, json.dumps({'providers': [], 'notice': 'Provider calls are disabled in this fictional preview.'}))
                    return
                with lock:
                    if path == '/v1/demo/deletion-request':
                        if role!='parent' or self.command!='POST': raise Problem('This demo request belongs to the fictional parent.',403)
                        old=store.get('USER#parent','DELETION_REQUEST#preview')
                        if not old: store.commit([change('USER#parent','DELETION_REQUEST#preview',{'createdAt':time.time(),'mode':'demo'},expires=time.time()+30*86400)])
                        result={'note':'Deletion request recorded in this fictional preview. No account or child records were deleted.'}
                    elif path == '/v1/demo/reset':
                        if role!='admin' or self.command!='POST': raise Problem('Reset requires the fictional administrator.',403)
                        store.rows=copy.deepcopy(INITIAL_ROWS)
                        readings.rows=copy.deepcopy(INITIAL_READINGS)
                        result={'note':'Fictional demo reset. No cloud records were changed.'}
                    elif path == '/v1/demo/live':
                        if role!='admin' or self.command!='POST': raise Problem('Live-source checks require the fictional administrator.',403)
                        config=store.get('SCHOOL#preview','CONFIG')
                        try:
                            result_air=openmeteo(config)
                            air=estimate(config,result_air['stations'])
                            air.update(mode='live',source='Open-Meteo / CAMS',forecast=result_air['forecast'],providers=[{'name':'Open-Meteo / CAMS','status':'Regional model; not a school-gate sensor'}],fetchedAt=iso(time.time()),forecastSource='Open-Meteo / CAMS',retentionApproved=True)
                            ingest(store,readings,config,air)
                            result={'note':'Live regional model retrieved. The school and accounts remain fictional.'}
                        except Exception:
                            previous=store.get('SCHOOL#preview','CURRENT')
                            if previous and previous.get('air',{}).get('mode')=='live':
                                ingest(store,readings,config,{'providers':[{'name':'Open-Meteo / CAMS','status':'Retrieval failed; cached reading'}]})
                            raise Problem('Live source unavailable. Current data was not replaced with invented readings.',503)
                    elif path in ('/v1/demo/load','/v1/demo/scenario'):
                        if role!='admin' or self.command!='POST': raise Problem('Demo tools require the fictional administrator.',403)
                        config=store.get('SCHOOL#preview','CONFIG')
                        if path.endswith('/load'):
                            result=seed(store,readings,config)
                        else:
                            choice=body.get('scenario')
                            if choice not in ('green','yellow','orange','red','stale'): raise Problem('Choose a supported demo scenario.')
                            result=select_scenario(store,readings,config,choice)
                    else:
                        result = application(store, readings, self.command, path, body, query, role, role + '@example.invalid')
                        if self.command=='POST': drain_demo_outbox()
                self.reply(200, json.dumps(result))
            except Problem as error:
                self.reply(error.status, json.dumps({'message': str(error)}))
            except Conflict:
                self.reply(409, json.dumps({'message': 'Record changed. Refresh and retry.'}))
            except Exception:
                self.reply(400, json.dumps({'message': 'Invalid preview request.'}))
            return
        if path == '/local-engine':
            from cloud.local_engine import handler
            from types import SimpleNamespace
            result = handler({'httpMethod':'GET','path':'/engine','headers':{},'queryStringParameters':None,'requestContext':{'stage':'local','requestId':'preview'},'body':None,'isBase64Encoded':False}, SimpleNamespace(function_name='local-engine',memory_limit_in_mb=256,invoked_function_arn='local-only',aws_request_id='preview'))
            self.reply(result['statusCode'], result['body']); return
        if path == '/cloud-auth.js':
            self.reply(200, AUTH, 'text/javascript'); return
        if path == '/':
            path = '/home.html'
        allowed = {'/landing.js', '/landing-scenarios.json', '/assets/landing.css', '/home.html', '/home.css', '/home.js', '/portal-design.css', '/assets/campus-landscape.webp', '/assets/logo.svg', '/brand-refresh.css', '/cloud-theme.js', '/assets/guardian-emblem.png', '/brand-entry.js', '/brand-entry.css', '/cloud.html', '/cloud-app.js', '/cloud.css', '/cloud-sw.js'}
        allowed.update({'/assets/story.js','/assets/pwa-upgrade.js', '/assets/resilient-fetch.js', '/offline.html', '/cloud-manifest.webmanifest', '/assets/upgrade.css', '/assets/upgrade-controls.js', '/assets/ui.css', '/assets/ui.js', '/assets/day-ui.js', '/assets/consistency-ui.js', '/assets/role-ui.js', '/assets/locale.js', '/assets/catalogue.json', '/assets/kid-ui.js', '/assets/planning-upgrade.js', '/assets/safe-html.js', '/assets/operations-ui.js', '/assets/setup-ui.js', '/assets/architecture.svg'})
        allowed.update({'/assets/guardian-emblem-small.webp','/assets/guardian-emblem-2x.webp','/assets/favicon.png',
                        '/assets/fonts/fonts.css','/assets/fonts/figtree-latin.woff2','/assets/fonts/figtree-latin-ext.woff2',
                        '/assets/fonts/noto-sans-devanagari.woff2'})
        if path not in allowed:
            self.reply(404, '{}'); return
        raw = (ROOT / path[1:]).read_bytes()
        if path == '/home.html':
            raw = raw.replace(b'<body ', b'<body data-demo="true" ', 1)
        content_type = {'js': 'text/javascript', 'woff2': 'font/woff2', 'webp': 'image/webp'}.get(
            path.rsplit('.', 1)[-1], mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.reply(200, raw, content_type)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=5185)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Fictional cloud workflow preview: http://127.0.0.1:{args.port}/cloud.html', flush=True)
    server.serve_forever()
