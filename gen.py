#!/usr/bin/env python3
"""Vygeneruje index.html (prehľad skladu e-shopu) zo snímky stock.json.

stock.json = dokument export/stock z artifactu Eshop Watcher:
{at, neg[], out[], min[], claim[], rest, fade[], catalog}
riadky: {c: kód, n: názov, a: stav, m: minimum, r: rezervované, f: nové za 7 dní}
fade:   {c, n, o: odišlo za 7 dní, a, m, d: dní do vypredania}
Použitie: SKLAD_HESLO=... python3 gen.py stock.json index.html [sales.json]
sales.json (voliteľné) = dokument export/sales z Watchera: obrat bez DPH, MoM/YoY a priebeh mesiaca.
Dáta sú v stránke zašifrované (AES-GCM, kľúč z hesla cez PBKDF2); bez hesla nie sú čitateľné.
"""
import json, sys, os, datetime, zoneinfo, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

src, out = sys.argv[1], sys.argv[2]
data = json.load(open(src, encoding="utf-8"))
if len(sys.argv) > 3:
    data["sales"] = json.load(open(sys.argv[3], encoding="utf-8"))
tz = zoneinfo.ZoneInfo("Europe/Bratislava")
at = datetime.datetime.fromtimestamp(data["at"] / 1000, tz)
now = datetime.datetime.now(tz)
age_h = (now - at).total_seconds() / 3600
data["atText"] = f"{at.day}. {at.month}. {at.year} o {at:%H:%M}"
data["genText"] = f"{now.day}. {now.month}. {now.year} o {now:%H:%M}"
data["stale"] = age_h > 12
data.setdefault("chg", [])
if isinstance(data.get("rest"), int):
    data["restPending"] = data["rest"]
    data["rest"] = []
pw = os.environ.get("SKLAD_HESLO", "")
if not pw:
    sys.exit("Chýba heslo v premennej SKLAD_HESLO")
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=310000).derive(pw.encode("utf-8"))
ct = AESGCM(key).encrypt(iv, json.dumps(data, ensure_ascii=False).encode("utf-8"), None)
blob = base64.b64encode(salt + iv + ct).decode("ascii")

