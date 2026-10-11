import {landingPage,bindLanding} from './landing.js';
import {translateUI,getLanguage} from './i18n.js';
import './pwa.js';
import {workspaceState,workspaceNavigation} from './workspace.js';
import {guardianPage,bindGuardian} from './guardian.js';
import {schools as defaults,readings,series,category,guidance} from './data.js';

import {fetchRegionalAir,csvDownload} from './services.js';

import {shell,dashboard,planPage,mapPage,alertsPage,journalPage,reportsPage,learnPage,fieldHero} from './ui.js';

import {kidsDashboard,kidsPlan,kidsLearn,kidsJournal,adultChecklist,kidMessage} from './kids.js';
import {kidShell,kidHome,kidGame,bindKidExperience,kidText} from './kids_experience.js';
import {sharedPlanPage,bindSharedPlan} from './shared_plan.js';

import {dayPlanner,familyReminders,campusNotes,plannerText,noteTypes} from './campus.js';

const store={get(k,f){try{return JSON.parse(localStorage.getItem(k))??f}catch{return f}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v));return true}catch{return false}}};

const extra=store.get('airguardian.schools',[]);

let schools=[...defaults,...(Array.isArray(extra)?extra.filter(s=>typeof s.id==='string'&&typeof s.name==='string'&&Number.isFinite(s.lat)&&Number.isFinite(s.lon)):[])];

const pref=store.get('airguardian.preferences',{});

let state={page:'overview',role:'parent',school:schools.some(s=>s.id===store.get('airguardian.selected',null))?store.get('airguardian.selected',null):'riverdale',scenario:'moderate',period:'24h',mode:'demo',loading:false,error:null,live:null,theme:store.get('airguardian.theme','light'),plans:store.get('airguardian.plans.v2',{}),entries:store.get('airguardian.journal',[]),preferences:{time:typeof pref.time==='string'?pref.time:'07:00',morning:pref.morning!==false,caution:pref.caution===true}};

if(!Array.isArray(state.entries))state.entries=[];

if(typeof state.plans!=='object'||!state.plans)state.plans={};

state.checks=store.get('airguardian.checklists',{});

if(!state.checks||typeof state.checks!=='object')state.checks={};

state.quizIndex=0;state.quizAnswer=null;

state.familyChecks=store.get('airguardian.family-checks',{});

if(!state.familyChecks||typeof state.familyChecks!=='object'||Array.isArray(state.familyChecks))state.familyChecks={};

state.campusNotes=store.get('airguardian.campus-notes',[]);

if(!Array.isArray(state.campusNotes))state.campusNotes=[];

state.campusNotes=state.campusNotes.filter(n=>n&&typeof n.id==='string'&&typeof n.school==='string'&&typeof n.note==='string'&&noteTypes.includes(n.type)).slice(0,100);

state.sharedStatus='checking';state.sharedError='';state.planPending=false;

state.plannerResult='';state.plannerSelection={activity:'PE lesson',minutes:30};state.plannerResultScope='';

const initialView=new URLSearchParams(location.search).get('view');
const sharedPlanToken=new URLSearchParams(location.search).get('share');

if(['parent','student','staff'].includes(initialView))state.role=initialView;

const initialPage=new URLSearchParams(location.search).get('page');if(initialPage&&['overview','guardian','plan','map','bell','journal','reports','book','play'].includes(initialPage))state.page=initialPage;else if(!initialView)state.page='landing';if(initialPage==='play')state.role='student';
let feedController;

let lastSharedKey='',planRequestId=0;

const localDate=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());

const dateTime=iso=>new Date(iso).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'})+' IST';

const demo=()=>({...readings[state.scenario],standard:'India',mode:'demo',source:'Demonstration fixture',no2:32,o3:24,so2:8,co:.6,observedAt:'2026-10-08T03:00:00Z'});

const getReading=()=>state.mode==='live'?(state.live||{standard:'US',source:'Open-Meteo / CAMS',mode:'live'}):demo();

