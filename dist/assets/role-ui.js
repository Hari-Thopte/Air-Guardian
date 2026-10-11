import {escape as esc,dayStrip,phone,when} from './day-ui.js';

// Presentation identity only. The verified workspace membership remains authoritative.
export const roleIdentity={
  admin:{title:'Publish the plan',label:'Admin',detail:'Decide, publish and track reviews.',scene:'control',icon:'M4 3h16v18H4z M8 8h8 M8 12h8 M8 16h4'},
  teacher:{title:'My class',label:'Teacher',detail:'Check the timetable and confirm your class plan.',scene:'classroom',icon:'M3 4h18v12H3z M8 21l4-5 4 5 M7 8h10'},
  staff:{title:'Duty and gate',label:'Staff',detail:'Read the duty instruction and complete your checklist.',scene:'gate',icon:'M4 21V6h16v15 M8 6v15 M16 6v15 M4 11h16 M4 16h16'},
  parent:{title:'Today for my child',label:'Parent',detail:'Read the school message and prepare for pickup.',scene:'morning',icon:'M12 21s-9-5-9-12a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 7-9 12-9 12Z'},
  kid:{title:'Air Explorer',label:'Kid',detail:'One little air question, with a grown-up nearby.',scene:'explorer',icon:'M12 3v3 M12 18v3 M3 12h3 M18 12h3 M6 6l2 2 M16 16l2 2 M6 18l2-2 M16 8l2-2 M8 12a4 4 0 1 0 8 0 4 4 0 1 0-8 0'}
};
export function roleIcon(role){return `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${roleIdentity[role]?.icon||roleIdentity.admin.icon}"/></svg>`;}
export function roleContext(w){
  const role=w.membership.role;
  const className=id=>w.classes.find(c=>c.id===id)?.label||(id?'School-linked class':'Class not linked');
  return {identity:roleIdentity[role]||roleIdentity.admin,
    classLabel:role==='teacher'?className(w.membership.class_id):null,
    children:role==='parent'||role==='teacher'?(w.children||[]).map(c=>({alias:c.alias,classLabel:className(c.class_id),extraCaution:role==='teacher'&&Boolean(c.extraCaution)})):[],
    tasks:(w.checklist||[]).filter(task=>task.role===role)};
}
export function roleScene(role){
  const scenes={
    admin:'<path d="M20 104h190V34H20z M35 87V67h20v20 M75 87V53h20v34 M115 87V43h20v44 M155 87V58h30v29 M85 105v16h60v-16 M65 121h100"/>',
    teacher:'<path d="M25 115V20h180v95Z M115 20v95 M25 66h180 M42 132h150 M55 115v17 M175 115v17"/><path d="M42 44h48 M145 95h38"/>',
    staff:'<path d="M25 133V30h22v103 M183 133V30h22v103 M47 42h136 M47 70h136 M62 70v63 M85 70v63 M145 70v63 M168 70v63 M80 33l35-16 35 16"/>',
    parent:'<circle cx="171" cy="42" r="25"/><path d="M139 13l-9-9 M171 5V0 M208 18l10-10 M206 48h20 M15 131q100-43 205 0 M74 110V67l31-24 31 24v43 M96 110V85h18v25"/>',
    kid:'<circle cx="115" cy="68" r="48"/><path d="M91 60h2 M137 60h2 M94 83q21 20 42 0 M30 35l7-15 7 15 15 7-15 7-7 15-7-15-15-7Z M182 106l7-15 7 15 15 7-15 7-7 15-7-15-15-7Z"/>'
  };
  return `<svg class="role-scene-art" viewBox="0 0 240 150" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${scenes[role]||scenes.admin}</svg>`;
}
export function personalizeToday(w,state,{open,review,complete}){
  const role=w.membership.role,panel=document.querySelector('#panel');
  if(role==='admin')return;
  const context=roleContext(w),notice=state.notice;
  const evidence=document.createElement('details');evidence.className='role-evidence';
  evidence.innerHTML='<summary>Air evidence &amp; planning tools</summary>';
  const contents=document.createElement('div');while(panel.firstChild)contents.append(panel.firstChild);evidence.append(contents);
  const hub=document.createElement('section');hub.className='card role-hub';
  const ownReview=Boolean(notice&&(w.receipts||[]).some(r=>r.sub===w.membership.sub));
  const currentText=notice?notice.reasons.join(' '):'The school has not published the current plan. Ask a school adult for the instruction.';
  const taskRows=context.tasks.map(task=>{
    const done=(w.completions||[]).some(c=>c.taskId===task.id);
    return `<li><p>${esc(task.text)}</p><button class="secondary" data-role-task="${esc(task.id)}" ${!notice||done?'disabled':''}>${done?'Completion recorded':'Confirm completed'}</button></li>`;
  }).join('');
  hub.innerHTML=`<p class="eyebrow">${esc(context.identity.title)}</p><span class="badge ${esc(notice?.flag||w.planning.flag)}">${esc(notice?.flag||w.planning.flag)}</span><h2>${esc(role==='teacher'?context.classLabel:role==='staff'?'Your duty briefing':'A message from your school')}</h2><p class="muted">${notice?'Published '+esc(when(notice.time,{schoolEvent:true})):'Awaiting publication · suggestions are not school instructions'}</p>${role==='parent'?phone(currentText,notice?.flag||'unknown',w.preferences.language):`<p class="role-instruction">${esc(currentText)}</p>`}${role==='teacher'?`<h3>Class timetable</h3>${dayStrip(w.dayPlan.timetable)}<p>${context.children.length} linked students · ${context.children.filter(c=>c.extraCaution).length} need extra caution</p>`:''}${role==='parent'?`<div class="role-child-list">${context.children.map(c=>`<p><strong>${esc(c.alias)}</strong> · ${esc(c.classLabel)}</p>`).join('')||'<p>No child profiles linked. Ask your school administrator.</p>'}</div><div class="row"><button data-role-review ${!notice||ownReview?'disabled':''}>${ownReview?'Review recorded':'Mark as read'}</button><button class="secondary" data-role-open="plan">Read the full school plan</button></div><p class="muted">At pickup, follow the school’s published gate arrangements. Keep vehicle engines off while waiting where permitted.</p>`:`<button data-role-open="plan">${role==='teacher'?'Review & acknowledge class plan':'Read the full duty plan'}</button>${taskRows?`<h3>${role==='staff'?'Duty checklist':'Class checklist'}</h3><ul class="role-task-list">${taskRows}</ul>`:'<p>No duty tasks assigned to this plan yet.</p>'}`}${role==='teacher'?'<button class="secondary" data-role-open="classes">Open my class details</button>':''}`;
  panel.append(hub,evidence);
  hub.querySelectorAll('[data-role-open]').forEach(button=>button.onclick=()=>open(button.dataset.roleOpen));
  hub.querySelector('[data-role-review]')?.addEventListener('click',()=>review(notice.id));
  hub.querySelectorAll('[data-role-task]').forEach(button=>button.onclick=()=>complete(notice.id,button.dataset.roleTask));
}
