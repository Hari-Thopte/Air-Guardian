import './assets/ui.js';
import {upgradeToday,cleanerWindows} from './assets/planning-upgrade.js';
import {kidView} from './assets/kid-ui.js';
import {number,localizeDom,getLanguage} from './assets/locale.js';
import {roleIdentity,personalizeToday} from './assets/role-ui.js';
import {settings,blockValues,people,sensors} from './assets/setup-ui.js';
import {enrichToday,checklist,operations,classes,notificationExtras} from './assets/operations-ui.js';
import {dayStrip,gauge,receipts,phone,when,actionHeadline} from './assets/day-ui.js';
import {historySeries,noticeState,receiptGroups} from './assets/consistency-ui.js';
import {api,login,logout,completeLogin,configured,preview} from './cloud-auth.js';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => Number.isFinite(value) ? number(value,{minimumFractionDigits:1,maximumFractionDigits:1}) : 'Unavailable';
const uid = () => crypto.randomUUID();
let draftNote='',priorNotice=null,editingPlan=false;
const demoDrafts=new Map();
let memberships=[], selected='', workspace=null, tab=location.hash==='#plan'?'plan':'today', busy=false, publishId=uid();
let messageTimer,offline=false;
function message(value='',error=false){clearTimeout(messageTimer);const node=$('#message');node.textContent=value;node.className=error?'toast error':'toast';node.setAttribute('role',error?'alert':'status');if(value)messageTimer=setTimeout(()=>{node.textContent='';},3000);}
function route(action){return '/v1/schools/'+encodeURIComponent(selected)+'/'+action;}
async function run(fn){if(busy)return;busy=true;const buttons=[...document.querySelectorAll('button')].map(b=>[b,b.disabled]);buttons.forEach(([b])=>b.disabled=true);const trigger=document.activeElement;if(trigger?.tagName==='BUTTON')trigger.setAttribute('aria-busy','true');try{message();await fn();}catch(e){message(e.message,true);}finally{busy=false;trigger?.removeAttribute('aria-busy');buttons.forEach(([b,disabled])=>{if(b.isConnected)b.disabled=disabled;});}}
async function post(action,body){if(offline)throw new Error('Offline · reconnect before changing the school plan.');return api(route(action),{method:'POST',body});}
function demoDraftKey(w){return 'ag-demo-draft-'+w.school.id;}
function markDemoDraft(w){
  const marker={noticeId:w.notice?.id||null,reading:w.air.fetchedAt,flag:w.planning.flag};
  demoDrafts.set(w.school.id,marker);
  try{localStorage.setItem(demoDraftKey(w),JSON.stringify(marker));}catch{}
}
function planView(w){
  let marker=demoDrafts.get(w.school.id)||null;
  if(preview&&!marker){try{marker=JSON.parse(localStorage.getItem(demoDraftKey(w))||'null');}catch{}}
  return noticeState(w,{demoDraft:preview?marker:null});
}
function completionRows(w,rows){
  const labelFor=r=>{
    if(r.class_id)return (w.classes.find(c=>c.id===r.class_id)?.label||'Class')+' teacher';
    const person=w.receiptSummary?.people.find(p=>p.sub===r.sub)||w.members.find(p=>p.sub===r.sub)||(w.membership.sub===r.sub?w.membership:null);
    return ({parent:'Parent / guardian',admin:'School administrator',staff:'School duty team',teacher:'Teacher'})[person?.role]||'School adult';
  };
  return receiptGroups(rows,labelFor,value=>when(value,{schoolEvent:true})).map(r=>`<p>${r.count} ${r.kind==='acknowledge'?'class acknowledgment'+(r.count===1?'':'s'):'review'+(r.count===1?'':'s')} · ${esc(r.label)} · ${esc(r.time)}</p>`).join('')||'<p>No receipts for this plan yet.</p>';
}
const tabLabels={today:'Today',plan:'School plan',history:'Update history',preferences:'Notifications',children:'Child profiles',privacy:'My data',school:'Campus settings',enrollment:'People & classes',devices:'Sensors',classes:'Classes',operations:'Plan history & activity log'};
const navIcon = key => {const paths={today:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',plan:'M7 4h10v17H5V4h2 M9 2h6v4H9z M8 10h6 M8 14h8',history:'M4 8a8 8 0 1 1-1 8 M4 3v5h5 M12 7v5l3 2',preferences:'M6 8a6 6 0 0 1 12 0v7l2 3H4l2-3z M10 21h4',children:'M9 8a3 3 0 1 0 0 .1 M3 21v-3a6 6 0 0 1 12 0v3 M17 5a3 3 0 0 1 0 6 M18 15a4 4 0 0 1 3 4v2',privacy:'M12 2 3 6v7q1 6 9 9 8-3 9-9V6z M8 12l3 3 5-6',school:'M3 21V8l9-5 9 5v13 M8 21v-6h8v6 M8 9h1 M15 9h1',enrollment:'M5 8a3 3 0 1 0 6 0 3 3 0 1 0-6 0 M2 21v-3a6 6 0 0 1 12 0v3 M19 7v8 M15 11h8',devices:'M6 3h12v18H6z M9 7h6 M9 11h6 M11 17h2'};return `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[key]||(key==='classes'?paths.children:key==='operations'?paths.history:paths.today)}"/></svg>`;};
const badge = flag => `<span class="badge ${esc(flag)}">${esc(flag)}</span>`;
const input = (name,label,value='',type='text') => `<label>${esc(label)}<input name="${name}" type="${type}" ${type==='number'?'step="any"':''} value="${esc(value)}" required></label>`;
const options = (values,current) => values.map(v=>`<option value="${esc(v)}" ${v===current?'selected':''}>${esc(v)}</option>`).join('');
const check = (name,label,checked=false) => `<label class="check"><input name="${name}" type="checkbox" ${checked?'checked':''}>${esc(label)}</label>`;

window.addEventListener('ag:language',()=>{if(workspace)render();});
async function session(){
  const result=await api('/v1/session');memberships=result.memberships;
  selected=memberships.some(m=>m.school===selected)?selected:memberships[0]?.school||'';
  $('#welcome').hidden=true;
  $('#account').innerHTML=preview?`<label>View as<select id="preview-role">${options(['admin','teacher','parent','staff','kid'],new URLSearchParams(location.search).get('role')||'admin')}</select></label>`:`${memberships.length>1?`<label>School<select id="school-select">${memberships.map(m=>`<option value="${esc(m.school)}" ${m.school===selected?'selected':''}>${esc(m.school)}</option>`).join('')}</select></label>`:''}<button class="secondary" id="logout">Sign out</button>`;
  window.AGRestyle.setDemo(preview);
  $('#preview-role')?.addEventListener('change',e=>location.assign('/cloud.html?role='+encodeURIComponent(e.target.value)));
  $('#logout')?.addEventListener('click',()=>run(logout));
  $('#school-select')?.addEventListener('change',e=>run(async()=>{selected=e.target.value;workspace=null;draftNote='';editingPlan=false;tab='today';await load();}));
  if(selected)await load();else enrollment();
}
function enrollment(){
  window.AGRestyle.setFlag('unknown');
  $('#content').innerHTML=`<section class="card"><p class="eyebrow">School approval</p><h2>Link your school</h2>${selected?'<button type="button" id="back-workspace" class="secondary">Back to workspace</button>':''}<p>Enter the invitation code shared privately by your administrator. Sign in with the email they invited.</p><form id="enroll">${input('token','Invitation code')}<button>Join school</button></form><p class="muted">First administrator? The deployment operator must bootstrap your verified account.</p></section>`;
  $('#back-workspace')?.addEventListener('click',()=>run(load));
  $('#enroll').onsubmit=e=>{e.preventDefault();void run(async()=>{await api('/v1/enroll',{method:'POST',body:{token:e.target.elements.token.value}});await session();});};
}
async function load({newDemoDraft=false}={}){
  if(!workspace){$('#content').innerHTML='<section class="loading-skeleton" role="status">Loading school information…</section>';localizeDom();}
  try{
    const next=await api(route('workspace'));workspace=next;offline=false;
    if(newDemoDraft){demoDrafts.clear();try{localStorage.removeItem(demoDraftKey(workspace));}catch{}markDemoDraft(workspace);editingPlan=false;draftNote='';priorNotice=null;}
    render();
  }catch(e){
    offline=true;if([401,403].includes(e.status))workspace=null;
    if(workspace)render();
    else{
      window.AGRestyle.setFlag('unknown');
      $('#content').innerHTML='<section class="card"><h2>Current school information is unavailable</h2><p>Use Refresh to retry. Follow the school’s actual instructions.</p><button id="retry-session">Refresh</button></section>';
      $('#retry-session').onclick=()=>run(session);localizeDom();
    }
    throw e;
  }
}
function offlineState(){
  if(!offline)return;
  window.AGRestyle.setFlag('unknown',{demo:preview});
  const note=document.createElement('p');note.className='notice';note.setAttribute('role','alert');
  note.textContent='Offline · last known plan. Current conditions cannot be verified. Reconnect before taking action.';$('#content').prepend(note);
  document.querySelectorAll('#panel form button,#review,[data-task],[data-role-task],[data-role-review],[data-publish-suggested]').forEach(b=>b.disabled=true);
  localizeDom();
}
function render(){
  if(!workspace)return;
  const w=workspace,role=w.membership.role;
  window.AGRestyle.setDataMode(w.air?.mode||'demo');
  document.body.dataset.role=role;
  if(role==='kid'){kidView(offline?{...w,kid:{...w.kid,flag:'unknown',actionCode:'verify'}}:w);window.AGRestyle.setFlag(offline?'unknown':w.kid.flag,{demo:preview});window.AGRestyle.update();offlineState();return;}
  const headingAction=w.membership.role==='staff'?(w.planning.actions.find(a=>a.id==='rotate')||w.planning.actions[0]):w.planning.actions[0];
  if(priorNotice!==w.notice?.id){if(priorNotice!==null)$('#plan-status').textContent=w.notice?'School plan updated. Open School plan to review the instruction.':'No school instruction is published.';priorNotice=w.notice?.id||'';}
  const tabs=['today','plan','history','preferences',...(role==='parent'?['children','privacy']:[]),...(role==='admin'?['school','enrollment','devices','classes','operations']:[]),...(role==='teacher'?['classes']:[])];
  if(!tabs.includes(tab))tab='today';
  const navGroups=[['Daily',['today','plan','children','classes']],['Messages',['preferences']],['Insights',['history']],['Setup',['school','enrollment','devices','privacy','operations']]];
  $('#content').innerHTML=`<div class="row between workspace-heading ${tab==='today'?'today-banner':''}">${tab==='today'?'<div class="sky-backdrop workspace-sky" data-sky aria-hidden="true"></div>':''}<div class="banner-card"><p class="eyebrow">${esc(role)} workspace${preview?(w.air.mode==='demo'?' · Demo clock 07:30 IST':' · Fictional school · Real source'):''}</p><h1>${tab==='today'?esc(actionHeadline(headingAction)):tabLabels[tab]}</h1><p class="workspace-subtitle">${tab==='today'?esc(roleIdentity[role].detail):esc(w.school.name)+' · Keep your school day coordinated.'}</p>${tab==='today'?'<p class="sky-caption" data-sky-caption></p>':''}</div><button class="secondary" id="refresh">Refresh</button></div><div class="school-layout"><nav class="school-nav" aria-label="School sections">${navGroups.map(([group,items])=>{const visible=items.filter(t=>tabs.includes(t));return visible.length?`<p class="nav-group-label">${group}</p>${visible.map(t=>`<button data-tab="${t}" ${t===tab?'aria-current="page"':''}>${navIcon(t)}<span>${tabLabels[t]}</span></button>`).join('')}`:'';}).join('')}${preview?'':'<button id="another-school">Join another school</button>'}<a class="workspace-return" href="/home.html">← Back to home</a></nav><div id="panel"></div></div>`;
  window.AGRestyle.setFlag(w.planning.flag,{demo:w.air.mode==='demo',pm25:w.air.pm25,boundaries:w.dayPlan.particleBoundaries});
  window.AGRestyle.update();
  $('#refresh').onclick=()=>run(async()=>{await load();message('School workspace updated.');});
  if(preview&&role==='admin'&&new URLSearchParams(location.search).get('present')!=='1'){
    window.AGRestyle.setDemoTools(()=>{
      const dialog=document.createElement('dialog');dialog.className='demo-tools';dialog.setAttribute('aria-labelledby','demo-tools-title');
      dialog.innerHTML='<h2 id="demo-tools-title">Demo tools</h2><p>Fictional data only. No external messages are sent.</p><label>Fictional air scenario<select id="demo-scenario"><option value="">Choose scenario</option><option value="green">Green</option><option value="yellow">Yellow</option><option value="orange">Orange</option><option value="red">Red</option><option value="stale">Stale reading</option></select></label><button class="secondary" id="load-demo">Refresh demo fixtures</button><p>Changing air starts a draft with zero reviews. Earlier plan reviews stay in history. Published/review times show 07:30 IST; freshness uses actual elapsed time.</p><button class="secondary" data-close-demo>Close</button>';
      document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.querySelector('#demo-scenario').value=w.planning.flag==='unknown'?'stale':w.planning.flag;dialog.showModal();
      dialog.querySelector('[data-close-demo]').onclick=()=>dialog.close();
      $('#load-demo').onclick=()=>run(async()=>{await api('/v1/demo/load',{method:'POST',body:{}});await load();dialog.close();message('Demo fixtures refreshed.');});
      const live=document.createElement('button');live.className='secondary';live.textContent='Fetch live regional model';dialog.querySelector('#load-demo').after(live);
      live.onclick=()=>run(async()=>{const result=await api('/v1/demo/live',{method:'POST',body:{}});await load({newDemoDraft:true});dialog.close();message(result.note);});
      const reset=document.createElement('button');reset.className='secondary';reset.textContent='Reset demo';live.after(reset);
      reset.onclick=()=>run(async()=>{await api('/v1/demo/reset',{method:'POST',body:{}});demoDrafts.clear();try{sessionStorage.removeItem(demoDraftKey(w));}catch{}draftNote='';editingPlan=false;await load();dialog.close();message('Fictional demo reset. No cloud records were changed.');});
      $('#demo-scenario').onchange=e=>{const scenario=e.target.value;if(scenario)void run(async()=>{await api('/v1/demo/scenario',{method:'POST',body:{scenario}});await load({newDemoDraft:true});dialog.close();message('Example air updated.');});};
    });
  }

  document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>run(async()=>{tab=b.dataset.tab;render();}));
  $('#another-school')?.addEventListener('click',enrollment);
  if(tab==='today')today();if(tab==='plan')schoolPlan();if(tab==='history')historyPanel();if(tab==='preferences')preferencesPanel();if(tab==='children')childrenPanel();if(tab==='school')schoolPanel();if(tab==='enrollment')adminEnrollment();if(tab==='devices')devices();if(tab==='privacy')privacy();
  if(tab==='school')settings(w);
  if(tab==='enrollment')void people(w,()=>api(route('operations'))).catch(e=>message(e.message,true));
  if(tab==='devices')sensors(w);
  if(tab==='classes'){const state=planView(w);classes({...w,notice:state.notice,receipts:state.receipts});$('#panel').insertAdjacentHTML('beforeend',cleanerWindows(w));}
  if(tab==='operations')void operations(w,()=>api(route('operations')),note=>{editingPlan=true;draftNote=note;tab='plan';render();}).catch(e=>message(e.message,true));
  window.AGRestyle.decoratePanel();
  offlineState();
  localizeDom();
}
function today(){
  const w=workspace,p=w.planning,a=w.air,state=planView(w);
  $('#panel').innerHTML=`<section class="card hero current-air"><p class="eyebrow">Current school planning priority</p>${badge(p.flag)}<h2>${p.flag==='unknown'?'Ask staff to verify current conditions.':({admin:'Set today’s school plan.',teacher:'Check the plan for your class.',parent:'Know what your child’s school has planned.',staff:'Your school-day duty instruction.'}[w.membership.role]||'Review today’s school plan.')}</h2><p class="hero-description">${p.flag==='unknown'?'A fresh reading is needed before planning outdoor activities.':'Use the school plan to coordinate today’s activities.'}</p><div class="row"><div><div class="metric">${fmt(a.pm25)}</div><small>PM2.5 · µg/m³</small></div><div><b>${a.mode==='demo'&&!String(a.source||'').startsWith('Demo data')?'Demo data · ':''}${esc(a.source)}</b><br><small>Observation: ${esc(when(a.observedAt))}</small><br><small>Successful retrieval: ${esc(when(w.lastSuccessfulIngestion))}</small></div></div><details><summary>Source details &amp; explanation</summary><p>${esc(a.selectionPolicy||a.note||'School-area estimate, not a school-gate measurement.')}</p><ul>${p.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul><p>Policy ${esc(p.policyVersion)} · Evidence: ${esc(p.evidenceQuality.label||'Unavailable')}</p></details></section><div class="grid"><section class="card"><h2>Your next steps</h2>${p.actions.slice(0,3).map((a,i)=>`<div class="action-item"><span>${i+1}</span><div><p>${esc(a.text)}</p><details><summary>Why this matters</summary><p class="muted">${esc(a.why)}</p></details></div></div>`).join('')}<p class="muted">Open the school plan to read the current notice and confirm your next step.</p><button id="open-plan">${w.membership.role==='admin'?'Create or review school plan':'Open school plan'} <span aria-hidden="true">→</span></button></section><section class="card"><h2>Data sources</h2>${(a.providers||[]).map(p=>`<p><b>${esc(p.name)}</b><br>${esc(p.status)}</p>`).join('')||'<p>Waiting for scheduled ingestion.</p>'}<p class="muted">Indoor conditions are unknown unless a suitable fresh measurement is available. AC does not establish clean indoor air.</p></section></div><section class="card"><details class="forecast-details"><summary>Plan an outdoor activity</summary><h2>Look ahead</h2><p class="muted">Provider forecast, not school-gate prediction. Forecast issue time may be unavailable; retrieval time is shown separately.</p>${!(a.forecast||[]).length?'<p class="notice">No forecast is available. Follow the current school plan and check again later.</p>':''}<div class="scroll"><table><thead><tr><th>Valid time</th><th>PM2.5 µg/m³</th><th>Source</th><th>Retrieved</th></tr></thead><tbody>${(a.forecast||[]).filter((p,i)=>i%3===0).slice(0,16).map(p=>`<tr><td>${esc(when(p.time,{scheduled:true}))}</td><td>${fmt(p.pm25)}</td><td>${esc(p.source)}</td><td>${esc(when(p.retrievedAt))}</td></tr>`).join('')}</tbody></table></div><form id="activity">${input('start','Activity start (local time)','','datetime-local')}${input('minutes','Activity duration in minutes',30,'number')}<button>Review activity window</button></form><div id="activity-result" role="status"></div></details></section>`;
  const hero=$('#panel .hero'), metric=hero.querySelector('.row');
  const mainAction=w.membership.role==='staff'?(p.actions.find(a=>a.id==='rotate')||p.actions[0]):p.actions[0];
  hero.querySelector('h2').textContent=actionHeadline(mainAction);hero.querySelector('h2').dataset.actionCode=mainAction.id;
  metric.classList.add('reading-evidence');
  metric.children[0].innerHTML=gauge(a.pm25,w.dayPlan.particleBoundaries);
  hero.querySelector('.hero-description').textContent=p.flag==='unknown'?'Fresh air data is needed. Publication is paused.':mainAction.id==='indoor-pe'?'Suggested change. Check room conditions before confirming.':'School planning suggestion. Follow the published school instruction.';
  const source=hero.querySelector('details');source.remove();
  const origin=document.createElement('section');origin.className='card';origin.innerHTML='<h2>Where this reading came from</h2>';origin.append(source);$('#panel').append(origin);
  hero.insertAdjacentHTML('afterend',`<section class="card"><h2>${w.membership.role==='teacher'?'School-day blocks for your class':'Your school day'}</h2><p class="muted">Suggestions to review with a school adult.</p>${dayStrip(w.dayPlan.timetable)}</section>${w.membership.role==='admin'?receipts(state.summary,w.classes,{draft:state.stage==='draft'}):''}`);
  if(w.membership.role==='admin'){
    const layout=document.createElement('div');layout.className='decision-layout';hero.before(layout);layout.append(hero);const receiptPanel=$('#receipts-panel');if(receiptPanel)layout.append(receiptPanel);
  }
  enrichToday(w,{preview,state,openPlan:note=>{editingPlan=true;draftNote=note;tab='plan';render();},publishSuggested:()=>{editingPlan=true;draftNote=w.planning.actions[0].text;tab='plan';render();$('#publish').requestSubmit();}});
  const notice=state.notice,previous=state.previousNotice;
  ($('#panel .decision-layout')||$('#panel .hero')).insertAdjacentHTML('afterend',`<section class="plan-strip"><div><p class="eyebrow">${notice?'Published school plan':'Draft school plan'}</p><h2>${notice?'The school instruction is published.':'Review the new draft before sharing.'}</h2><p>${notice?esc(notice.reasons.join(' ')):previous?'Earlier plan reviews belong to the earlier instruction. This draft has no confirmations.':'Air guidance is a suggestion. Your school has not published a plan yet.'}</p>${notice?`<small>Published · ${esc(when(notice.time,{schoolEvent:true}))}</small>`:''}</div><button class="secondary" data-open-plan>${notice?'Read school plan':w.membership.role==='admin'?'Review draft':'Read school plan'} →</button></section>`);
  document.querySelectorAll('#open-plan,[data-open-plan]').forEach(button=>button.onclick=()=>run(async()=>{tab='plan';render();}));
  const weather=a.weather||{};
  if(weather.observedAt)$('#panel').insertAdjacentHTML('beforeend',`<section class="card"><h2>Weather context</h2><p>${esc(weather.source||'Unavailable')} · ${esc(when(weather.observedAt))}</p><p>Temperature ${fmt(weather.temperature)} °C · Humidity ${fmt(weather.humidity)}% · Wind ${fmt(weather.wind)} km/h</p><p class="muted">Weather is supporting context. It does not establish safe exposure or clean indoor air.</p></section>`);
  $('#indices')?.addEventListener('click',()=>run(async()=>{const r=await api(route('indices'));$('#indices-result').innerHTML=`<p>${esc(r.notice)}</p>${r.providers.map(v=>`<h3>${esc(v.name)}</h3><p>${esc(v.status)}</p><pre>${esc(JSON.stringify(v.indices,null,2))}</pre>`).join('')}`;}));
  $('#activity').onsubmit=e=>{e.preventDefault();const f=e.target;void run(async()=>{const r=await post('activity-plan',{start:new Date(f.elements.start.value).toISOString(),minutes:Number(f.elements.minutes.value)});$('#activity-result').innerHTML=`<p>Regional forecast for this window: <b>${fmt(r.activity.forecastPm25)} µg/m³</b></p><p>${esc(r.activity.label)}</p>${r.activity.planning?badge(r.activity.planning.flag):'<p>No usable forecast covers this activity.</p>'}`;});};
  upgradeToday(w,state,{post,refresh:load,notify:message,history:()=>api(route('history')+'?days=1')});
  personalizeToday(w,state,{open:next=>run(async()=>{tab=next;render();}),review:eventId=>run(async()=>{await post('review',{eventId});await load();message('Review saved.');}),complete:(eventId,taskId)=>run(async()=>{await post('checklist',{eventId,taskId});await load();message('Completion recorded.');})});
}
function schoolPlan(){
  const w=workspace,state=planView(w),n=state.notice,role=w.membership.role;
  $('#panel').innerHTML=`<section class="card"><h2>The shared school plan</h2>${n?`${badge(n.flag)}${role==='parent'?'':`<p>${n.reasons.map(esc).join(' ')}</p>`}<p class="muted">Published ${esc(when(n.time,{schoolEvent:true}))} · Expires ${esc(when(n.expiresAt,{schoolEvent:true}))}</p>`:state.previousNotice?`<p>A new draft is awaiting publication. Reviews for the earlier plan are kept in history.</p><details><summary>Earlier published instruction</summary><p>${state.previousNotice.reasons.map(esc).join(' ')}</p><small>Published · ${esc(when(state.previousNotice.time,{schoolEvent:true}))}</small></details>`:'<p>No school notice has been published.</p>'}${n&&role==='parent'?phone(n.reasons.join(' '),n.flag,w.preferences.language):''}${n?'<button id="review">Mark as read</button>':''}${n&&role==='teacher'?`<form id="ack">${check('read','I read the latest notice')}${check('room','I confirmed the room and supervision')}${check('tell','I told the class what changes')}${input('minutes','Outdoor minutes moved indoors',0,'number')}<button>Acknowledge class plan</button></form>`:''}${role==='admin'?`${state.stage==='draft'||editingPlan?'':'<button type="button" class="secondary" id="edit-plan">Draft a revision</button>'}<div id="plan-editor" ${state.stage==='draft'||editingPlan?'':'hidden'}><form id="publish"><label>School instruction<textarea name="note" maxlength="300" required rows="4">${esc(draftNote||w.planning.actions[0].text)}</textarea></label><div class="row"><button>Publish plan</button><button type="button" class="secondary" id="reset-draft">Reset to suggestion</button></div></form><label>Preview language<select id="phone-language">${[['en','English'],['hi','हिन्दी'],['mr','मराठी']].map(([v,label])=>`<option value="${v}" ${v===w.preferences.language?'selected':''}>${label}</option>`).join('')}</select></label><div id="phone-preview"></div></div>`:''}${role==='admin'?receipts(state.summary,w.classes,{draft:state.stage==='draft'}):''}<button class="secondary" id="print-notice" ${n?'':'disabled'}>Print notice</button><h3>Explicit completion receipts</h3>${completionRows(w,state.receipts)}<p class="muted">Receipts record review and checklist completion, not health outcomes.</p></section>${role==='teacher'?`<section class="card"><h2>Your class</h2>${w.children.map(c=>`<p>${esc(c.alias)} — ${c.extraCaution?'Parent-selected extra caution':'Usual class guidance'}</p>`).join('')||'<p>No children linked to this class.</p>'}</section>`:''}`;
  $('#edit-plan')?.addEventListener('click',()=>{editingPlan=true;draftNote=n.reasons.join(' ');render();$('#publish textarea').focus();});
  const ownReceipt=w.receipts.some(r=>r.sub===w.membership.sub);
  if(n&&n.expiresAt<=Date.now()/1000){$('#review')?.setAttribute('disabled','');$('#ack')?.querySelector('button')?.setAttribute('disabled','');}
  if(ownReceipt&&$('#review')){$('#review').disabled=true;$('#review').textContent='Review recorded';}
  if(w.receipts.some(r=>r.sub===w.membership.sub&&r.kind==='acknowledge')&&$('#ack')){$('#ack').innerHTML='<p>Your class acknowledgment is recorded for this plan.</p>';}
  $('#review')?.addEventListener('click',()=>run(async()=>{await post('review',{eventId:n.id});await load();message('Review saved.');}));
  $('#ack')?.addEventListener('submit',e=>{e.preventDefault();const f=e.target;void run(async()=>{await post('acknowledge',{eventId:n.id,checks:[f.elements.read.checked,f.elements.room.checked,f.elements.tell.checked],minutesMoved:Number(f.elements.minutes.value)});await load();message('Class acknowledgment saved.');});});
  if($('#publish')){
    if(w.planning.flag==='unknown'){const button=$('#publish button');button.disabled=true;button.title='A fresh usable reading is required before publication.';}
    const field=$('#publish textarea');
    const show=()=>{$('#phone-preview').innerHTML=phone(field.value,w.planning.flag,$('#phone-language').value);};
    field.oninput=()=>{draftNote=field.value;show();};$('#phone-language').onchange=show;show();
    $('#reset-draft').onclick=()=>{draftNote='';field.value=w.planning.actions[0].text;show();};
    $('#publish').onsubmit=e=>{
      e.preventDefault();const note=field.value;
      const dialog=document.createElement('dialog');dialog.innerHTML=`<h2>Publish this school plan?</h2><p>${esc(note)}</p><p>This will notify ${w.receiptSummary.total} adults. Quiet hours and the daily limit still apply.</p><p>${preview?'Demo data. No external messages will be sent.':'The delivery worker applies each recipient’s saved preferences.'}</p><div class="row"><button id="confirm-publish">Publish plan</button><button class="secondary" id="cancel-publish">Keep editing</button></div>`;
      document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();
      dialog.querySelector('#cancel-publish').onclick=()=>dialog.close();
      dialog.querySelector('#confirm-publish').onclick=()=>{dialog.close();void run(async()=>{await post('announce',{note,requestId:publishId});publishId=uid();draftNote='';editingPlan=false;await load();message('Published.');$('#receipts-panel')?.scrollIntoView({block:'center',behavior:'smooth'});});};
    };
  }
  checklist({...w,checklist:n?w.checklist:[],completions:n?w.completions:[]},taskId=>run(async()=>{await post('checklist',{eventId:n.id,taskId});await load();message('Completion recorded.');}));
  $('#print-notice').onclick=()=>{if(!n)return;const print=document.createElement('section');print.id='print-sheet';print.innerHTML=`<h1>${esc(w.school.name)}</h1><p>${esc(when(n.time,{schoolEvent:true}))}</p>${badge(n.flag)}<h2>${n.reasons.map(esc).join(' ')}</h2><p>School instruction as published. ${n.mode==='demo'?'Demo data.':''}</p><p>Review this instruction with a school adult.</p><p>${({en:'',hi:'स्कूल के जिम्मेदार वयस्क के साथ इस निर्देश को पढ़ें।',mr:'शाळेतील जबाबदार प्रौढ व्यक्तीसोबत ही सूचना वाचा.'})[$('#phone-language')?.value||w.preferences.language]}</p><small>The school instruction above retains its original wording; this footer is translated.</small>`;document.body.append(print);window.print();print.remove();};
}
function chart(rows){
  if(!rows.length)return '<p>No observations collected yet. History builds as scheduled ingestion runs.</p>';
  const series=historySeries(rows);
  return series.map(({source,points})=>{
    if(points.length<2)return `<section class="history-series"><h3>${esc(source)}</h3><p class="sample-count">${points.length} observation${points.length===1?'':'s'} from this source. At least two are needed for a trend; see the available numbers below.</p></section>`;
    const times=points.map(p=>Date.parse(p.observedAt)),start=Math.min(...times),end=Math.max(...times),max=Math.max(workspace.dayPlan.particleBoundaries[2]*1.5,...points.map(p=>p.pm25));
    const xy=p=>[45+(Date.parse(p.observedAt)-start)/Math.max(1,end-start)*700,190-p.pm25/max*150];
    const limits=[0,...workspace.dayPlan.particleBoundaries,max],flags=['green','yellow','orange','red'];
    const bands=flags.map((flag,i)=>`<rect class="history-band ${flag}" x="45" y="${190-limits[i+1]/max*150}" width="710" height="${(limits[i+1]-limits[i])/max*150}"/>`).join('');
    let paths=[],segment=[];points.forEach((p,i)=>{if(i&&times[i]-times[i-1]>5400000){paths.push(segment);segment=[];}segment.push(xy(p).join(','));});paths.push(segment);
    return `<section class="history-series"><h3>${esc(source)}</h3><p class="sample-count">${points.length} observations plotted from this source · PM2.5 µg/m³</p><svg class="chart" viewBox="0 0 800 230" role="img" aria-label="${points.length} observed PM2.5 points for ${esc(source)}; gaps break the line">${bands}<line x1="45" y1="190" x2="755" y2="190"/><text x="4" y="40">${max.toFixed(0)}</text><text x="15" y="190">0</text>${paths.filter(s=>s.length>1).map(s=>`<polyline points="${s.join(' ')}"/>`).join('')}${points.map(p=>{const[x,y]=xy(p);return `<circle cx="${x}" cy="${y}" r="2"><title>${esc(when(p.observedAt))}: ${fmt(p.pm25)} µg/m³</title></circle>`;}).join('')}<text x="45" y="218">${esc(new Date(start).toLocaleDateString())}</text><text x="670" y="218">${esc(new Date(end).toLocaleDateString())}</text></svg></section>`;
  }).join('')+`<p>School particle planning bands: ${['green','yellow','orange','red'].map(badge).join(' ')}. These are not official AQI bands.</p>`;
}
function historyPanel(){
  $('#panel').innerHTML='<section class="card"><div class="row between"><h2>Air-quality history</h2><label>Window<select id="days"><option value="1">24 hours</option><option value="7" selected>7 days</option><option value="30">30 days</option></select></label></div><p class="muted">PM2.5 concentrations. Sources remain separate; missing periods are unknown.</p><div id="history-result">Loading observations…</div></section>';
  const get=async()=>{const result=await api(route('history')+'?days='+$('#days').value);if(tab!=='history')return;$('#history-result').innerHTML=chart(result.readings)+`<details><summary>Show the numbers</summary><div class="scroll"><table><thead><tr><th>UTC day</th><th>Source</th><th>Sample mean µg/m³</th><th>Observed hours</th><th>Samples</th></tr></thead><tbody>${result.daily.map(d=>`<tr><td>${esc(d.day)}</td><td>${esc(d.source)}</td><td>${fmt(d.sampleMeanPm25)}</td><td>${d.hoursObserved}/24</td><td>${d.samples}</td></tr>`).join('')}</tbody></table></div><p class="muted">Sample means are not official daily AQI. A source change can look like an environmental change.</p></details>`;};
  $('#days').onchange=()=>run(get);void get().catch(e=>message(e.message,true));
}
function preferencesPanel(){
  const w=workspace,p=w.preferences,channels=preview?['in-app']:(w.enabledChannels||['in-app','push','email']);
  $('#panel').innerHTML=`<section class="card"><h2>Your notifications</h2><form id="prefs"><label>Message language<select name="language">${[['en','English'],['hi','Hindi'],['mr','Marathi']].map(([v,label])=>`<option value="${v}" ${v===p.language?'selected':''}>${label}</option>`).join('')}</select></label>${input('quietStart','Quiet hours start',p.quietStart,'time')}${input('quietEnd','Quiet hours end',p.quietEnd,'time')}${input('dailyCap','Daily cap per channel',p.dailyCap,'number')}<fieldset><legend>Channels you consent to receive</legend>${channels.map(c=>check(c,c,p.channels.includes(c))).join('')}</fieldset>${check('morning','Morning school-plan update',p.morning)}<button>Save preferences</button></form><div class="row">${w.pushPublicKey?'<button id="push">Enable browser notifications</button>':''}${preview?'':'<button id="remove-push" class="secondary">Remove browser subscriptions</button>'}</div><p class="muted">${preview?'Demo preferences are saved for this running preview. External notifications are off.':(w.pushPublicKey?'Enable browser notifications on this device to receive Push.':'Browser notifications are not configured.')+' Email and phone delivery require verified contact details and configured services.'} Quiet hours use ${esc(w.school.timezone)}.</p></section><section class="card"><h2>Delivery history</h2>${w.deliveries.map(d=>`<p><b>${esc(d.channel)}</b> · ${esc(d.status)} · ${esc(when(d.createdAt))}</p>`).join('')||'<p>No delivery attempts recorded.</p>'}<p class="muted">Provider acceptance does not establish that the device displayed a message or that a person read it.</p></section>`;
  const languageSelect=$('#prefs').elements.language;
  if(!preview){
    $('#panel').insertAdjacentHTML('beforeend',`<section class="card"><h2>Verify your phone</h2><p id="phone-status" role="status">Loading account status…</p><form id="phone-enroll"><label>Phone number with country code<input name="phone" type="tel" autocomplete="tel" placeholder="+919876543210" required pattern="\\+[1-9][0-9]{7,14}"></label><button>Send verification code</button></form><form id="phone-verify"><label>SMS verification code<input name="code" inputmode="numeric" autocomplete="one-time-code" required pattern="[0-9]{6}" maxlength="6"></label><button>Verify phone</button><button type="button" id="phone-resend" class="secondary">Resend code</button></form><p class="muted">Verification requires the school's configured SMS service. After verification, select an available phone channel and save your consent above.</p></section>`);
    const status=async()=>{const a=await api('/v1/account');if($('#phone-status'))$('#phone-status').textContent=`${a.phone||'No phone saved'} · ${a.phoneVerified?'Verified':'Unverified'} · Authenticator MFA ${a.mfaEnabled?'enabled':'not enrolled'}`;};
    void status().catch(e=>{if($('#phone-status'))$('#phone-status').textContent=e.message;});
    $('#phone-enroll').onsubmit=e=>{e.preventDefault();void run(async()=>{const a=await api('/v1/account/phone',{method:'POST',body:{phone:e.target.elements.phone.value.trim()}});message('Verification code sent '+a.destination);await status();});};
    $('#phone-verify').onsubmit=e=>{e.preventDefault();void run(async()=>{await api('/v1/account/phone/verify',{method:'POST',body:{code:e.target.elements.code.value.trim()}});await status();message('Phone verified. Save notification preferences to enable delivery.');});};
    $('#phone-resend').onclick=()=>run(async()=>{await api('/v1/account/phone/resend',{method:'POST',body:{}});message('Verification code sent.');});
  }
  const choices=document.createElement('div');choices.className='language-choices';choices.setAttribute('aria-label','Message language');
  [['en','English'],['hi','हिन्दी'],['mr','मराठी']].forEach(([value,label])=>{const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=label;b.setAttribute('aria-pressed',String(value===languageSelect.value));b.onclick=()=>{languageSelect.value=value;languageSelect.dispatchEvent(new Event('change'));[...choices.children].forEach(c=>c.setAttribute('aria-pressed',String(c===b)));};choices.append(b);});languageSelect.closest('label').after(choices);
  const state=planView(w);
  notificationExtras({...w,notice:state.notice,reminderState:state.notice?w.reminderState:{allowed:false,reason:'Publish this draft before requesting reviews.'}},{preview,fetchOperations:()=>api(route('operations')),post:(action,body)=>post(action,body),refresh:load,notify:message});
  $('#prefs').onsubmit=e=>{e.preventDefault();const f=e.target;void run(async()=>{await post('preferences',{language:f.elements.language.value,quietStart:f.elements.quietStart.value,quietEnd:f.elements.quietEnd.value,dailyCap:Number(f.elements.dailyCap.value),morning:f.elements.morning.checked,channels:channels.filter(c=>f.elements[c].checked)});await load();message('Preferences saved.');});};
  if($('#push'))$('#push').onclick=()=>run(async()=>{if(!w.pushPublicKey)throw new Error('Push is not configured.');if(!('PushManager'in window)||!('Notification'in window))throw new Error('This browser does not support Web Push.');if(await Notification.requestPermission()!=='granted')throw new Error('Notification permission was not granted.');const reg=await navigator.serviceWorker.register('/cloud-sw.js');await navigator.serviceWorker.ready;const bytes=Uint8Array.from(atob(w.pushPublicKey.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-w.pushPublicKey.length%4)%4)),c=>c.charCodeAt(0));const sub=await reg.pushManager.getSubscription()||await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes});await post('push',{subscription:sub.toJSON()});message('Browser subscribed. Select Push in preferences to receive alerts.');});
  if($('#remove-push'))$('#remove-push').onclick=()=>run(async()=>{await post('push',{subscription:null});message('All browser subscriptions removed from this account.');});
}
function childrenPanel(){
  const children=workspace.children;
  $('#panel').innerHTML=children.length?children.map(c=>`<section class="card"><div class="row between"><h2>${esc(c.alias)}</h2>${badge(c.planning.flag)}</div><form data-profile="${esc(c.id)}">${input('alias','Child alias',c.alias)}<label>Age group<select name="age_group">${options(['5-8','9-12','13-17'],c.age_group)}</select></label>${check('caution','Higher-caution planning preference',c.caution)}<button>Save child preferences</button></form><details><summary>Private check-in and exposure record</summary><form data-checkin="${esc(c.id)}">${check('signal','Use extra caution today (private check-in)')}<button>Save check-in</button></form><form data-exposure="${esc(c.id)}"><label>Setting<select name="context">${options(['outdoor','indoor','commute'])}</select></label>${input('minutes','Minutes',20,'number')}${input('concentration','Measured or explicitly estimated PM2.5 µg/m³','','number')}<button>Record exposure proxy</button></form><p class="muted">Concentration × minutes is a planning proxy, not inhaled dose or a safe limit. Check-ins and activity records expire after 30 days and remain parent-only.</p></details></section>`).join(''):'<section class="card"><h2>No children linked</h2><p>Ask your administrator to provide an invitation linked to your child aliases.</p></section>';
  document.querySelectorAll('[data-profile]').forEach(f=>f.onsubmit=e=>{e.preventDefault();void run(async()=>{await post('profile',{childId:f.dataset.profile,alias:f.elements.alias.value,age_group:f.elements.age_group.value,caution:f.elements.caution.checked});await load();message('Child preferences saved.');});});
  document.querySelectorAll('[data-checkin]').forEach(f=>f.onsubmit=e=>{e.preventDefault();void run(async()=>{await post('checkin',{childId:f.dataset.checkin,signal:f.elements.signal.checked});message('Private check-in saved.');});});
  document.querySelectorAll('[data-exposure]').forEach(f=>{const requestId=uid();f.onsubmit=e=>{e.preventDefault();void run(async()=>{await post('exposure',{childId:f.dataset.exposure,context:f.elements.context.value,minutes:Number(f.elements.minutes.value),concentration:Number(f.elements.concentration.value),requestId});await load();message('Exposure proxy saved.');});};});
}
function schoolPanel(){
  const s=workspace.school;
  $('#panel').innerHTML=`<div class="grid"><section class="card"><h2>School context</h2><form id="school-form">${input('name','School name',s.name)}${input('lat','Latitude',s.lat,'number')}${input('lon','Longitude',s.lon,'number')}${input('timezone','IANA timezone',s.timezone)}<label>Building type<select name="building_type">${options(['unknown','ac','non-ac','mixed'],s.building_type)}</select></label>${input('ventilation','Ventilation (unknown if unassessed)',s.ventilation)}${input('filtration','Filtration (unknown if unassessed)',s.filtration)}${input('cpcb_city','CPCB exact city (unconfigured if unused)',s.cpcb_city||'unconfigured')}${input('outdoor_area_score','Outdoor area assessment (0 unassessed; 1–5 local rating)',s.outdoor_area_score||0,'number')}${input('outdoor_area_notes','Outdoor area assessment notes',s.outdoor_area_notes||'Not assessed')}${input('school_start','School start',s.school_start,'time')}${input('school_end','School end',s.school_end,'time')}<button>Save school context</button></form></section><section class="card"><h2>Classes and rooms</h2><form id="class-form">${input('id','Class ID')}${input('label','Class label')}<button>Save class</button></form><form id="room-form">${input('id','Room ID')}${input('label','Room label')}${input('ventilation','Room ventilation','unknown')}${input('filtration','Room filtration','unknown')}<button>Save room</button></form><p>${workspace.classes.map(c=>esc(c.label)).join(' · ')||'No classes yet'}</p><p>${workspace.rooms.map(r=>esc(r.label)).join(' · ')||'No rooms yet'}</p></section></div>`;
  $('#school-form').querySelectorAll('[type=number]').forEach(i=>i.step='any');
  $('#school-form').onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));data.lat=Number(data.lat);data.lon=Number(data.lon);data.outdoor_area_score=Number(data.outdoor_area_score);data.timetable=blockValues();void run(async()=>{await post('school',data);await load();message('School context saved. New coordinates take effect on the next scheduled ingestion.');});};
  for(const name of ['class','room'])$('#'+name+'-form').onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));void run(async()=>{await post(name,data);await load();message(name+' saved.');});};
}
function adminEnrollment(){
  $('#panel').innerHTML=`<div class="grid"><section class="card"><h2>Create a child alias</h2><p class="muted">Use an alias. No date of birth or diagnosis is needed.</p><form id="child-form">${input('id','Child ID')}${input('alias','Alias')}<label>Class<select name="class_id">${workspace.classes.map(c=>`<option value="${esc(c.id)}">${esc(c.label)}</option>`).join('')}</select></label><label>Age band<select name="age_group">${options(['5-8','9-12','13-17'])}</select></label><button>Create alias</button></form></section><section class="card"><h2>Invite an adult</h2><form id="invite-form">${input('email','Verified email to invite','','email')}<label>Role<select name="role">${options(['parent','teacher','staff','admin'])}</select></label><label>Teacher class ID (teachers only)<input name="class_id"></label><label>Child IDs, comma-separated (parents only)<input name="children"></label><button>Create private invitation code</button></form><div id="invite-result"></div></section></div><section class="card"><h2>School memberships</h2>${workspace.members.map(m=>`<p>${esc(m.sub)} · ${esc(m.role)} · ${m.active?'Active':'Revoked'} ${m.sub!==workspace.membership.sub&&m.active?`<button class="secondary" data-revoke="${esc(m.sub)}">Revoke access</button>`:''}</p>`).join('')}</section>`;
  $('#child-form').onsubmit=e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));void run(async()=>{await post('child',body);await load();message('Child alias created. Link it using a parent invitation.');});};
  $('#invite-form').onsubmit=e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));body.children=body.children.split(',').map(v=>v.trim()).filter(Boolean);void run(async()=>{const result=await post('invite',body);$('#invite-result').innerHTML=`<p>Expires in ${result.expiresInHours} hours. Share privately with the invited adult.</p><pre>${esc(result.token)}</pre><p class="muted">No email or message has been sent.</p>`;});};
  $('#panel').insertAdjacentHTML('beforeend',`<section class="card"><h2>Link an existing parent</h2><form id="guardian-link">${input('sub','Parent account ID from memberships')}${input('childId','Child ID')}<button>Link parent to child</button></form></section>`);
  $('#guardian-link').onsubmit=e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));void run(async()=>{await post('guardian-link',body);message('Parent linked to child.');});};
  document.querySelectorAll('[data-revoke]').forEach(b=>b.onclick=()=>{if(confirm('Revoke this account’s access to this school?'))void run(async()=>{await post('revoke',{sub:b.dataset.revoke});await load();});});
}
function devices(){
  $('#panel').innerHTML=`<section class="card"><h2>Experimental school sensors</h2><p>Register a device identity, then install and assess it before using its readings.</p><form id="device-form">${input('id','Device ID')}<label>Location<select name="location">${options(['gate','indoor'])}</select></label>${input('room_id','Room ID or gate label','gate')}<button>Register device identity</button></form><div class="scroll"><table><thead><tr><th>Device</th><th>PM2.5</th><th>Device status</th><th>Observed</th><th>Reasons</th></tr></thead><tbody>${workspace.sensors.map(s=>`<tr><td>${esc(s.deviceId)}</td><td>${fmt(s.pm25)}</td><td>${esc(s.quality)} · ${s.online?'online':'offline'}</td><td>${esc(when(s.observedAt))}</td><td>${esc(s.qualityReasons.join('; '))}</td></tr>`).join('')}</tbody></table></div><p class="muted">These sensors do not automatically replace the regional school planning input. Calibration and placement review are still required.</p></section>`;
  $('#device-form').onsubmit=e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));void run(async()=>{const r=await post('device',body);await load();message(r.note);});};
}
function privacy(){
  $('#panel').innerHTML=`<section class="card"><h2>Your information</h2><p>Your school uses child aliases, age bands and your optional caution preference for planning. Teachers see class aliases and your caution preference; they do not see your private check-ins or exposure entries.</p><p>Private check-ins and activity records expire after 30 days. Delivery records expire after 30 days. School notices and completion receipts are retained for 90 days. Backups may retain prior copies according to the operator’s recovery policy.</p><div class="row"><button id="export">Download my school data</button><button class="secondary" id="unlink">Leave this school</button></div><p class="muted">Leaving removes your school access and personal activity records. School operational receipts follow the school’s retention policy. For complete Cognito account deletion or child-record erasure, contact the deployment operator.</p></section>`;
  $('#panel .card').insertAdjacentHTML('beforeend',`<details><summary>What is stored for you</summary><p>School membership and notification preferences.</p><p>Linked aliases: ${workspace.children.map(c=>esc(c.alias)).join(' · ')||'None'}</p><p>Language ${esc(workspace.preferences.language)} · Channels ${workspace.preferences.channels.map(esc).join(', ')} · Quiet hours ${esc(workspace.preferences.quietStart)}–${esc(workspace.preferences.quietEnd)}</p></details>`);
  $('#export').onclick=()=>run(async()=>{const data=await api(route('export'));const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='air-guardian-my-data.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('#unlink').onclick=()=>{if(confirm('Leave this school and remove your private activity records?'))void run(async()=>{await api(route('membership'),{method:'DELETE'});await session();message('School membership removed.');});};
  if(preview){$('#unlink').textContent='Request deletion';$('#unlink').onclick=()=>run(async()=>{const result=await api('/v1/demo/deletion-request',{method:'POST',body:{}});message(result.note);});}
}
$('#login').onclick=()=>run(login);
if(!configured()){message('Cloud deployment settings are not configured. The local demo remains at the main project URL.',true);$('#login').disabled=true;}
else void run(async()=>{if(await completeLogin())await session();});

setInterval(()=>{if(workspace&&!busy&&!document.hidden&&tab==='today'&&!document.activeElement?.closest('form'))void run(load);},60000);