const planKey=()=>`${state.school}:${state.mode}:${state.mode==='live'?localDate()+':'+category(getReading().aqi,'US').label:state.scenario}`;

function toast(message){const el=document.querySelector('#toast');el.textContent=message;el.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),4500)}

function getHistory(r){if(state.mode==='live')return (r.history||[]).map(p=>({...p,label:new Date(p.time).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'})}));return series[state.period].map((v,i)=>{const time=state.period==='24h'?new Date(Date.parse('2026-10-08T03:00:00Z')-(23-i)*3600000).toISOString():new Date(Date.UTC(2026,state.period==='7d'?9:8,(state.period==='7d'?2:9)+i)).toISOString();return {aqi:Math.round(Math.max(8,Math.min(490,v*r.aqi/156))),time,label:new Date(time).toLocaleString('en-IN',state.period==='24h'?{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'}:{day:'numeric',month:'short',timeZone:'Asia/Kolkata'})}});}

const checklistKey=()=>`${state.school}:${state.mode}:${state.mode==='demo'?state.scenario:localDate()}:${state.role}`;

const familyKey=()=>`${state.school}:${localDate()}`;

const plannerScope=()=>`${state.school}:${state.mode}:${getReading().aqi}:${state.preferences.caution}:${state.role}`;

function context(){const r=getReading(),plan=state.plans[planKey()];return {state,schools,school:schools.find(s=>s.id===state.school),r,cat:category(r.aqi,r.standard),a:guidance(r.aqi,state.preferences.caution,r.standard),planA:guidance(r.aqi,plan?.shared?plan.caution:state.preferences.caution,r.standard),plan,entries:state.entries.filter(e=>e.school===state.school),checks:state.checks[checklistKey()]||[false,false,false],adultChecks:state.checks[checklistKey()]||[false,false,false],familyChecks:state.familyChecks[familyKey()]||[false,false,false],campusNotes:state.campusNotes.filter(n=>n.school===state.school),history:getHistory(r),timeLabel:r.observedAt?dateTime(r.observedAt):'Time unavailable',weatherTime:r.weatherObservedAt?dateTime(r.weatherObservedAt):'Time unavailable'};}

const views={guardian:guardianPage,overview:dashboard,plan:planPage,map:mapPage,bell:alertsPage,journal:journalPage,reports:reportsPage,book:learnPage};

