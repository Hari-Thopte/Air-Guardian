import {escape as esc} from './day-ui.js';

export function formDialog(selector,label){
  const form=document.querySelector(selector);if(!form)return;
  const opener=document.createElement('button');opener.type='button';opener.className='secondary';opener.textContent=label;
  form.before(opener);
  const dialog=document.createElement('dialog'),title=document.createElement('h2'),close=document.createElement('button');
  title.textContent=label;close.type='button';close.className='secondary';close.textContent='Close';
  dialog.append(title,form);if(selector==='#invite-form'){const result=document.querySelector('#invite-result');if(result)dialog.append(result);}dialog.append(close);opener.after(dialog);
  opener.onclick=()=>dialog.showModal();close.onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>opener.focus());
}
export function settings(w){
  const form=document.querySelector('#school-form');
  const groups=[['School',['name','timezone']],['Location',['lat','lon','cpcb_city']],['Building and ventilation',['building_type','ventilation','filtration','outdoor_area_score','outdoor_area_notes']],['School day',['school_start','school_end']]];
  const submit=form.querySelector('button');
  for(const [title,names] of groups){
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=title;details.append(summary);
    if(title==='School')details.open=true;
    names.forEach(name=>details.append(form.elements[name].closest('label')));form.insertBefore(details,submit);
  }
  const blocks=document.createElement('fieldset');blocks.id='school-blocks';blocks.innerHTML=`<legend>School-day blocks</legend><p>Editable defaults. Indoor alternatives need room and supervision review.</p>${(w.school.timetable||w.dayPlan.timetable).map((b,i)=>`<div class="block-editor" data-block="${i}"><label>Block name<input data-field="name" value="${esc(b.name)}" maxlength="60" required></label><label>Start<input data-field="start" type="time" value="${esc(b.start)}" required></label><label>End<input data-field="end" type="time" value="${esc(b.end)}" required></label><label class="check"><input data-field="outdoors" type="checkbox" ${b.outdoors?'checked':''}>Planned outdoors</label></div>`).join('')}`;
  form.lastElementChild.before(blocks);
  form.insertAdjacentHTML('afterbegin',`<p class="muted">${esc(w.school.name)} · ${w.school.lat.toFixed(4)}, ${w.school.lon.toFixed(4)} · ${esc(w.school.building_type)} building. Unknown ventilation or filtration does not imply clean air.</p>`);
  formDialog('#class-form','Add a class');formDialog('#room-form','Add a room');
}
export function blockValues(){return [...document.querySelectorAll('[data-block]')].map(row=>Object.fromEntries([...row.querySelectorAll('[data-field]')].map(input=>[input.dataset.field,input.type==='checkbox'?input.checked:input.value])));}

export async function people(w,fetchData){
  const root=document.querySelector('#panel'),result=await fetchData();if(!root.isConnected)return;
  const tabs=document.createElement('div');tabs.className='setup-tabs';tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','School people');
  const sets=[['Children (aliases)',['#child-form']],['Adults',['#invite-form']],['Parent links',['#guardian-link']]];
  const childrenTable=document.createElement('section');childrenTable.className='card';childrenTable.innerHTML=`<h2>Child aliases</h2><p>Use an alias. No date of birth or diagnosis is needed.</p><div class="scroll"><table><thead><tr><th>Alias</th><th>Class</th><th>Parent links</th></tr></thead><tbody>${result.children.map(c=>`<tr><td>${esc(c.alias)}</td><td>${esc(c.class_id)}</td><td>${c.guardians.length}</td></tr>`).join('')}</tbody></table></div>`;
  root.prepend(childrenTable);root.prepend(tabs);
  const childSection=document.querySelector('#child-form').closest('section'),adultSection=document.querySelector('#invite-form').closest('section'),linkSection=document.querySelector('#guardian-link').closest('section');
  const memberships=[...root.querySelectorAll('section')].find(s=>s.querySelector('h2')?.textContent==='School memberships');
  formDialog('#child-form','Add child alias');formDialog('#invite-form','Invite an adult');formDialog('#guardian-link','Link parent to child');
  const panels=[[childrenTable,childSection],[adultSection,memberships],[linkSection,childrenTable]];
  function select(index){panels.flat().forEach(p=>{if(p)p.hidden=true;});panels[index].forEach(p=>{if(p)p.hidden=false;});[...tabs.children].forEach((b,i)=>{b.setAttribute('aria-selected',String(i===index));b.tabIndex=i===index?0:-1;});}
  sets.forEach(([label],i)=>{const b=document.createElement('button');b.type='button';b.role='tab';b.textContent=label;b.onclick=()=>select(i);b.onkeydown=e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();const n=(i+(e.key==='ArrowRight'?1:2))%3;select(n);tabs.children[n].focus();}};tabs.append(b);});select(0);
}
export function sensors(w){
  const panel=document.querySelector('#panel');
  panel.insertAdjacentHTML('afterbegin','<p class="notice">Experimental sensors. Installation, calibration and placement review are required.</p>');
  formDialog('#device-form','Add sensor');
  const table=panel.querySelector('tbody');
  for(const device of w.devices||[]){if(w.sensors.some(s=>s.deviceId===device.id))continue;table.insertAdjacentHTML('beforeend',`<tr><td>${esc(device.id)}</td><td>Unavailable</td><td>Not installed</td><td>Unavailable</td><td>Registered identity only; no measurements.</td></tr>`);}
  [...table.rows].forEach((row,i)=>{const sensor=w.sensors[i];if(!sensor)return;row.cells[2].textContent=sensor.mode==='demo'&&sensor.deviceId==='demo-0'?'Not installed':sensor.quality==='usable'?'Active · experimental':sensor.quality==='review'?'Needs calibration or review':'Stale or offline';if(sensor.mode==='demo')row.cells[0].append(' · Demo data');});
  table.closest('table').classList.add('sensor-table');
  [...table.rows].forEach(row=>[...row.cells].forEach((cell,i)=>{cell.dataset.label=['Device','PM2.5 · µg/m³','Device status','Observed','Notes'][i]||'';}));
  if(!table.rows.length)table.innerHTML='<tr><td colspan="5">No sensors installed. Use Add sensor to register a device.</td></tr>';
}
