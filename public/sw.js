const CACHE='gursha-app-v3.0.0';
const CORE=['./','index.html','style.css?v=3.0.0','app.js?v=3.0.0','engine.js','guidance.js','portions.js','planner.js','vault.js','assets/gursha-logo.png','assets/food-placeholder.svg','data/foods.json','data/images.json'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('gursha-app-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin)return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok&&!url.search&&['/data/','/images/','/assets/'].some(path=>url.pathname.includes(path))){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy)).catch(()=>{});}
    return response;
  }).catch(async()=>await caches.match(event.request)||((event.request.mode==='navigate')?await caches.match('index.html'):Response.error())));
});