function render(){
 if(sharedPlanToken){document.body.dataset.theme=state.theme;document.body.dataset.page='shared-plan';document.querySelector('#app').innerHTML=sharedPlanPage(sharedPlanToken);bindSharedPlan(sharedPlanToken,render);return}
 if(state.page==='landing'){
  document.body.dataset.theme=state.theme;document.body.dataset.page='landing';document.body.dataset.guardianAuthenticated='false';
  const landingSchool=schools.find(s=>s.id===state.school)||schools[0];let welcome=landingPage(state.theme,landingSchool),saveData=false;try{saveData=localStorage.getItem('airguardian.dataSaver')==='true'}catch{}
  document.body.dataset.dataSaver=String(saveData);
  if(saveData)welcome=welcome.replace(/<img[^>]+src="\/assets\/campus[^\"]+"[^>]*>/g,'<div class="data-saver-placeholder">Illustration hidden · data saver</div>');
  document.querySelector('#app').innerHTML=welcome;
  bindLanding({school:landingSchool,changed:render,enter:target=>{state.role=target==='kids'?'student':'parent';navigate(target==='kids'?'overview':target)},theme:()=>{state.theme=state.theme==='dark'?'light':'dark';store.set('airguardian.theme',state.theme);render()}});
  return;
 }


 if(state.page==='guardian'&&workspaceState.user&&schools.some(s=>s.id===workspaceState.user.school)){state.school=workspaceState.user.school;store.set('airguardian.selected',state.school)}
 if(state.role==='student'&&!['overview','plan','book','journal','play'].includes(state.page))state.page='overview';

 if(state.plannerResultScope!==plannerScope())state.plannerResult='';

 document.body.dataset.theme=state.theme;document.body.dataset.role=state.role;

 const sharedKeyChanged=state.mode==='demo'&&state.sharedStatus==='connected'&&lastSharedKey!==planKey();

 if(sharedKeyChanged)delete state.plans[planKey()];

 const d=context();

 const tools=`<div class="campus-tools" id="school-day-tools">${dayPlanner(d)}${familyReminders(d)}</div>`;

 const kidViews={overview:kidHome,plan:kidsPlan,play:kidGame,book:kidsLearn,journal:kidsJournal};

 const renderer=state.role==='student'?kidViews[state.page]:views[state.page];

 let content=state.page!=='guardian'&&state.mode==='live'&&(state.loading||state.error)?'':renderer(d);

 if(content&&state.role!=='student'){

  if(state.page==='overview')content=fieldHero(d)+content+tools+campusNotes(d)+adultChecklist(d);

  else if(state.page==='plan')content+=tools;

  else if(state.page==='map')content+=campusNotes(d);

 }

 let dataSaver=false;try{dataSaver=localStorage.getItem('airguardian.dataSaver')==='true'}catch{}
 if(dataSaver)content=content.replace(/<img[^>]+src="\/assets\/(?:campus|indoor|kids|school-day)[^"]+"[^>]*>/g,'<div class="data-saver-placeholder">Illustration hidden · data saver</div>');
 document.body.dataset.dataSaver=String(dataSaver);
 document.body.dataset.page=state.page;
 document.body.dataset.guardianAuthenticated=String(state.page==='guardian'&&Boolean(workspaceState.user));
 document.querySelector('#app').innerHTML=state.role==='student'?kidShell(d,content):shell(d,content);

 if(state.page==='guardian'&&workspaceState.user){document.querySelector('.nav').innerHTML=workspaceNavigation();document.querySelector('.nav-label').textContent='SCHOOL WORKSPACE';document.querySelector('.profile b').textContent=workspaceState.user.role+' account';document.querySelector('.profile small').textContent='Signed-in role · fictional demo';}
 if(state.role==='student')bindKidExperience(d,render);

 else if(state.page==='overview'){document.querySelector('h1').textContent='Air quality at your school.';document.querySelector('.subtitle').textContent='Conditions, school activity plans, and updates in one place.';document.querySelector('.eyebrow').textContent='SCHOOL AIR MONITOR';}

 bind();bindExtras();
 if(state.page==='guardian'){bindGuardian(d,render);document.querySelector('.heading-actions').innerHTML='';const footer=document.querySelector('.page-footer>span:last-child');if(footer)footer.textContent='Local school workspace · source labels show data provenance';if(workspaceState.user){const select=document.querySelector('#school-select');select.disabled=true;const option=document.createElement('option');option.textContent=workspaceState.data?.school.name||workspaceState.user.school;select.replaceChildren(option);const location=document.querySelector('.school-picker small');if(location)location.textContent='Signed-in school · role permissions apply';}}
 translateUI(getLanguage());

 if(sharedKeyChanged){

  lastSharedKey=planKey();void syncSharedPlan();

 }

 if(state.mode==='demo'&&state.role!=='student'&&state.page!=='guardian'){

  const strip=document.createElement('div');strip.className='shared-demo-status';strip.setAttribute('role','status');

  strip.textContent=state.sharedError|| (state.sharedStatus==='connected'?(state.role==='student'?'Practice school plans are shared on this computer.':'Shared practice plans · updates on this computer'):state.sharedStatus==='checking'?'Connecting the local school-plan demo…':'Browser-only preview · the shared demo API is unavailable.');

  if(state.role!=='student'&&state.sharedStatus==='connected'){
   const about=document.createElement('details'),summary=document.createElement('summary'),description=document.createElement('p');
   summary.textContent='About this demo';description.textContent='The school-plan API runs with Powertools for AWS Lambda (Python), an AWS open-source project. Plans are saved in SQLite on this computer and checked every five seconds. This is a local demonstration, with preview roles and no cloud deployment or delivered notifications.';
   about.append(summary,description);strip.append(about);
  }
  document.querySelector('.context-strip').after(strip);

 }

}