html = """<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive,nosnippet,noimageindex">
<meta name="googlebot" content="noindex,nofollow,noarchive,nosnippet">
<meta name="bingbot" content="noindex,nofollow,noarchive,nosnippet">
<title>Prehľad</title>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{color-scheme:light dark;--bg:light-dark(#fff,#0f1a13);--panel:light-dark(#f3f7f3,#16241b);--ink:light-dark(#13261a,#e8f1ea);--mute:light-dark(#5d6f62,#9fb3a5);--line:light-dark(#dfe8e0,#26392c);--g:light-dark(#2e7d32,#6fcf75);--red:light-dark(#c62828,#ff7b72);--amb:light-dark(#a86200,#f2b84b);--g2:light-dark(#a5c9a7,#3d6b42);--pm:light-dark(#3f6fb5,#8fb4ff)}
*{box-sizing:border-box;min-width:0}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 Inter,system-ui,sans-serif}
.band{padding:clamp(18px,3vw,36px) max(4vw,16px)}.wrap{max-width:1240px;margin:0 auto}
h1{font:700 clamp(26px,3.4vw,38px)/1.05 "Inter Tight",sans-serif;margin:0}h1 span{color:var(--g)}
h2{font:700 22px/1.2 "Inter Tight",sans-serif;margin:0 0 4px}
.sub{color:var(--mute);font-size:14px}
.warn{margin-top:12px;padding:10px 14px;border-radius:10px;background:light-dark(#fff4e5,#2b2210);color:var(--amb);font-size:14px}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:20px}
.card{background:var(--panel);border-radius:12px;padding:14px;border:2px solid transparent;cursor:pointer;text-align:left;font:inherit;color:inherit}
.card b{display:block;font:300 40px/1 "Inter Tight"}.card.r b{color:var(--red)}.card.a b{color:var(--amb)}
.card small{color:var(--mute);font-size:13px}.card.sel{border-color:var(--ink)}
.card:focus-visible{outline:3px solid var(--g);outline-offset:2px}
table{width:100%;border-collapse:collapse;font-size:15px;margin-top:10px}
th{text-align:left;font:600 13px Inter;color:var(--mute);border-bottom:1px solid var(--line);padding:8px}
td{border-bottom:1px solid var(--line);padding:9px 8px;vertical-align:top}
td.num,th.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.code{white-space:nowrap;color:var(--mute);font-size:14px}.neg{color:var(--red);font-weight:700}
.dd{display:inline-block;margin-left:6px;font-size:12px;font-weight:700;padding:0 6px;border-radius:99px}.dd.pl{color:var(--g);background:light-dark(#e6f3e7,#1d3322)}.dd.mi{color:var(--red);background:light-dark(#fde8e8,#3a1715)}
.tag{display:inline-block;font-size:12px;font-weight:600;padding:1px 7px;border-radius:99px;background:light-dark(#fde8e8,#3a1715);color:var(--red);margin-left:6px}
.empty{color:var(--mute);padding:16px 8px}
.money{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:clamp(16px,3vw,40px)}
.big{font:300 clamp(40px,6vw,64px)/1 "Inter Tight",sans-serif;white-space:nowrap;margin-top:8px}
.delta{font:600 16px Inter;margin-top:6px}.up{color:var(--g)}.down{color:var(--red)}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:18px}
.stat{background:var(--panel);border-radius:12px;padding:12px 14px}.stat b{display:block;font:600 20px "Inter Tight";white-space:nowrap}.stat small{color:var(--mute);font-size:13px;display:block}
.fig{position:relative;min-height:280px}.fig>svg{position:absolute;inset:0;width:100%;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--mute);margin-top:6px}
.legend i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:6px;background:var(--g)}.legend i.ly{background:var(--g2)}.legend i.pm{background:var(--pm)}
@media(max-width:760px){.money{grid-template-columns:minmax(0,1fr)}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
input{font:16px Inter;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);width:min(360px,100%);margin-top:14px}
footer{color:var(--mute);font-size:13px;border-top:1px solid var(--line)}
@media(max-width:900px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:560px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){table{font-size:13px}.stack thead{display:none}.stack tr{display:grid;padding-block:10px;border-bottom:1px solid var(--line)}.stack td{display:flow-root;border:0;padding:3px 0;padding-inline-start:8em;text-align:start}.stack td::before{content:attr(data-l);float:inline-start;width:7.5em;margin-inline-start:-8em;color:var(--mute)}}
</style>
</head>
<body>
<div class="band" id="lock"><div class="wrap" style="max-width:420px">
  <h1>E-shop · <span>sklad</span></h1>
  <form id="pwf" style="margin-top:18px"><label for="pw" class="sub">Heslo</label><br>
  <input id="pw" type="password" autocomplete="current-password" required style="margin-top:6px">
  <button type="submit" style="font:600 15px Inter;min-height:44px;padding:0 18px;border-radius:10px;border:0;background:var(--g);color:light-dark(#fff,#0f1a13);margin-top:10px;cursor:pointer">Otvoriť</button>
  <div class="sub" id="pwmsg" style="margin-top:8px"></div></form>
</div></div>
<div id="app" hidden>
<header class="band"><div class="wrap">
  <h1>E-shop · <span>prehľad</span></h1>
  <div class="sub" id="when"></div>
</div></header>
<section class="band" id="salesSec" hidden style="padding-top:0"><div class="wrap money">
  <div>
    <h2 id="mtitle">Obrat</h2>
    <div class="sub" id="mrange"></div>
    <div class="big" id="mtd"></div>
    <div class="delta" id="yoy"></div>
    <div class="delta" id="mom"></div>
    <div class="stats">
      <div class="stat"><small>Objednávky</small><b id="cnt"></b><small id="cntx"></small></div>
      <div class="stat"><small>Priemerná objednávka</small><b id="aov"></b><small id="aovx"></small></div>
      <div class="stat"><small>Odhad celého mesiaca</small><b id="proj"></b><small id="projx"></small></div>
    </div>
  </div>
  <div>
    <div class="fig" id="chart"><svg id="svg" role="img" aria-label="Kumulatívny obrat po dňoch"></svg></div>
    <div class="legend"><span><i></i><span id="lgNow"></span></span><span><i class="pm"></i><span id="lgPm"></span></span><span><i class="ly"></i><span id="lgLy"></span></span></div>
  </div>
</div></section>
<section class="band" style="padding-top:0"><div class="wrap">
  <h2>Zmena od včera</h2>
  <div class="sub">Produkty, ktorých stav sa zmenil od polnoci (▲ príjem, ▼ úbytok).</div>
  <table class="stack" id="chgTbl"></table>
  <h2 style="margin-top:28px">Sklad</h2>
  <div class="warn" id="stale" hidden></div>
  <div class="cards" id="cards"></div>
  <input id="q" type="search" placeholder="Hľadať kód alebo produkt" aria-label="Hľadať kód alebo produkt">
  <table class="stack" id="tbl"></table>
</div></section>
<section class="band" style="padding-top:0"><div class="wrap">
  <h2>Najrýchlejšie ubúda</h2>
  <div class="sub">Úbytok za posledných 7 dní. „Vydrží“ = stav ÷ priemerný denný úbytok.</div>
  <table class="stack" id="fade"></table>
</div></section>
<footer class="band"><div class="wrap">Vynechané sú postele, sety s posteľou alebo matracom, produkty na dopyt (0,01 €) a skryté produkty. Stránka sa aktualizuje každé ráno o 7:00. <a href="#" id="logout" style="color:inherit">Odhlásiť</a></div></footer>
</div>
<script id="data" type="text/plain">__DATA__</script>
<script>
{
const $=id=>document.getElementById(id);
const RAW=Uint8Array.from(atob($("data").textContent.trim()),c=>c.charCodeAt(0));
async function decrypt(pw){
  const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]);
  const key=await crypto.subtle.deriveKey({name:"PBKDF2",salt:RAW.slice(0,16),iterations:310000,hash:"SHA-256"},base,{name:"AES-GCM",length:256},false,["decrypt"]);
  const pt=await crypto.subtle.decrypt({name:"AES-GCM",iv:RAW.slice(16,28)},key,RAW.slice(28));
  return JSON.parse(new TextDecoder().decode(pt));
}
const store={get(){try{return localStorage.getItem("sklad-pw")}catch{return null}},set(v){try{v?localStorage.setItem("sklad-pw",v):localStorage.removeItem("sklad-pw")}catch{}}};
async function unlock(pw,remember){
  try{const D=await decrypt(pw);if(remember)store.set(pw);$("lock").hidden=true;$("app").hidden=false;start(D)}
  catch{store.set(null);$("pwmsg").textContent="Nesprávne heslo."}
}
$("pwf").addEventListener("submit",e=>{e.preventDefault();$("pwmsg").textContent="Overujem…";unlock($("pw").value,true)});
$("logout").addEventListener("click",e=>{e.preventDefault();store.set(null);location.reload()});
{const s=store.get();if(s)unlock(s,false)}
function start(D){
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const nf=new Intl.NumberFormat("sk-SK",{maximumFractionDigits:1}),n=v=>v==null?"–":nf.format(v);
const dd=d=>!d?"":`<span class="dd ${d>0?"pl":"mi"}" title="zmena od včera">${d>0?"▲ +":"▼ −"}${n(Math.abs(d))}</span>`;
$("when").textContent=`Stav skladu k ${D.atText} · vygenerované ${D.genText}`;
if(D.stale){$("stale").hidden=false;$("stale").textContent=`Pozor: údaje sú staršie ako 12 hodín (posledná kontrola ${D.atText}).`}
const T=[["neg","Záporný stav","r"],["out","Vypredané (s minimom)","r"],["min","Na/pod minimom","a"],["rest","Vypredané bez minima",""]];
let tab=location.hash.slice(1);if(!T.some(t=>t[0]===tab))tab="neg";
function cards(){$("cards").innerHTML=T.map(([k,l,c])=>`<button class="card ${c} ${k===tab?"sel":""}" data-k="${k}"><b>${k==="rest"&&D.restPending?D.restPending:D[k].length}</b><small>${esc(l)}</small></button>`).join("")}
function chgTable(){
  const L=D.chg||[];
  if(!L.length){$("chgTbl").innerHTML=`<tbody><tr><td class="empty">Od polnoci sa stav skladu nezmenil.</td></tr></tbody>`;return}
  $("chgTbl").innerHTML=`<thead><tr><th>Kód</th><th>Produkt</th><th class="num">Zmena</th><th class="num">Stav</th><th class="num">Minimum</th></tr></thead><tbody>`+
   L.map(r=>`<tr><td class="code">${esc(r.c)}</td><td>${esc(r.n)}</td><td class="num">${dd(r.d)}</td><td class="num ${r.a<0?"neg":""}">${n(r.a)}</td><td class="num">${n(r.m)}</td></tr>`).join("")+`</tbody>`;
}
function table(){
  const q=$("q").value.trim().toLowerCase(),list=D[tab].filter(r=>!q||(r.c+" "+r.n).toLowerCase().includes(q));
  if(!list.length){$("tbl").innerHTML=`<tbody><tr><td class="empty">${tab==="rest"&&D.restPending?`Zoznam (${D.restPending} položiek) pribudne pri ďalšej aktualizácii.`:"Nič tu nie je."}</td></tr></tbody>`;return}
  $("tbl").innerHTML=`<thead><tr><th>Kód</th><th>Produkt</th><th class="num">Stav</th><th class="num">Minimum</th></tr></thead><tbody>`+
   list.map(r=>`<tr><td class="code">${esc(r.c)}</td><td>${esc(r.n)}${r.f?'<span class="tag">nové za 7 dní</span>':""}</td><td class="num ${r.a<0?"neg":""}">${n(r.a)}${dd(r.d)}</td><td class="num">${n(r.m)}</td></tr>`).join("")+`</tbody>`;
}
function fade(){
  if(!D.fade.length){$("fade").innerHTML=`<tbody><tr><td class="empty">Za posledných 7 dní žiadny úbytok.</td></tr></tbody>`;return}
  $("fade").innerHTML=`<thead><tr><th>Kód</th><th>Produkt</th><th class="num">Odišlo za 7 dní</th><th class="num">Stav</th><th class="num">Minimum</th><th class="num">Vydrží</th></tr></thead><tbody>`+
   D.fade.map(r=>`<tr><td class="code">${esc(r.c)}</td><td>${esc(r.n)}</td><td class="num">${n(r.o)}</td><td class="num ${r.a<0?"neg":""}">${n(r.a)}${dd(r.dd)}</td><td class="num">${n(r.m)}</td><td class="num ${r.d<7?"neg":""}">${r.a<=0?"vypredané":"~"+n(Math.round(r.d))+" dní"}</td></tr>`).join("")+`</tbody>`;
}
$("cards").addEventListener("click",e=>{const b=e.target.closest("[data-k]");if(b){tab=b.dataset.k;history.replaceState(null,"","#"+tab);cards();table()}});
$("q").addEventListener("input",table);
new MutationObserver(()=>{for(const c of document.querySelectorAll('.stack td:not([data-l])')){let i=0,p=c;while(p=p.previousElementSibling)i+=p.colSpan;c.dataset.l=c.closest('table').rows[0].cells[i]?.textContent||''}}).observe(document.body,{childList:true,subtree:true});
chgTable();cards();table();fade();
if(D.sales)sales(D.sales);
}
function sales(S){
  const nf=new Intl.NumberFormat("sk-SK",{maximumFractionDigits:1});
  const eur=new Intl.NumberFormat("sk-SK",{style:"currency",currency:"EUR",maximumFractionDigits:0}),eur2=new Intl.NumberFormat("sk-SK",{style:"currency",currency:"EUR",maximumFractionDigits:2});
  $("salesSec").hidden=false;
  $("mtitle").textContent=`Obrat ${S.month} ${S.year}`;
  $("mrange").textContent=`1.–${S.day}. ${S.month} · bez DPH, bez stornovaných`;
  $("mtd").textContent=eur.format(S.mtd);
  const dl=(el,v,base,txt)=>{const d=v-base,p=base?d/base*100:null;el.className="delta "+(d>=0?"up":"down");el.textContent=`${d>=0?"+":"−"}${eur.format(Math.abs(d))}${p!=null?` (${d>=0?"+":"−"}${nf.format(Math.abs(p))} %)`:""} ${txt} (${eur.format(base)})`};
  dl($("yoy"),S.mtd,S.lmtd,`oproti 1.–${S.lyDay}. ${S.month} ${S.year-1}`);
  dl($("mom"),S.mtd,S.pmtd,`oproti 1.–${S.pmDay}. ${S.pmMonth} ${S.pmYear}`);
  $("cnt").textContent=S.cnt;$("cntx").textContent=`min. mesiac ${S.pcnt} · min. rok ${S.lcnt}`;
  $("aov").textContent=S.cnt?eur2.format(S.mtd/S.cnt):"–";$("aovx").textContent=`min. mesiac ${S.pcnt?eur2.format(S.pmtd/S.pcnt):"–"} · min. rok ${S.lcnt?eur2.format(S.lmtd/S.lcnt):"–"}`;
  $("proj").textContent=S.proj?eur.format(S.proj):"–";$("projx").textContent=`celý ${S.pmMonth}: ${eur.format(S.pfull)} · ${S.month} ${S.year-1}: ${eur.format(S.lfull)}`;
  $("lgNow").textContent=`${S.month} ${S.year}`;$("lgPm").textContent=`${S.pmMonth} ${S.pmYear}`;$("lgLy").textContent=`${S.month} ${S.year-1}`;
  const s=$("svg");
  const draw=()=>{const W=s.clientWidth,H=s.clientHeight;if(!W)return;const {cur,ly,pm,dim}=S,small=W<520;
    const max=Math.max(1,...cur,...ly,...pm)*1.08,L=small?8:58,R=12,T=12,B=26;
    const x=i=>L+i/dim*(W-L-R),yv=v=>T+(1-v/max)*(H-T-B),path=a=>a.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${yv(v).toFixed(1)}`).join("");
    let g="";for(let k=0;k<=4;k++){const v=max/4*k,yy=yv(v);g+=`<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" stroke="var(--line)"/>`;if(!small)g+=`<text x="${L-8}" y="${yy+4}" text-anchor="end" font-size="12" fill="var(--mute)">${Math.round(v/1000)} tis.</text>`}
    for(const dd of [1,10,20,dim])g+=`<text x="${x(dd)}" y="${H-6}" text-anchor="middle" font-size="12" fill="var(--mute)">${dd}.</text>`;
    g+=`<path d="${path(ly)}" fill="none" stroke="var(--g2)" stroke-width="2.5" stroke-dasharray="5 4"/>`;
    g+=`<path d="${path(pm)}" fill="none" stroke="var(--pm)" stroke-width="2.5" stroke-dasharray="2 4" stroke-linecap="round"/>`;
    g+=`<path d="${path(cur)}" fill="none" stroke="var(--g)" stroke-width="3.5" stroke-linejoin="round"/>`;
    const li=cur.length-1;g+=`<circle cx="${x(li)}" cy="${yv(cur[li])}" r="5" fill="var(--g)"/>`;s.innerHTML=g};
  new ResizeObserver(draw).observe($("chart"));draw();
}
}
</script>
</body>
</html>
"""
open(out, "w", encoding="utf-8").write(html.replace("__DATA__", blob))
print(f"OK {out}: neg={len(data['neg'])} out={len(data['out'])} min={len(data['min'])} claim={len(data['claim'])} chg={len(data['chg'])} rest={len(data['rest'])} fade={len(data['fade'])} at={data['atText']} stale={data['stale']}")
