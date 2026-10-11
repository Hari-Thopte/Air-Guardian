// Public offline fallback only. Never cache private API data, auth or configuration.
const BUILD='round-20261011-a6';
const CACHE='airguardian-public-'+BUILD;
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.add('/offline.html'))));
self.addEventListener('activate',event=>event.waitUntil(Promise.all([self.clients.claim(),caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('airguardian-public-')&&k!==CACHE).map(k=>caches.delete(k))))])));
self.addEventListener('message',event=>{if(event.data?.type==='ACTIVATE')self.skipWaiting();});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/v1/')||url.pathname.includes('auth')||url.pathname.includes('config'))return;
  if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('/offline.html')));
});
self.addEventListener('push', event => {
  let data = {title:'Air Guardian',body:'Review your school’s current plan.'};
  try { data = {...data,...event.data.json()}; } catch { /* generic notice */ }
  event.waitUntil(self.registration.showNotification(data.title,{body:data.body,tag:'airguardian-school',data:{url:'/cloud.html'}}));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow('/cloud.html'));
});