function listen(){if(!('speechSynthesis'in window)){toast('Read aloud is unavailable in this browser. Ask an adult to read the update with you.');return}if(speechSynthesis.speaking){speechSynthesis.cancel();return}const content=document.querySelector('.kid-glance,.kid-plan-full,.kid-game,.kid-explainer,.kid-game-complete')||document.querySelector('#main');const text=content.innerText;speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang={en:'en-IN',hi:'hi-IN',mr:'mr-IN'}[getLanguage()];utterance.rate=.88;const updateLabel=text=>{const button=document.querySelector('[data-action="listen"]');if(button){button.innerHTML=`${icon('speaker')} ${kidText(text)}`;button.setAttribute('aria-live','polite')}};utterance.onstart=()=>updateLabel('Breezy is speaking…');utterance.onend=()=>updateLabel('Read aloud');utterance.onerror=()=>{updateLabel('Read aloud');toast('The browser could not read this update. Ask an adult to help.')};speechSynthesis.speak(utterance);}

function navigate(page){state.page=page;history.replaceState(null,'',page==='landing'?'/':`/?page=${page}${state.role==='student'?'&view=student':''}`);render();if(page!=='landing'&&state.sharedStatus==='checking')void connectSharedDemo();document.querySelector('#main').focus();window.scrollTo(0,0)}

async function refresh(){feedController?.abort();const c=new AbortController();feedController=c;const school=schools.find(s=>s.id===state.school);state.live=null;state.loading=true;state.error=null;render();const timeout=setTimeout(()=>c.abort(),20000);try{const data=await fetchRegionalAir(school,c.signal);if(feedController!==c||state.mode!=='live')return;state.live=data;}catch(e){if(feedController!==c||state.mode!=='live')return;state.error=e.name==='AbortError'?'The provider request timed out. Retry or use clearly labelled demo scenarios.':e.message;}finally{clearTimeout(timeout);if(feedController===c&&state.mode==='live'){state.loading=false;render()}}}

function openPreferences(){const f=document.querySelector('#preferences-form');f.elements.time.value=state.preferences.time;f.elements.morning.checked=state.preferences.morning;f.elements.caution.checked=state.preferences.caution;document.querySelector('#settings').showModal()}

function openSchool(){const f=document.querySelector('#school-form'),s=schools.find(s=>s.id===state.school);f.elements.name.value=s.demo?'':s.name;f.elements.city.value=s.city;f.elements.lat.value=s.lat;f.elements.lon.value=s.lon;document.querySelector('#school-dialog').showModal()}

function exportReport(){if(state.loading||state.error||!Number.isFinite(getReading().aqi)){toast('No current reading is available to export.');return}const d=context(),r=d.r;csvDownload('air-guardian-report.csv',[['Air Guardian school air report'],['School',d.school.name],['Source',r.source],['Mode',state.mode],['Standard',r.standard],['Air time (UTC)',r.observedAt],['Weather time (UTC)',r.weatherObservedAt||r.observedAt],['Coverage',state.mode==='live'?'Regional model, approximately 45 km grid in India':'Fictional sample station'],[],['Measurement','Value','Unit'],...[['AQI',r.aqi,r.standard+' AQI'],['PM2.5',r.pm25,'µg/m³'],['PM10',r.pm10,'µg/m³'],['NO2',r.no2,'µg/m³'],['O3',r.o3,'µg/m³'],['SO2',r.so2,'µg/m³'],['CO',r.co,'mg/m³'],['Temperature',r.temp,'°C'],['Humidity',r.humidity,'%'],['Pressure',r.pressure,'hPa'],['Wind',r.wind,'km/h']].map(([n,v,u])=>[n,Number.isFinite(v)?v:'',u])]);toast('Report downloaded with source and timestamps.')}

