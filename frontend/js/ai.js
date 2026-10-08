/* Home dashboard, live rates, notifications, AI chat (Groq/Gemini via backend), AI photo scan */
let RT={},busy=false,ch=[],lastUnread=0;
Object.assign(T.en,{home:"Home",hello:"Hello",earned:"Total earned",bought:"Total purchased",kgsold:"Kg sold",kgbought:"Kg bought",openlots:"Open lots",avg:"Avg ₹/kg",byType:"Earnings by scrap type",nodata:"No sales yet. Your numbers appear after the first accepted offer.",scan:"Scan photo with AI",scanning:"Analysing photo...",pickphoto:"Choose a photo first.",found:"AI found",report:"Report rate",yourRate:"Your ₹/kg",upd3:"Rates are reported by verified recyclers on this platform. Dates show the last update.",upd2:"Update a rate to share what you pay today. All users see it.",notif:"Notifications",nonotif:"No notifications yet.",n_bid:"{who} bid ₹{amount} on lot {lot}",n_sold:"{who} accepted your bid of ₹{amount} on lot {lot}",aiHint:"AI answers use live platform rates. Tap 🎤 to talk."});
Object.assign(T.hi,{home:"होम",hello:"नमस्ते",earned:"कुल कमाई",bought:"कुल खरीद",kgsold:"बेचा (किलो)",kgbought:"खरीदा (किलो)",openlots:"खुले लॉट",avg:"औसत ₹/किलो",byType:"कबाड़ के हिसाब से कमाई",nodata:"अभी कोई बिक्री नहीं। पहला ऑफर मंज़ूर होते ही आँकड़े दिखेंगे।",scan:"AI से फोटो स्कैन करें",scanning:"फोटो देख रहा हूँ...",pickphoto:"पहले फोटो चुनें।",found:"AI ने पहचाना",report:"रेट बताएँ",yourRate:"आपका ₹/किलो",upd3:"रेट इस प्लेटफ़ॉर्म के सत्यापित रीसाइकलर बताते हैं। तारीख आखिरी अपडेट की है।",upd2:"आज जो रेट आप देते हैं वो अपडेट करें। सबको दिखेगा।",notif:"सूचनाएँ",nonotif:"अभी कोई सूचना नहीं।",n_bid:"{who} ने लॉट {lot} पर ₹{amount} की बोली लगाई",n_sold:"{who} ने लॉट {lot} पर आपकी ₹{amount} की बोली मंज़ूर की",aiHint:"AI जवाब लाइव रेट पर आधारित हैं। बोलने के लिए 🎤 दबाएँ।"});
const fmt=(k,d)=>t(k).replace(/\{(\w+)\}/g,(_,x)=>esc(d[x]??""));
async function loadRates(){try{RT=await api("/rates")}catch(e){}}
rate=function(id){return RT[id]?RT[id].price:S.find(x=>x[0]==id)[3]};
/* Home */
async function renderHome(){const el=$("#p-home");if(!el||!U)return;try{const s=await api("/stats"),col=U.role=="collector",mx=Math.max(1,...s.by_type.map(x=>x.amount));
el.innerHTML=`<h2 class="hi"></h2><div class="stats"><div class="card stat"><span class="mut">${t(col?"earned":"bought")}</span><div class="big">₹${Math.round(s.amount)}</div></div><div class="card stat"><span class="mut">${t(col?"kgsold":"kgbought")}</span><div class="big">${s.kg}</div></div><div class="card stat"><span class="mut">${t("openlots")}</span><div class="big">${s.open}</div></div><div class="card stat"><span class="mut">${t("avg")}</span><div class="big">₹${s.avg}</div></div></div><div class="card"><b>${t("byType")}</b>`+(s.by_type.length?s.by_type.map(x=>`<div style="margin-top:10px"><div class="row" style="flex-wrap:nowrap"><span>${esc(nm(S.find(y=>y[0]==x.type)))}</span><b style="flex:0 0 auto">₹${Math.round(x.amount)}</b></div><div class="bar" style="width:${Math.round(x.amount/mx*100)}%"></div></div>`).join(""):`<p class="mut">${t("nodata")}</p>`)+`</div>`;
$(".hi").textContent=t("hello")+", "+U.name+" 👋"}catch(e){el.innerHTML=`<div class="card mut">${esc(e.message)}</div>`}}
/* Rates (live from DB, recyclers can report) */
renderRate=async function(){const el=$("#p-rate");if(!el)return;await loadRates();const rec=U&&U.role=="recycler";
el.innerHTML=`<div class="card"><b>${t("rates")}</b><table>`+S.map(s=>{const r=RT[s[0]]||{price:s[3]};return `<tr><td>${esc(nm(s))}</td><td><b>₹${r.price}</b><div class="mut">${r.updated?new Date(r.updated*1000).toLocaleDateString():t("defRate")}</div></td>${rec?`<td><div class="row" style="flex-wrap:nowrap"><input type="number" min="1" id="r-${s[0]}" placeholder="${t("yourRate")}" aria-label="${t("yourRate")}" style="height:36px"><button class="btn sm" data-r="${s[0]}" style="flex:0 0 auto">${t("report")}</button></div></td>`:""}</tr>`}).join("")+`</table><p class="mut">${t(rec?"upd2":"upd3")}</p></div>`;
el.onclick=async e=>{const b=e.target.closest("[data-r]");if(!b)return;const v=+$("#r-"+b.dataset.r).value;if(!(v>0))return;try{await api("/rates/"+b.dataset.r,{method:"PUT",body:{amount:v}});renderRate()}catch(x){alert(x.message)}}};
/* AI photo scan */
async function shrink(f){const b=await createImageBitmap(f),k=Math.min(1,1024/Math.max(b.width,b.height)),c=document.createElement("canvas");c.width=b.width*k;c.height=b.height*k;c.getContext("2d").drawImage(b,0,0,c.width,c.height);return c.toDataURL("image/jpeg",.8).split(",")[1]}
const _rs2=renderSell;renderSell=function(){_rs2();$("#pv").insertAdjacentHTML("afterend",`<button type="button" class="btn alt sm" id="sc" style="margin-top:8px">✨ ${t("scan")}</button>`);
$("#sc").onclick=async()=>{const f=$("#ph").files[0];if(!f){$("#vm").textContent=t("pickphoto");return}$("#vm").textContent=t("scanning");
try{const r=await api("/ai/scan",{method:"POST",body:{image:await shrink(f),mime:"image/jpeg"}});if(r.type)$("#ty").value=r.type;if(r.kg>0)$("#wt").value=r.kg;$("#es").textContent="₹"+est();$("#vm").textContent=t("found")+": "+(r.note||"")}catch(e){$("#vm").textContent=e.message}}};
/* AI chat */
function draw2(){const c=$("#cl");if(!c)return;c.innerHTML=ch.map(()=>'<div class="m"></div>').join("");[...c.children].forEach((d,i)=>{d.className="m "+ch[i][0];d.textContent=ch[i][1]});c.scrollTop=c.scrollHeight}
renderChat=function(){const el=$("#p-chat");el.innerHTML=`<div class="card"><div class="chat" id="cl" aria-live="polite"></div><div class="row" style="flex-wrap:nowrap"><input id="ci" placeholder="${t("ask")}" aria-label="${t("ask")}" style="flex:3"><button class="btn" id="cs" style="flex:0 0 auto">${t("send")}</button><button class="ib" id="cm" aria-label="${t("speak")}" style="flex:0 0 auto">🎤</button></div><p class="mut" style="margin:10px 0 0">${t("aiHint")}</p></div>`;
if(!ch.length)ch.push(["b",t("hi")]);draw2();
const send=async(v,voice)=>{v=v.trim();if(!v||busy)return;busy=true;ch.push(["u",v],["b","…"]);draw2();$("#ci").value="";
try{const m=ch.slice(0,-1).filter((x,i)=>i>0||x[0]=="u").slice(-8).map(x=>({role:x[0]=="u"?"user":"assistant",content:x[1]}));const r=await api("/ai/chat",{method:"POST",body:{messages:m,lang:L}});ch[ch.length-1]=["b",r.reply];if(voice)speak(r.reply)}catch(e){ch[ch.length-1]=["b",e.message]}busy=false;draw2()};
$("#cs").onclick=()=>send($("#ci").value);$("#ci").onkeydown=e=>{if(e.key=="Enter")send(e.target.value)};
$("#cm").onclick=()=>{const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert(t("nov"));return}const r=new SR();r.lang=L=="hi"?"hi-IN":"en-IN";r.onresult=e=>send(e.results[0][0].transcript,true);r.start()}};
/* Notifications */
function ensureBell(){if($("#bell")||!$("#th"))return;const b=document.createElement("button");b.className="ib";b.id="bell";b.setAttribute("aria-label","Notifications");b.innerHTML='🔔<span id="bc" class="badge hide"></span>';$("#th").before(b);
const p=document.createElement("div");p.id="np";p.className="np hide";document.body.appendChild(p);
b.onclick=async()=>{p.classList.toggle("hide");if(!p.classList.contains("hide")){await loadNotes(true)}};
document.addEventListener("click",e=>{if(!p.contains(e.target)&&!b.contains(e.target))p.classList.add("hide")})}
async function loadNotes(open){if(!U)return;try{const d=await api("/notifications");const bc=$("#bc");bc.textContent=d.unread;bc.classList.toggle("hide",!d.unread);
if(d.unread>lastUnread&&!open)speak?.call&&0;lastUnread=d.unread;
$("#np").innerHTML=`<b>${t("notif")}</b>`+(d.items.length?d.items.map(n=>`<div class="ni ${n.read?"":"new"}">${fmt("n_"+n.kind,n.data)}<div class="mut">${new Date(n.created*1000).toLocaleString()}</div></div>`).join(""):`<p class="mut">${t("nonotif")}</p>`);
if(open&&d.unread){await api("/notifications/read",{method:"POST"});bc.classList.add("hide");lastUnread=0}}catch(e){}}
/* wire up */
const _all2=all;all=function(){_all2();ensureBell();renderHome();renderRate();loadNotes(false);const n=$("#bell");if(n)n.title=t("notif")};
const _boot=boot;boot=function(){loadRates().finally(_boot)};
setInterval(()=>{if(U&&!document.hidden)loadNotes(false)},15000);
const _logout=logout;logout=function(){ch=[];_logout()};
boot();
