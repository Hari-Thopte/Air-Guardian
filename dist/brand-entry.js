// A brief brand introduction; independent of authentication or application loading.
const seen = sessionStorage.getItem('ag-brand-seen');
if (!seen) {
const intro = document.createElement('div');
intro.className = 'brand-entry';
intro.setAttribute('role', 'dialog');
intro.setAttribute('aria-modal', 'true');
intro.setAttribute('aria-label', 'Welcome to Air Guardian');
intro.innerHTML = `<div class="entry-orbit" aria-hidden="true"><span></span><img src="/assets/guardian-emblem.png" alt="" width="100" height="100"></div><p class="entry-kicker">A CLEARER SCHOOL DAY</p><h1>Air Guardian<span>A little clarity.<br>A better school day.</span></h1><div class="entry-track" aria-hidden="true"><span></span></div><button type="button">Enter website <span aria-hidden="true">↗</span></button>`;
const background = [...document.body.children].filter(el=>!['SCRIPT','LINK'].includes(el.tagName));
const states = background.map(el=>[el,el.inert]);
const previousFocus = document.activeElement;
states.forEach(([el])=>el.inert=true);
document.body.append(intro);
let dismissed = false;
function dismiss(){
  if(dismissed)return; dismissed=true;
  const hadFocus=intro.contains(document.activeElement);
  intro.remove(); states.forEach(([el,state])=>el.inert=state);
  if(hadFocus&&previousFocus&&previousFocus!==document.body)previousFocus.focus();
  else if(hadFocus)document.querySelector('#main')?.focus({preventScroll:true});
}
intro.querySelector('button').onclick=dismiss;
intro.addEventListener('keydown',e=>{if(e.key==='Escape')dismiss();if(e.key==='Tab'){e.preventDefault();intro.querySelector('button').focus();}});
intro.querySelector('button').focus({preventScroll:true});
sessionStorage.setItem('ag-brand-seen','1');
setTimeout(dismiss,seen?0:matchMedia('(prefers-reduced-motion: reduce)').matches?100:1400);

}
