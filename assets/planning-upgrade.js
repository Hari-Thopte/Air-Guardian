import {html} from './safe-html.js';
import {when,escape} from './day-ui.js';
import {translateText,number,localizeDom} from './locale.js';

export function cleanerWindows(w){
  const windows=w.cleanestWindows||[];
  return `<section class="card cleaner-windows"><h2>Cleaner activity windows</h2><p class="muted">Planning estimate</p>${windows.length?windows.map(row=>html`<p><strong>${row.block}</strong> · ${row.original} → ${row.suggested} · ${number(row.originalPm25)} → ${number(row.suggestedPm25)} µg/m³</p><p>${row.label}</p>`).join(''):'<p>No complete forecast window is available.</p>'}<p class="muted">No safer time or activity clearance is implied.</p></section>`;
}
export function upgradeToday(w,state,{post,refresh,notify,history}){
  const panel=document.querySelector('#panel');
  panel.insertAdjacentHTML('beforeend',cleanerWindows(w));
  const boundary=w.dayPlan.particleBoundaries[2],pm=w.air.pm25;
  const forecast=(['Fresh','Getting old'].includes(w.dataHealth.status)?w.air.forecast||[]:[]).filter(p=>Number.isFinite(p.pm25)&&Date.parse(p.time)>Date.now()).sort((a,b)=>Date.parse(a.time)-Date.parse(b.time));
  const crossing=Number.isFinite(pm)&&pm>boundary?forecast.find(p=>p.pm25<=boundary):null;
  const hero=panel.querySelector('.hero');
  hero?.insertAdjacentHTML('beforeend',html`<p class="threshold-context">${Number.isFinite(pm)?`${number(Math.abs(pm-boundary),{maximumFractionDigits:1})} µg/m³ ${pm>boundary?'above':'below'} ${number(boundary)} µg/m³ · red planning boundary`:'Unavailable'}</p>`);
  if(crossing)hero?.insertAdjacentHTML('beforeend',html`<p>${translateText('Forecast below red boundary')}: ${when(crossing.time,{scheduled:true})} · ${number(crossing.pm25)} µg/m³</p>`);
  const status=document.createElement('section');status.className='card system-status';status.innerHTML=html`<h2>System status</h2><p>${w.dataHealth.status} · ${w.air.source}</p>`;panel.append(status);
  if(w.air.cached)status.insertAdjacentHTML('beforeend',html`<p>${translateText('Cached reading · last successful retrieval')}: ${when(w.lastSuccessfulIngestion)}</p>`);
  if(w.air.mode==='live'&&String(w.air.source).includes('CAMS'))status.insertAdjacentHTML('beforeend','<p><a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo</a> · <a href="https://atmosphere.copernicus.eu/" target="_blank" rel="noopener">CAMS</a> · Regional model, not a school-gate sensor.</p>');
  if(w.stability?.candidate&&w.stability.candidate!==w.stability.flag)hero?.insertAdjacentHTML('beforeend',html`<p>${translateText('Hourly recovery check pending')} · ${number(w.stability.meanPm25)} µg/m³ · ${translateText('Supporting hourly mean; not a replacement measurement.')}</p>`);
  if(w.membership.role!=='admin')return;
  const block=(w.dayPlan.timetable||w.outdoorSummary?.blocks||[]).find(b=>b.name==='Assembly');
  if(block){const [hour,minute]=block.start.split(':').map(Number);const deadline=hour*60+minute-15;const parts=new Intl.DateTimeFormat('en-GB',{timeZone:w.school.timezone||'Asia/Kolkata',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());const now=w.air.mode==='demo'?450:Number(parts.find(p=>p.type==='hour').value)*60+Number(parts.find(p=>p.type==='minute').value);const label=String(Math.floor(deadline/60)).padStart(2,'0')+':'+String(deadline%60).padStart(2,'0');hero?.insertAdjacentHTML('beforeend',html`<p>${translateText('Publish by')} ${label} · ${translateText('Assembly')} ${block.start} · ${now<deadline?number(deadline-now)+' '+translateText('minutes remaining'):translateText('Deadline passed — check the current instruction')}</p>`);}
  const notice=state.notice,rows=panel.querySelectorAll('#receipts-panel .review-people>p');
  if(w.deadlineNudge)panel.querySelector('#receipts-panel')?.insertAdjacentHTML('beforeend',html`<p>${translateText('Automatic deadline reminder queued')}: ${number(w.deadlineNudge.count)} · ${when(w.deadlineNudge.time)}</p><small>${translateText('Consent, quiet hours and daily caps still apply.')}</small>`);
  rows.forEach((row,i)=>{
    const person=state.summary?.people[i];if(!person||person.confirmed||!notice)return;
    const small=document.createElement('small');small.textContent='Waiting since '+when(notice.time,{schoolEvent:true});row.append(small);
    const button=document.createElement('button');button.className='secondary';button.textContent='Remind';button.disabled=!w.reminderState.allowed;button.title=w.reminderState.reason;
    button.onclick=async()=>{button.disabled=true;try{const result=await post('remind',{recipient:person.sub,requestId:crypto.randomUUID()});notify(result.note);await refresh();}catch(e){notify(e.message,true);button.disabled=false;}};row.append(button);
  });
  const override=document.createElement('section');override.className='card';
  override.innerHTML='<details><summary>School adult override</summary><p>Recorded decision does not establish safe air.</p><form id="schedule-override"><label>Keep outdoors<input name="reason" aria-label="Required reason" required minlength="10" maxlength="300"></label><button>Record decision</button></form></details>';
  panel.append(override);override.querySelector('form').onsubmit=async e=>{e.preventDefault();try{await post('schedule-decision',{decision:'keep-outdoors',reason:e.target.elements.reason.value});notify('Decision recorded. Review and publish the school instruction.');}catch(error){notify(error.message,true);}};
  const trend=document.createElement('p');trend.className='reading-trend';trend.textContent='Trend unavailable';hero?.append(trend);
  void history().then(result=>{
    if(!trend.isConnected)return;
    const points=result.readings.filter(p=>p.source===w.air.source&&Number.isFinite(p.pm25)).sort((a,b)=>Date.parse(a.observedAt)-Date.parse(b.observedAt));
    trend.textContent=points.length<2?'Trend unavailable':points.at(-1).pm25>points.at(-2).pm25?'Rising · supplied observations':points.at(-1).pm25<points.at(-2).pm25?'Falling · supplied observations':'Stable · supplied observations';localizeDom();
  }).catch(()=>{trend.textContent='Trend unavailable';});
}