const actions={preferences:openPreferences,school:openSchool,refresh,theme(){state.theme=state.theme==='dark'?'light':'dark';store.set('airguardian.theme',state.theme);render()},confirm:()=>saveSharedPlan('POST'),'reset-plan':()=>saveSharedPlan('DELETE'),log(){const f=document.querySelector('#journal-form');f.reset();f.elements.date.value=localDate();f.elements.date.max=localDate();document.querySelector('#journal-dialog').showModal()},export:exportReport,'export-history'(){const d=context();csvDownload('air-guardian-history.csv',[['School','Source','Mode','Standard','Time','AQI'],...d.history.map(p=>[d.school.name,d.r.source,state.mode,d.r.standard,p.time,p.aqi])]);toast('Displayed history downloaded.')},'export-journal'(){const d=context();csvDownload('air-guardian-activities.csv',[['Date','Activity','Minutes','AQI at entry time','Standard','Mode','Reading time','Note'],...d.entries.map(e=>[e.date,e.activity,e.minutes,e.aqi,e.standard,e.mode,e.observedAt,e.note])]);toast('Activity journal downloaded.')},print(){window.print()}};

function bind(){document.querySelectorAll('button[data-page],a[data-page]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();navigate(b.dataset.page)}));document.querySelectorAll('button[data-role]').forEach(b=>b.addEventListener('click',()=>{state.role=b.dataset.role;navigate(state.role==='student'&&!['overview','plan','book','journal','play'].includes(state.page)?'overview':state.page==='play'?'overview':state.page)}));document.querySelector('#school-select').addEventListener('change',e=>{state.school=e.target.value;store.set('airguardian.selected',state.school);if(state.mode==='live')refresh();else render()});document.querySelector('#scenario')?.addEventListener('change',e=>{state.scenario=e.target.value;render()});document.querySelector('#data-mode').addEventListener('change',e=>{state.mode=e.target.value;state.period='24h';if(state.mode==='live')refresh();else{feedController?.abort();feedController=null;state.loading=false;state.error=null;render()}});document.querySelectorAll('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{state.scenario=b.dataset.scenario;render()}));document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>{state.period=b.dataset.period;render()}));document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>actions[b.dataset.action]?.()));document.querySelectorAll('[data-delete]').forEach(b=>b.addEventListener('click',()=>{state.entries=state.entries.filter(e=>e.id!==b.dataset.delete);const saved=store.set('airguardian.journal',state.entries);render();toast(saved?'Activity deleted from this device.':'Deleted for this session.')}))}

actions.listen=listen;

actions['quiz-next']=()=>{state.quizIndex=(state.quizIndex+1)%3;state.quizAnswer=null;render()};

function bindExtras(){

 if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)document.querySelectorAll('img[src="/assets/logo.svg"]').forEach(img=>img.src='/assets/logo-still.svg');

 document.querySelectorAll('[data-kid-check],[data-adult-check]').forEach(input=>input.addEventListener('change',()=>{const i=Number(input.dataset.kidCheck??input.dataset.adultCheck);const checks=[...(state.checks[checklistKey()]||[false,false,false])];checks[i]=input.checked;state.checks[checklistKey()]=checks;const saved=store.set('airguardian.checklists',state.checks);const progress=document.querySelector('.check-progress');if(progress){progress.setAttribute('role','status');progress.textContent=`${checks.filter(Boolean).length} / 3 · ${saved?kidText('Saved on this device'):kidText('Saved for this session')}`;if(state.role==='student'&&checks.every(Boolean)){const earned=document.createElement('b');earned.className='kid-earned';earned.textContent=kidText('Plan checked!');progress.append(earned);}}if(!saved)toast('Checklist updated for this session.')}));

 document.querySelectorAll('[data-quiz-answer]').forEach(b=>b.addEventListener('click',()=>{if(state.quizAnswer!==null)return;state.quizAnswer=Number(b.dataset.quizAnswer);render()}));

 document.querySelector('[data-planner-form]')?.addEventListener('submit',e=>{

  e.preventDefault();const f=e.target,minutes=Number(f.elements.minutes.value);

  if(!Number.isInteger(minutes)||minutes<1||minutes>180)return;

  state.plannerSelection={activity:f.elements.activity.value,minutes};

  state.plannerResult=plannerText(context(),state.plannerSelection.activity,minutes);state.plannerResultScope=plannerScope();

  render();const result=document.querySelector('.planner-result');result.tabIndex=-1;result.focus({preventScroll:true});result.scrollIntoView({block:'nearest',behavior:'auto'});

 });

 document.querySelectorAll('[data-family-check]').forEach(input=>input.addEventListener('change',()=>{

  const checks=[...(state.familyChecks[familyKey()]||[false,false,false])];checks[Number(input.dataset.familyCheck)]=input.checked;

  state.familyChecks[familyKey()]=checks;const saved=store.set('airguardian.family-checks',state.familyChecks);

  const progress=document.querySelector('[data-family-progress]');progress.setAttribute('role','status');progress.textContent=`${checks.filter(Boolean).length} / 3 · ${saved?kidText('Saved on this device'):kidText('Saved for this session')}`;if(state.role==='student'&&checks.every(Boolean)){const earned=document.createElement('b');earned.className='kid-earned';earned.textContent=kidText('Plan checked!');progress.append(earned);}

 }));

 document.querySelector('[data-campus-form]')?.addEventListener('submit',e=>{

  e.preventDefault();if(state.role==='student')return;const f=e.target,type=f.elements.type.value,note=f.elements.note.value.trim();

  if(!note||note.length>240||!noteTypes.includes(type))return;

  state.campusNotes.unshift({id:crypto.randomUUID(),school:state.school,type,note,role:state.role,time:new Date().toISOString()});state.campusNotes=state.campusNotes.slice(0,100);

  const saved=store.set('airguardian.campus-notes',state.campusNotes);render();toast(saved?'Campus note saved on this device.':'Campus note saved for this session.');

  document.querySelector('#campus-notes-heading').scrollIntoView({block:'start',behavior:'auto'});

 });

 document.querySelectorAll('[data-campus-delete]').forEach(b=>b.addEventListener('click',()=>{

  state.campusNotes=state.campusNotes.filter(n=>n.id!==b.dataset.campusDelete||n.school!==state.school);store.set('airguardian.campus-notes',state.campusNotes);render();toast('Campus note removed from this device.');

 }));

 document.querySelector('[data-action="review-activity"]')?.addEventListener('click',()=>{

  document.querySelector('#planner-heading').scrollIntoView({block:'start',behavior:'auto'});document.querySelector('#planner-activity').focus({preventScroll:true});

 });

}

document.querySelector('#close-settings').addEventListener('click',()=>document.querySelector('#settings').close());document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.close).close()));

