import {localizeDom} from './locale.js';
const params=new URLSearchParams(location.search);
if(params.get('story')==='1'&&params.get('present')!=='1'){
  const bar=document.createElement('aside');bar.className='story-stepper';bar.setAttribute('aria-label','Demo story');
  const steps=[['Home','/home.html?story=1'],['Today','/cloud.html?role=admin&story=1'],['Publish','/cloud.html?role=admin&story=1#plan'],['Parent view','/cloud.html?role=parent&story=1#plan'],['Mark as read','/cloud.html?role=parent&story=1#plan'],['Receipts','/cloud.html?role=admin&story=1']];
  for(const [label,url] of steps){const link=document.createElement('a');link.textContent=label;link.href=url;bar.append(link);}
  document.body.append(bar);localizeDom();
}
