/* Service worker: app shell works offline. API (other origin) always goes to the network. */
const V = "kc-v8", SHELL = ["./", "index.html", "config.js?v=8", "css/style.css?v=8", "js/core.js?v=8", "js/app.js?v=8", "js/ai.js?v=8", "js/ui.js?v=8", "js/v5.js?v=8", "js/v6.js?v=8", "manifest.json", "icons/icon-192.png"];
self.addEventListener("install", e => e.waitUntil(caches.open(V).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== V).map(x => caches.delete(x)))).then(() => clients.claim())));
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET" || new URL(r.url).origin !== location.origin) return;
  e.respondWith(fetch(r, { cache: "no-cache" }).then(res => { if (res.ok) { const cp = res.clone(); caches.open(V).then(c => c.put(r, cp)); } return res; })
    .catch(() => caches.match(r).then(m => m || caches.match("index.html"))));
});
