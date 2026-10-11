const CACHE='airguardian-shell-v8';
const SHELL=['/brand-refresh.css','/assets/guardian-emblem.png','/brand-entry.js','/brand-entry.css','/','/index.html','/landing.js','/shared_plan.js','/experience.css','/feedback.css','/assets/kids-air-day.svg','/assets/school-day.svg','/app.js','/ui.js','/kids.js','/kids_experience.js','/campus.js','/guardian.js','/guardian_services.js','/workspace.js','/workspace_extras.js','/i18n.js','/pwa.js','/data.js','/services.js','/styles.css','/redesign.css','/refinement.css','/guardian.css','/assets/logo-still.svg','/assets/logo.svg'];
const ILLUSTRATIONS=['/assets/kids-reading-v2.webp','/assets/campus-landscape.webp'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('airguardian-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(url.origin!==self.location.origin||event.request.method!=='GET')return;
 if(url.pathname.startsWith('/api/')){
  event.respondWith(fetch(event.request).catch(()=>new Response(JSON.stringify({message:'Offline. Current readings and private school records are unavailable.'}),{status:503,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}})));return;
 }
 if(SHELL.includes(url.pathname)||ILLUSTRATIONS.includes(url.pathname))event.respondWith(fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)))}return response}).catch(()=>caches.match(event.request).then(cached=>cached||(ILLUSTRATIONS.includes(url.pathname)?new Response('',{status:503}):caches.match('/index.html')))));
});
self.addEventListener('push',event=>{let data={title:'Air Guardian',body:'Check your latest school plan.',url:'/?page=guardian'};try{data={...data,...event.data.json()}}catch{}event.waitUntil(self.registration.showNotification(data.title,{body:data.body,icon:'/assets/logo-still.svg',tag:'school-air-update',data:{url:data.url}}))});
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil(self.clients.openWindow(event.notification.data?.url||'/?page=guardian'))});