document.querySelector('#preferences-form').addEventListener('submit',e=>{e.preventDefault();const f=e.target;state.preferences={time:f.elements.time.value,morning:f.elements.morning.checked,caution:f.elements.caution.checked};const saved=store.set('airguardian.preferences',state.preferences);document.querySelector('#settings').close();render();toast(saved?'Preferences saved on this device.':'Preferences applied for this session.')});

document.querySelector('#school-form').elements.city.addEventListener('change',e=>{e.target.form.elements.lat.value=e.target.value==='Mumbai'?19.076:28.6139;e.target.form.elements.lon.value=e.target.value==='Mumbai'?72.8777:77.209});

document.querySelector('#school-form').addEventListener('submit',e=>{e.preventDefault();const f=e.target,name=f.elements.name.value.trim(),lat=Number(f.elements.lat.value),lon=Number(f.elements.lon.value);if(!name||!Number.isFinite(lat)||Math.abs(lat)>90||!Number.isFinite(lon)||Math.abs(lon)>180)return;const current=schools.find(s=>s.id===state.school);const school={id:current.demo?'campus-'+crypto.randomUUID():current.id,name,city:f.elements.city.value,area:f.elements.city.value,lat,lon,demo:false};if(current.demo)schools.push(school);else schools=schools.map(s=>s.id===school.id?school:s);state.school=school.id;const saved=store.set('airguardian.schools',schools.filter(s=>!s.demo));store.set('airguardian.selected',state.school);document.querySelector('#school-dialog').close();if(state.mode==='live')refresh();else render();toast(saved?'School saved. Verify the campus coordinates.':'School added for this session.')});

