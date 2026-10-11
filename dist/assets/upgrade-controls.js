import {getLanguage,localizeDom,t} from './locale.js';
const bar=document.createElement('div');bar.className='upgrade-controls';
const reduce=document.createElement('button');reduce.className='secondary';reduce.textContent='Reduce effects';
reduce.setAttribute('aria-pressed','false');
reduce.onclick=()=>{const active=reduce.getAttribute('aria-pressed')!=='true';reduce.setAttribute('aria-pressed',String(active));document.body.dataset.effects=active?'reduced':'full';};
const size=document.createElement('button');size.className='secondary';size.textContent='Larger text';size.setAttribute('aria-pressed','false');
size.onclick=()=>{const active=size.getAttribute('aria-pressed')!=='true';size.setAttribute('aria-pressed',String(active));document.documentElement.style.fontSize=active?'18px':'16px';};
bar.append(reduce,size);document.querySelector('footer')?.prepend(bar);
const marker=document.createElement('p');marker.className='translation-review';marker.setAttribute('role','status');document.querySelector('header')?.after(marker);
function review(){marker.hidden=getLanguage()==='en';marker.textContent=t('ui.native-review');localizeDom();}
review();window.addEventListener('ag:language',review);
document.addEventListener('visibilitychange',()=>{document.body.dataset.tabHidden=String(document.hidden);});
window.addEventListener('pagehide',()=>window.speechSynthesis?.cancel());
