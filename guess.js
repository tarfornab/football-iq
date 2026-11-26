"use strict";
const byId = id => document.getElementById(id);
const cfg = JSON.parse(byId("config").textContent);
const ar = document.documentElement.lang === "ar";
const tr = (en, arabic) => ar ? arabic : en;
if (ar) document.documentElement.dir = "rtl";
const aliases = {
  "Manchester United":["man utd","man united","مانشستر يونايتد"],"Manchester City":["man city","مانشستر سيتي"],
  "Barcelona":["barca","barça","برشلونة"],"Real Madrid":["ريال مدريد"],"Atlético Madrid":["atleti","atletico de madrid","أتلتيكو مدريد"],
  "Inter Milan":["inter","internazionale","إنتر ميلان"],"AC Milan":["milan","ميلان"],"Tottenham Hotspur":["spurs","توتنهام"],
  "PSG":["paris","paris saint germain","باريس سان جيرمان"],"Juventus":["juve","يوفنتوس"],"Liverpool":["ليفربول"],
  "Chelsea":["تشيلسي"],"Arsenal":["آرسنال","أرسنال"],"Athletic Club":["athletic bilbao"],"Brighton":["brighton and hove albion"],
  "Bournemouth":["afc bournemouth"],"Roma":["as roma"],"Deportivo La Coruña":["depor","deportivo de la coruna"]
};
const norm = s => s.toLowerCase().normalize("NFD").replace(/\p{M}/gu,"").replace(/[^\p{L}\p{N}]/gu,"");
const keys = name => [name,...(aliases[name] || [])].map(norm);
const input = byId("club");
let state, busy = false, clockEnd = 0, drawn = -1;
byId("title").textContent = tr("Guess the Clubs","خمّن الأندية");
byId("label").textContent = tr("Which club?","أي نادٍ؟");
byId("submit").ariaLabel = tr("Submit guess","إرسال التخمين");
byId("back").textContent = tr("Back to games","العودة للألعاب");
byId("instructions").textContent = cfg.host ? tr("Identify as many clubs as you can in two minutes.","خمّن أكبر عدد من الأندية خلال دقيقتين.") : tr("Waiting for the host to start.","بانتظار بدء المضيف.");
if (cfg.host) {
  byId("start").textContent = tr("Start · 2:00","ابدأ · 2:00");
  byId("start").onclick = () => sync({start:true});
}
function draw(rows) {
  byId("formation").replaceChildren(...rows.map(row => {
    const div = document.createElement("div"); div.className = "row";
    row.forEach(code => {
      const img = new Image(); img.src = "/static/flags/"+code+".svg";
      const home = {"gb-eng":"England","gb-nir":"Northern Ireland","gb-sct":"Scotland","gb-wls":"Wales"};
      img.alt = home[code] || new Intl.DisplayNames([ar?"ar":"en"],{type:"region"}).of(code.toUpperCase());
      div.append(img);
    }); return div;
  }));
}
function showClock() {
  const s = state?.phase === "playing" ? Math.max(0,Math.ceil((clockEnd-performance.now())/1000)) : state?.seconds ?? 120;
  byId("clock").textContent = Math.floor(s/60)+":"+String(s%60).padStart(2,"0");
}
function show(s) {
  state=s; clockEnd=performance.now()+s.seconds*1000; showClock();
  byId("score").textContent=tr("Score","النقاط")+" · "+s.index;
  byId("waiting").hidden=s.phase!=="waiting"; byId("play").hidden=s.phase!=="playing";
  if (s.phase==="playing" && drawn!==s.index) {
    draw(s.rows); drawn=s.index; input.value=""; byId("suggestions").replaceChildren();
  }
  byId("results").hidden=!["complete","finished"].includes(s.phase);
  if (!byId("results").hidden) {
    byId("resultTitle").textContent=s.phase==="complete"?tr("All clubs guessed","خمّنت جميع الأندية"):tr("Final score","النتيجة النهائية");
    byId("ranking").replaceChildren(...s.scores.sort((a,b)=>b.score-a.score).map(e=>{
      const li=document.createElement("li");li.textContent=e.name+" · "+e.score;return li;
    }));
  }
}
async function sync(data) {
  if (busy) return;
  busy=true;
  try {
    const res=await fetch(cfg.url,data?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}:{cache:"no-store"});
    if(!res.ok) throw Error();
    const [s,feedback]=await res.json();show(s);
    if(feedback) byId("message").textContent=feedback==="correct"?tr("Correct!","صحيح!"):tr("Try another club.","جرّب ناديًا آخر.");
  } catch {byId("message").textContent=tr("Connection interrupted. Retrying…","انقطع الاتصال. جارٍ إعادة المحاولة…");}
  finally {busy=false;}
}
function guess(name) {
  if(busy || state?.phase!=="playing") return;
  input.value=name;byId("suggestions").replaceChildren();sync({club:name,index:state.index});
}
input.oninput=()=>{
  const q=norm(input.value);
  byId("suggestions").replaceChildren(...(q?cfg.clubs.filter(c=>keys(c).some(k=>k.includes(q))).slice(0,7):[]).map(name=>{
    const b=document.createElement("button");b.type="button";b.textContent=name;b.onclick=()=>guess(name);return b;
  }));
};
byId("answer").onsubmit=e=>{
  e.preventDefault();const match=cfg.clubs.find(c=>keys(c).includes(norm(input.value)));
  if(match) guess(match);else byId("message").textContent=tr("Choose a club from the suggestions.","اختر ناديًا من الاقتراحات.");
};
sync();setInterval(showClock,200);
setInterval(()=>{if(!state || state.phase==="waiting" || state.phase==="complete" || (state.phase==="playing" && performance.now()>=clockEnd))sync();},700);
