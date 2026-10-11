import './assets/ui.js';
import {roleIdentity} from './assets/role-ui.js';
import {dayStrip,escape,actionHeadline} from './assets/day-ui.js';
const instrument=document.querySelector('#day-instrument');
async function start(){
  const scenario=document.querySelector('#scenario'),hour=document.querySelector('#day-hour');
  let role='admin';
  let data=JSON.parse(document.querySelector('#default-scenario').textContent);
  function update(){
    const selected=data.scenarios.find(s=>s.name.toLowerCase()===scenario.value)||data.scenarios[0];
    const point=selected.hours[Number(hour.value)];
    const label=`${String(point.hour).padStart(2,'0')}:00`;
    document.querySelector('#hour-label').textContent=label;
    hour.setAttribute('aria-valuetext',`${label}, ${point.flag} school planning flag`);
    document.body.dataset.role=role;
    const roleContent=dayStrip(point.blocks);
    document.querySelector('#day-result').innerHTML=`<span class="badge ${escape(point.flag)}">${escape(point.flag)}</span><h3 id="simulator-role" data-action-code="${escape(point.actions[0].id)}">${role==='admin'?'':escape(roleIdentity[role].label)+' · '}${escape(actionHeadline(point.actions[0]))}</h3><p class="simulator-role-detail">${escape(roleIdentity[role].detail)}</p><p>Example PM2.5: ${point.pm25.toFixed(1)} µg/m³ · planning flag, not official AQI.</p><details><summary>Why this suggestion?</summary><p>${escape(point.headline)}</p><p>${escape(point.actions[0].why)}</p></details>${roleContent}`;
    window.AGRestyle.setFlag(point.flag,{example:true,pm25:point.pm25,boundaries:data.thresholds});window.AGRestyle.setHour(point.hour);
  }
  document.querySelectorAll('[data-sim-role]').forEach(button=>button.onclick=()=>{role=button.dataset.simRole;document.querySelectorAll('[data-sim-role]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));update();});
  update();
  scenario.disabled=true;scenario.setAttribute('aria-busy','true');
  scenario.onchange=update;hour.oninput=update;
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);
  try{
    const response=await fetch('/landing-scenarios.json',{signal:controller.signal});if(!response.ok)throw new Error('Examples unavailable');
    const loaded=await response.json();
    if(!Array.isArray(loaded.scenarios)||loaded.scenarios.some(s=>!Array.isArray(s.hours)||s.hours.length!==9))throw new Error('Invalid examples');
    data=loaded;const selected=scenario.value;
    scenario.innerHTML=data.scenarios.map(s=>`<option value="${escape(s.name.toLowerCase())}">${escape(s.name)} example</option>`).join('');scenario.value=selected;update();
  }catch(error){
    scenario.innerHTML='<option value="orange">Orange example</option>';scenario.value='orange';update();
    instrument.insertAdjacentHTML('beforeend','<p class="muted" role="status">The saved orange example is available offline. Other scenarios could not load.</p>');
  }finally{
    clearTimeout(timeout);scenario.disabled=false;scenario.removeAttribute('aria-busy');
  }
}
start();
