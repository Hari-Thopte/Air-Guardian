// Shared school-day components. All actions and boundaries are supplied by the engine.
export const escape = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localizedNumber=(value,options={})=>window.AGLocale?.number(value,options)||new Intl.NumberFormat('en-IN',options).format(value);
export const when = (value,options) => window.AGRestyle?.formatTime(value,options) || (value ? new Date(typeof value==='number'?value*1000:value).toLocaleString() : 'Unavailable');
// These short labels describe engine action IDs; the full policy wording remains visible.
export function actionHeadline(action){
  return ({'indoor-pe':'Move PE and assembly indoors','gentle':'Shorter, gentler outdoor activities',
    'usual':'Keep the usual school timetable','verify':'Verify conditions before outdoor activities',
    'rotate':'Rotate outdoor duties and take indoor breaks','pickup':'Reduce waiting at the school gate'})[action?.id] || action?.text || 'Ask staff to verify conditions';
}
export function dayStrip(blocks){return `<div class="timetable-strip">${blocks.map(b=>`<article class="day-block ${escape(b.flag)}"><time>${escape(b.start)}–${escape(b.end)}</time><h3>${escape(b.name)}</h3><p>${b.actionId?escape(actionHeadline({id:b.actionId,text:b.action})):'No change'}</p><small>${b.outdoors?'Planned outdoors':'Planned indoors'} · ${b.minutes} min</small>${b.actionId?`<details><summary>Why?</summary><p>${escape(b.action)}</p><p>${escape(b.why)}</p></details>`:''}</article>`).join('')}</div>`;}
export function gaugeGeometry(value,bands=[15,35,60]){
  const maximum=Math.max(bands[2]*2,150);
  const angle=Math.PI*(1-Math.min(maximum,Math.max(0,Number(value)||0))/maximum);
  return {maximum,x:100+72*Math.cos(angle),y:100-72*Math.sin(angle)};
}
export function gauge(value,bands=[15,35,60]){
  const available=Number.isFinite(value),{maximum,x,y}=gaugeGeometry(value,bands);
  const arc=(start,end)=>{const a=Math.PI*(1-start/maximum),b=Math.PI*(1-end/maximum);return `M ${100+80*Math.cos(a)} ${100-80*Math.sin(a)} A 80 80 0 0 1 ${100+80*Math.cos(b)} ${100-80*Math.sin(b)}`;};

  return `<div class="planning-gauge" role="group" aria-label="PM2.5 ${available?localizedNumber(value,{minimumFractionDigits:1,maximumFractionDigits:1})+' micrograms per cubic metre':'unavailable'}; school planning bands, not official AQI"><div class="gauge-face"><svg viewBox="0 0 200 116" aria-hidden="true">${['green','yellow','orange','red'].map((f,i)=>`<path class="gauge-band ${available?f:'unknown'}" d="${arc(i?bands[i-1]:0,i===3?maximum:bands[i])}"/>`).join('')}${available?`<path class="needle" d="M100 100 L${x} ${y}"/><circle class="needle" cx="100" cy="100" r="4"/>`:''}</svg></div><div class="gauge-readout"><strong>${available?localizedNumber(value,{minimumFractionDigits:1,maximumFractionDigits:1}):'Unavailable'}</strong><span>PM2.5 · µg/m³</span><small>Planning bands, not official AQI</small></div></div>`;
}
export function receipts(summary,classes=[],{draft=false}={}){
  if(!summary)return '';
  const label=p=>p.class_id?(classes.find(c=>c.id===p.class_id)?.label||'Class')+' teacher':({admin:'School administrator',parent:'Parent / guardian',staff:'School duty team'})[p.role]||'School adult';
  return `<section class="card receipts-panel" id="receipts-panel"><h2>Plan reviews</h2><strong class="receipt-count">Reviews ${summary.confirmed} of ${summary.total}</strong><progress value="${summary.confirmed}" max="${summary.total||1}" aria-label="Adults who confirmed review"></progress><div class="review-people">${summary.people.map(p=>`<p><span ${p.class_id?`data-i18n="review.classTeacher" data-i18n-params="${escape(JSON.stringify([classes.find(c=>c.id===p.class_id)?.label||'Class']))}"`: ''}>${escape(label(p))}</span><b>${p.confirmed?'Reviewed':'Waiting'}</b></p>`).join('')}</div><small>${draft?'This draft has no confirmations. Publish it before requesting reviews.':'Records review, not health outcomes.'}</small></section>`;
}
const wrapper={en:'School instruction · original wording',hi:'स्कूल का निर्देश · मूल भाषा में',mr:'शाळेची सूचना · मूळ भाषेत'};
export function phone(note,flag,language='en'){
  return `<div class="phone-preview"><p>Air Guardian</p><span class="badge ${escape(flag)}">${escape(flag)}</span><h3 lang="${escape(language)}">${wrapper[language]||wrapper.en}</h3><p class="phone-message" data-original-wording>${escape(note)}</p><small>School wording is not automatically translated.</small></div>`;
}