document.querySelector('#journal-form').addEventListener('submit',e=>{e.preventDefault();const f=e.target,minutes=Number(f.elements.minutes.value);if(!Number.isInteger(minutes)||minutes<1||minutes>1440||f.elements.date.value>localDate())return;const r=getReading();state.entries.unshift({id:crypto.randomUUID(),school:state.school,date:f.elements.date.value,activity:f.elements.activity.value,minutes,note:f.elements.note.value.trim(),aqi:Number.isFinite(r.aqi)?r.aqi:null,standard:r.standard,mode:state.mode,observedAt:r.observedAt||'Unavailable'});const saved=store.set('airguardian.journal',state.entries);document.querySelector('#journal-dialog').close();state.page='journal';render();toast(saved?'Activity saved on this device.':'Activity saved for this session.')});

render();

window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',render);



async function planApi(path,options={}){

 const response=await fetch(path,{...options,signal:AbortSignal.timeout(5000),headers:{'Content-Type':'application/json',...options.headers}});

 if(!response.ok)throw new Error('The shared demo plan could not be loaded.');

 return response.json();

}

function sharedPath(school=state.school,scenario=state.scenario){return `/api/plans/${encodeURIComponent(school)}?scenario=${encodeURIComponent(scenario)}`}

async function syncSharedPlan(){

 if(state.mode!=='demo'||state.sharedStatus!=='connected'||state.planPending)return;

 const key=planKey(),request=++planRequestId;

 try{

  const data=await planApi(sharedPath());

  if(request!==planRequestId||key!==planKey()||state.mode!=='demo')return;

  const changed=JSON.stringify(state.plans[key]||null)!==JSON.stringify(data.plan);

  if(data.plan)state.plans[key]=data.plan;else delete state.plans[key];

  const hadError=Boolean(state.sharedError);state.sharedError='';

  if(changed||hadError)render();

 }catch{

  if(request!==planRequestId||key!==planKey())return;

  delete state.plans[key];state.sharedError='Shared plan unavailable. Retry by refreshing this page; no confirmation is shown.';render();

 }

}

async function saveSharedPlan(method){

 if(state.role!=='staff'||state.planPending||!Number.isFinite(getReading().aqi))return;

 const key=planKey(),note=document.querySelector('#plan-note')?.value.trim()||'';

 if(state.mode!=='demo'||state.sharedStatus==='unavailable'){

  if(method==='POST')state.plans[key]={time:new Date().toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}),school:state.school,note};else delete state.plans[key];

  store.set('airguardian.plans.v2',state.plans);render();toast(method==='POST'?'Plan confirmed in this browser.':'Plan reopened for review.');return;

 }

 if(state.sharedStatus!=='connected'){toast('The local demo API is still connecting. Please try again.');return}

 const path=sharedPath();state.planPending=true;++planRequestId;

 document.querySelector('[data-action="confirm"]')?.setAttribute('disabled','');

 document.querySelector('[data-action="reset-plan"]')?.setAttribute('disabled','');

 try{

  const data=await planApi(path,{method,headers:{'X-Demo-Role':'staff'},...(method==='POST'?{body:JSON.stringify({note,caution:state.preferences.caution})}:{})});

  if(data.plan)state.plans[key]=data.plan;else delete state.plans[key];

  state.sharedError='';toast(method==='POST'?'Demo plan shared with browsers on this computer.':'Demo plan reopened for review.');

 }catch{state.sharedError='The plan change was not saved. Try again.';toast(state.sharedError)}

 finally{state.planPending=false;render()}

}

async function connectSharedDemo(){

 try{const health=await planApi('/api/health');state.sharedStatus=health.mode==='local-demo'?'connected':'unavailable'}

 catch{state.sharedStatus='unavailable'}

 render();

}

if(state.page!=='landing')void connectSharedDemo();

setInterval(()=>{if(document.visibilityState==='visible')void syncSharedPlan()},5000);

document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')void syncSharedPlan()});



