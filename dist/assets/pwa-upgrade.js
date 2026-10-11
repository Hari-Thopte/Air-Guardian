if('serviceWorker' in navigator){
  let requestedUpdate=false;
  navigator.serviceWorker.register('/cloud-sw.js').then(reg=>{
    function offer(){if(!reg.waiting)return;const button=document.createElement('button');button.className='secondary';button.textContent='Update available — reload';button.onclick=()=>{requestedUpdate=true;reg.waiting.postMessage({type:'ACTIVATE'});};document.querySelector('footer')?.prepend(button);}
    offer();reg.addEventListener('updatefound',()=>reg.installing?.addEventListener('statechange',()=>{if(reg.waiting&&navigator.serviceWorker.controller)offer();}));
  }).catch(()=>{});
  let reloading=false;navigator.serviceWorker.addEventListener('controllerchange',()=>{if(requestedUpdate&&!reloading){reloading=true;location.reload();}});
}
