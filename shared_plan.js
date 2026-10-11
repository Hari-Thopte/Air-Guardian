import {esc} from './ui.js';

const state={token:'',data:null,error:'',loading:false};

export function sharedPlanPage(token){
 state.token=token;
 if(state.loading&&!state.data)return `<main id="main" class="shared-plan-page" tabindex="-1"><section class="panel content-panel" role="status"><h1>Loading today’s school plan…</h1></section></main>`;
 if(state.error)return `<main id="main" class="shared-plan-page" tabindex="-1"><section class="panel content-panel empty-state"><h1>School plan unavailable</h1><p>${esc(state.error)}</p><button class="primary" data-shared-retry>Try again</button></section></main>`;
 if(!state.data)return `<main id="main" class="shared-plan-page" tabindex="-1"><section class="panel content-panel" role="status"><h1>Loading today’s school plan…</h1></section></main>`;
 const plan=state.data;
 return `<main id="main" class="shared-plan-page" tabindex="-1"><section class="panel content-panel shared-plan-card"><div class="panel-kicker">${esc(plan.school)} · TODAY’S SCHOOL PLAN</div><h1><span class="guardian-flag ${esc(plan.flag)}">${esc(plan.flag)}</span> Today’s flag</h1><article class="plan-notice"><h2>Notice from school</h2><p>${esc(plan.notice)}</p><small>Published ${esc(new Date(plan.publishedAt*1000).toLocaleString('en-IN'))}</small></article><button class="primary shared-review-button" data-shared-review ${plan.reviewed?'disabled':''}>${plan.reviewed?'I’ve read this':'I’ve read this'}</button>${plan.reviewed?'<p class="review-status" role="status">Review recorded. You can close this page.</p>':'<p class="micro">This link records one linked parent’s review. It contains no child details.</p>'}</section></main>`;
}

export async function loadSharedPlan(token,changed){
 state.loading=true;state.error='';changed();
 try{const response=await fetch('/api/guardian/shared-plan/'+encodeURIComponent(token),{headers:{Accept:'application/json'}});const body=await response.json();if(!response.ok)throw new Error(body.message||'The school plan could not be loaded.');state.data=body}
 catch(error){state.error=error.message;state.data=null}
 finally{state.loading=false;changed()}
}

export function bindSharedPlan(token,changed){
 document.querySelector('[data-shared-retry]')?.addEventListener('click',()=>void loadSharedPlan(token,changed));
 document.querySelector('[data-shared-review]')?.addEventListener('click',async event=>{event.currentTarget.disabled=true;try{const response=await fetch('/api/guardian/shared-plan/'+encodeURIComponent(token)+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const body=await response.json();if(!response.ok)throw new Error(body.message||'The review could not be recorded.');state.data={...state.data,reviewed:true};state.error=''}catch(error){state.error=error.message}changed()});
 if(!state.data&&!state.loading&&!state.error)void loadSharedPlan(token,changed);
}
