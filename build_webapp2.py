#!/usr/bin/env python3
"""Erzeugt die ZWEITE eigenständige Web-App "JoMe" (Fonds & ETFs) als
jome/index.html aus data/funds2.json. Gleiche Funktionen wie App 1, zusätzlich
ETF-Kategorie im Anbieterfilter (leere Buckets werden ausgeblendet). App 1 wird
NICHT verändert.

    python3 build_webapp2.py     # schreibt jome/index.html
"""
from __future__ import annotations
import json, os

DATA = "data/funds2.json"
OUT = "jome/index.html"

HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="theme-color" content="#1f4e79">
<title>JoMe</title>
<style>
  :root{ --bg:#0f1115; --card:#1a1e26; --fg:#f2f4f8; --muted:#9aa4b2;
         --union:#e3000f; --quoniam:#3b82f6; --etf:#10b981; --sonst:#6b7280;
         --line:#2a2f3a; --accent:#1f4e79; }
  *{ box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body{ margin:0; background:var(--bg); color:var(--fg);
        font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header{ position:sticky; top:0; background:linear-gradient(180deg,#11151c,#11151cee);
          backdrop-filter:blur(6px); padding:14px 16px 10px; border-bottom:1px solid var(--line); z-index:5; }
  h1{ font-size:18px; margin:0 0 2px; }
  .sub{ color:var(--muted); font-size:12px; }
  main{ padding:14px 16px 40px; max-width:760px; margin:0 auto; }
  .controls{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .controls .wide{ grid-column:1 / -1; }
  label{ display:block; font-size:12px; color:var(--muted); margin:0 0 4px 2px; }
  select{ width:100%; padding:12px; font-size:16px; color:var(--fg);
          background:var(--card); border:1px solid var(--line); border-radius:12px; appearance:none; }
  .meta{ display:flex; justify-content:space-between; align-items:center;
         margin:16px 2px 8px; gap:10px; }
  .count{ color:var(--muted); font-size:13px; }
  button{ background:var(--accent); color:#fff; border:0; border-radius:10px;
          padding:9px 12px; font-size:14px; font-weight:600; }
  button:disabled{ opacity:.4; }
  ol{ list-style:none; margin:0; padding:0; }
  li{ display:grid; grid-template-columns:34px 1fr auto; gap:10px; align-items:center;
      background:var(--card); border:1px solid var(--line); border-radius:12px;
      padding:10px 12px; margin-bottom:8px; }
  .rank{ font-weight:700; color:var(--muted); text-align:center; }
  .name{ font-size:14px; }
  .badge{ display:inline-block; font-size:11px; padding:1px 7px; border-radius:999px;
          margin-top:3px; color:#fff; }
  .b-union{ background:var(--union); } .b-quoniam{ background:var(--quoniam); }
  .b-etf{ background:var(--etf); } .b-sonstige{ background:var(--sonst); }
  .bench{ font-size:11px; color:var(--muted); margin-top:3px; line-height:1.3;
          overflow:hidden; text-overflow:ellipsis; display:-webkit-box;
          -webkit-line-clamp:1; -webkit-box-orient:vertical; }
  li.tap{ cursor:pointer; } li.tap:active{ background:#20252f; }
  .chev{ color:var(--muted); font-size:13px; }
  .val{ font-variant-numeric:tabular-nums; font-weight:700; font-size:16px; text-align:right; }
  .pos{ color:#34d399; } .neg{ color:#f87171; }
  .empty{ color:var(--muted); text-align:center; padding:30px 10px; }
  .hint{ color:var(--muted); font-size:11.5px; line-height:1.4; margin:2px 2px 10px;
         padding:8px 10px; background:#181c24; border:1px solid var(--line); border-radius:9px; }
  .hint:empty{ display:none; }
  .hint b{ color:var(--fg); font-weight:600; }
  footer{ color:var(--muted); font-size:11px; text-align:center; padding:18px; }
  /* Detail-Overlay */
  .overlay{ position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:20;
            display:flex; align-items:flex-end; justify-content:center; }
  .overlay[hidden]{ display:none; }
  .sheet{ background:var(--card); width:100%; max-width:760px; max-height:88vh;
          overflow-y:auto; border-radius:16px 16px 0 0; border:1px solid var(--line);
          padding:16px 16px 28px; -webkit-overflow-scrolling:touch; }
  @media(min-width:600px){ .overlay{ align-items:center; } .sheet{ border-radius:16px; } }
  .sheet h2{ font-size:17px; margin:2px 0 2px; padding-right:34px; }
  .sheet .isin{ color:var(--muted); font-size:12px; font-variant-numeric:tabular-nums; }
  .x{ position:absolute; top:12px; right:14px; background:#2a2f3a; color:#fff;
      width:30px; height:30px; border-radius:999px; border:0; font-size:16px; }
  .shead{ position:relative; }
  .stars{ color:#f5c518; letter-spacing:2px; font-size:15px; }
  .stars .off{ color:#3a3f4a; }
  .medal{ display:inline-block; font-size:11px; padding:1px 8px; border-radius:999px;
          background:#3a3f4a; color:#fff; }
  .kv{ display:grid; grid-template-columns:auto 1fr; gap:4px 12px; margin:12px 0;
       font-size:13px; }
  .kv dt{ color:var(--muted); } .kv dd{ margin:0; text-align:right; font-variant-numeric:tabular-nums; }
  .kv dd.l{ text-align:left; }
  .mt{ margin-top:14px; }
  .mt h3{ font-size:13px; color:var(--muted); margin:0 0 6px; text-transform:uppercase; letter-spacing:.04em; }
  .mrow{ display:grid; grid-template-columns:118px 1fr; gap:8px; padding:6px 0;
         border-top:1px solid var(--line); font-size:13px; align-items:baseline; }
  .mrow .ml{ color:var(--muted); }
  .chips{ display:flex; flex-wrap:wrap; gap:4px 10px; }
  .chip{ font-variant-numeric:tabular-nums; }
  .chip b{ color:var(--muted); font-weight:600; font-size:11px; margin-right:3px; }
  /* Factsheet */
  .sec{ margin-top:16px; }
  .sec h3{ font-size:12px; color:var(--muted); margin:0 0 8px; text-transform:uppercase; letter-spacing:.05em; }
  .alloc{ display:flex; height:16px; border-radius:6px; overflow:hidden; border:1px solid var(--line); }
  .alloc span{ display:block; height:100%; }
  .alloc .aeq{ background:#6366f1; } .alloc .abd{ background:#10b981; }
  .alloc .aca{ background:#f59e0b; } .alloc .aot{ background:#6b7280; }
  .alegend{ display:flex; flex-wrap:wrap; gap:6px 14px; margin-top:7px; font-size:12px; color:var(--muted); }
  .alegend i{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:5px; vertical-align:baseline; }
  .brow{ display:grid; grid-template-columns:96px 1fr 46px; gap:8px; align-items:center;
         font-size:12.5px; margin:5px 0; }
  .brow .bl{ color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .track{ background:#252b36; border-radius:5px; height:9px; overflow:hidden; }
  .track i{ display:block; height:100%; background:var(--quoniam); border-radius:5px; }
  .brow .bv{ text-align:right; font-variant-numeric:tabular-nums; }
  .sbox{ display:inline-grid; grid-template-columns:repeat(3,26px); grid-auto-rows:26px; gap:3px; }
  .sbox div{ background:#252b36; border-radius:4px; }
  .sbox div.on{ background:var(--quoniam); box-shadow:0 0 0 2px rgba(59,130,246,.35); }
  .sbaxis{ display:flex; gap:14px; margin-top:8px; font-size:11px; color:var(--muted); flex-wrap:wrap; }
  .fikpi{ display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin-top:10px; }
  .fikpi .k{ background:#20252f; border:1px solid var(--line); border-radius:10px; padding:8px 10px; }
  .fikpi .k .kl{ font-size:11px; color:var(--muted); } .fikpi .k .kn{ font-size:16px; font-weight:700; }
  .grid2{ display:grid; grid-template-columns:1fr 1fr; gap:6px 18px; }
  @media(max-width:520px){ .grid2{ grid-template-columns:1fr; } }
  .catline{ font-size:12px; color:var(--muted); margin-top:3px; }
</style>
</head>
<body>
<header>
  <h1>JoMe</h1>
  <div class="sub" id="srcline"></div>
</header>
<main>
  <div class="controls">
    <div>
      <label for="metric">Kennzahl</label>
      <select id="metric"></select>
    </div>
    <div>
      <label for="period">Laufzeit</label>
      <select id="period"></select>
    </div>
    <div>
      <label for="provider">Anbieter</label>
      <select id="provider"></select>
    </div>
    <div>
      <label for="topn">Anzahl</label>
      <select id="topn">
        <option value="0">Alle</option>
        <option value="10">Top 10</option>
        <option value="25">Top 25</option>
        <option value="50">Top 50</option>
        <option value="-10">Flop 10</option>
        <option value="-25">Flop 25</option>
        <option value="-50">Flop 50</option>
      </select>
    </div>
    <div class="wide">
      <label for="assetclass">Anlageklasse (grobes Raster)</label>
      <select id="assetclass"></select>
    </div>
    <div class="wide">
      <label for="category">Morningstar-Kategorie (fein)</label>
      <select id="category"></select>
    </div>
  </div>

  <div class="meta">
    <span class="count" id="count"></span>
    <button id="csv">CSV teilen / speichern</button>
  </div>
  <div class="hint" id="hint"></div>

  <ol id="results"></ol>
</main>

<div id="ov" class="overlay" hidden>
  <div class="sheet">
    <div class="shead">
      <button class="x" id="ovclose" aria-label="Schliessen">×</button>
      <div id="ovbody"></div>
    </div>
  </div>
</div>

<footer id="foot"></footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const METRICS = {
  performance:  {label:"Performance (Rendite)", periods:["1m","3m","6m","1y","3y","5y","10y","incep"], higher:true,  pct:true},
  alphacat:     {label:"Alpha (ggü. Kategorie-Index)", periods:["1y","3y","5y","10y"],   higher:true,  pct:true},
  alpha:        {label:"Jensens Alpha (Std.-Index)", periods:["1y","3y","5y","10y"],     higher:true,  pct:true},
  sharpe:       {label:"Sharpe Ratio",          periods:["1y","3y","5y","10y"],          higher:true,  pct:false},
  sortino:      {label:"Sortino Ratio",         periods:["1y","3y","5y","10y"],          higher:true,  pct:false},
  information:  {label:"Information Ratio",      periods:["1y","3y","5y","10y"],          higher:true,  pct:false},
  treynor:      {label:"Treynor Ratio",         periods:["1y","3y","5y","10y"],          higher:true,  pct:false},
  volatility:   {label:"Volatilität",           periods:["1y","3y","5y","10y"],          higher:false, pct:true},
  beta:         {label:"Beta",                  periods:["1y","3y","5y","10y"],          higher:true,  pct:false},
  trackingerror:{label:"Tracking Error",        periods:["3y","5y","10y"],               higher:false, pct:true},
};
const PLABEL = {"1m":"1 Monat","3m":"3 Monate","6m":"6 Monate",
                "1y":"1 Jahr","3y":"3 Jahre","5y":"5 Jahre","10y":"10 Jahre","incep":"seit Auflage"};
const $ = id => document.getElementById(id);
let SHOWN = [];

function normCat(c){ return (c||"").replace(/^EAA Fund /, "").trim(); }
// Anbieter-Bucket vergleichen; "uq" = Union + Quoniam zusammengefasst.
function providerMatch(f,p){
  if (p==="all") return true;
  if (p==="uq") return f.branding==="Union Investment" || f.branding==="Quoniam";
  return f.branding===p;
}

function assetClass(catRaw){
  const c = normCat(catRaw).toLowerCase();
  if (c.includes("money market") || c.includes("ultra short")) return "Geldmarkt";
  if (c.includes("property")) return "Immobilien";
  if (c.includes("commodit")) return "Rohstoffe";
  if (c.includes("convertible")) return "Wandelanleihen";
  if (c.includes("allocation") || c.includes("target date") || c.includes("capital protected")
      || c.includes("guaranteed")) return "Mischfonds";
  if (c.includes("equity") || c.includes("equities")) return "Aktienfonds";
  if (c.includes("bond") || c.includes("fixed term") || c.includes("credit")
      || c.includes("renten") || c.includes("gilt")) return "Anleihen";
  if (c.includes("market neutral") || c.includes("systematic trend")
      || c.includes("infrastructure direct")) return "Alternative";
  return "Sonstige";
}
const ASSET_ORDER = ["Aktienfonds","Anleihen","Mischfonds","Immobilien","Rohstoffe",
                     "Wandelanleihen","Geldmarkt","Alternative","Sonstige"];

// Anbieter-Dropdown: nur Buckets zeigen, die tatsächlich Wertpapiere enthalten
// (leere Kategorien wie "Sonstige Fonds" werden ausgeblendet).
const PROV_ORDER = ["Union Investment","Quoniam","Sonstige Fonds","ETF"];
function fillProviders(){
  const present = new Set(DATA.funds.map(f=>f.branding));
  let opts = `<option value="all">Alle</option>`;
  if (present.has("Union Investment") && present.has("Quoniam"))
    opts += `<option value="uq">Union + Quoniam</option>`;
  opts += PROV_ORDER.filter(p=>present.has(p))
      .map(p=>`<option value="${p}">${p}</option>`).join("");
  $("provider").innerHTML = opts;
}
function fillMetrics(){
  $("metric").innerHTML = Object.entries(METRICS)
    .map(([k,m])=>`<option value="${k}">${m.label}</option>`).join("");
}
function fillPeriods(){
  const m = METRICS[$("metric").value];
  const cur = $("period").value;
  $("period").innerHTML = m.periods
    .map(p=>`<option value="${p}">${PLABEL[p]}</option>`).join("");
  if (m.periods.includes(cur)) $("period").value = cur;
}
function fillAssetClasses(){
  const prov = $("provider").value;
  const present = new Set(DATA.funds.filter(f=>providerMatch(f,prov))
      .map(f=>assetClass(f.category)));
  const list = ASSET_ORDER.filter(a=>present.has(a));
  const cur = $("assetclass").value;
  $("assetclass").innerHTML = `<option value="">Alle Anlageklassen</option>` +
      list.map(a=>`<option value="${a}">${a}</option>`).join("");
  if (cur && list.includes(cur)) $("assetclass").value = cur;
}
function fillCategories(){
  const prov = $("provider").value, ac = $("assetclass").value;
  const cats = [...new Set(DATA.funds.filter(f=>providerMatch(f,prov))
      .filter(f=> !ac || assetClass(f.category)===ac)
      .map(f=>normCat(f.category)))].sort();
  const cur = $("category").value;
  $("category").innerHTML = `<option value="">Alle Kategorien</option>` +
      cats.map(c=>`<option value="${c}">${c}</option>`).join("");
  if (cur && cats.includes(cur)) $("category").value = cur; else $("category").value = "";
}

function currentRows(){
  const metric=$("metric").value, period=$("period").value,
        prov=$("provider").value, ac=$("assetclass").value, cat=$("category").value;
  const key = metric+"_"+period;
  let rows = DATA.funds.filter(f=>providerMatch(f,prov))
    .filter(f=> !ac || assetClass(f.category)===ac)
    .filter(f=> !cat || normCat(f.category)===cat)
    .filter(f=> f.metrics && f.metrics[key]!=null)
    .map(f=>({fund:f, name:f.name, branding:f.branding, value:f.metrics[key]}));
  const higher = METRICS[metric].higher;
  rows.sort((a,b)=> higher ? b.value-a.value : a.value-b.value);
  return rows;
}

function selectRows(rows, topn){
  if (topn > 0) return {list: rows.slice(0, topn), flop:false};
  if (topn < 0){ const n = Math.min(-topn, rows.length);
    return {list: rows.slice(rows.length - n).reverse(), flop:true}; }
  return {list: rows, flop:false};
}

function badgeClass(b){
  if (b==="ETF") return "b-etf";
  if (b==="Quoniam") return "b-quoniam";
  if (b==="Union Investment") return "b-union";
  return "b-sonstige";
}

function render(){
  fillPeriods(); fillAssetClasses(); fillCategories();
  const rows = currentRows();
  const topn = parseInt($("topn").value,10);
  const {list:shown} = selectRows(rows, topn);
  const m = METRICS[$("metric").value];
  const tag = topn>0 ? `Top ${topn}` : topn<0 ? `Flop ${-topn}` : "alle";
  $("count").textContent =
    `${tag}: ${shown.length} von ${rows.length} Wertpapieren · ${m.label} (${PLABEL[$("period").value]})`;
  const hk = $("metric").value;
  $("hint").innerHTML =
    hk==="alphacat" ? `<b>Alpha ggü. Kategorie-Index:</b> Mehrrendite p.a. gegenüber dem <b>Morningstar-Kategorie-Index</b> – für alle Fonds einer Kategorie identisch, daher fair vergleichbar. (Rendite abzüglich Index-Rendite; Index-Währung ggf. abweichend.)` :
    hk==="alpha" ? `<b>Jensens Alpha</b> von Morningstar wird gegen den <b>Standard-Index</b> gerechnet (je Fonds unterschiedlich) – nur eingeschränkt zwischen ähnlichen Fonds vergleichbar. Für den fairen Vergleich „Alpha (ggü. Kategorie-Index)" wählen.` : "";
  const ol = $("results");
  SHOWN = shown;
  if (!shown.length){ ol.innerHTML = `<div class="empty">Keine Wertpapiere mit Werten für diese Auswahl.</div>`; return; }
  const mkey = $("metric").value;
  const showCat = (mkey==="alphacat");
  ol.innerHTML = shown.map((r,i)=>{
    const cls = badgeClass(r.branding);
    const vcls = r.value>=0 ? "pos":"neg";
    const txt = m.pct ? r.value.toFixed(2)+" %" : r.value.toFixed(3);
    const btxt = showCat ? (r.fund.benchcat||r.fund.bench) : r.fund.bench;
    const blbl = showCat ? "Kategorie-Index" : "Benchmark";
    const bench = btxt ? `<div class="bench">${blbl}: ${esc(btxt)}</div>` : "";
    return `<li class="tap" data-i="${i}"><div class="rank">${i+1}</div>
      <div><div class="name">${esc(r.name)} <span class="chev">›</span></div>
      <span class="badge ${cls}">${r.branding}</span>${bench}</div>
      <div class="val ${vcls}">${txt}</div></li>`;
  }).join("");
}

function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function fmtVal(v, pct){ return pct ? v.toFixed(2)+" %" : v.toFixed(3); }
function fmtAum(v){ if(v==null) return null;
  if(v>=1e9) return (v/1e9).toFixed(v>=1e10?0:1).replace(".",",")+" Mrd. USD";
  if(v>=1e6) return (v/1e6).toFixed(0)+" Mio. USD";
  return Math.round(v).toLocaleString("de-DE")+" USD"; }
function stars(r){ const n=parseInt(r,10); if(!n) return null;
  return `<span class="stars">${"★".repeat(n)}<span class="off">${"★".repeat(5-n)}</span></span> <span style="color:var(--muted)">(${n}/5)</span>`; }

const SB_SIZE = {large:"Groß",mid:"Mittel",small:"Klein"};
const SB_STYLE = {value:"Substanz",blend:"Misch",core:"Kern",growth:"Wachstum"};
const FI_CR = {high:"Hoch",medium:"Mittel",low:"Niedrig"};
const FI_RT = {limited:"Kurz",moderate:"Mittel",extensive:"Lang"};
const SEC_LBL = {ba:"Grundstoffe",co:"Kommunikation",cy:"Zykl. Konsum",df:"Def. Konsum",
  he:"Gesundheit",in:"Industrie",re:"Immobilien",te:"Technologie",en:"Energie",
  fi:"Finanzen",ut:"Versorger"};
const REG_LBL = {am:"Amerika",eu:"Europa",as:"Asien",em:"Schwellenländer"};
const CTR_LBL = {us:"USA",uk:"Großbritannien",jp:"Japan",de:"Deutschland",
  fr:"Frankreich",ch:"Schweiz",nl:"Niederlande",cn:"China"};

function bars(obj, labels, max){
  const items = Object.entries(obj).map(([k,v])=>[labels[k]||k, v]).sort((a,b)=>b[1]-a[1]);
  const top = max ? items.slice(0,max) : items;
  const hi = Math.max(...top.map(x=>x[1]), 1);
  return top.map(([l,v])=>`<div class="brow"><div class="bl">${esc(l)}</div>
    <div class="track"><i style="width:${Math.max(2,v/hi*100).toFixed(0)}%"></i></div>
    <div class="bv">${v.toFixed(1)} %</div></div>`).join("");
}
function sboxGrid(row,col){
  let cells="";
  for(let r=0;r<3;r++) for(let c=0;c<3;c++) cells+=`<div class="${r===row&&c===col?'on':''}"></div>`;
  return `<div class="sbox">${cells}</div>`;
}
function styleBoxEq(s){
  const t=(s||"").toLowerCase(), p=(s||"").split(" ");
  const row = t.includes("large")?0 : t.includes("mid")?1 : t.includes("small")?2 : -1;
  const col = t.includes("value")?0 : t.includes("growth")?2 : (t.includes("blend")||t.includes("core"))?1 : -1;
  return sboxGrid(row,col)+`<div class="sbaxis">
    <span>Größe: ${esc(SB_SIZE[(p[0]||"").toLowerCase()]||p[0]||"–")}</span>
    <span>Stil: ${esc(SB_STYLE[(p[1]||"").toLowerCase()]||p[1]||"–")}</span></div>`;
}
function styleBoxFi(s){
  const p=(s||"").split(" "), cr=(p[0]||"").toLowerCase(), rt=(p[1]||"").toLowerCase();
  const row = cr==="high"?0 : cr==="medium"?1 : cr==="low"?2 : -1;
  const col = rt==="limited"?0 : rt==="moderate"?1 : rt==="extensive"?2 : -1;
  return sboxGrid(row,col)+`<div class="sbaxis">
    <span>Bonität: ${esc(FI_CR[cr]||"–")}</span>
    <span>Zinssensitivität: ${esc(FI_RT[rt]||"–")}</span></div>`;
}
function fmtMc(m){
  if(m>=1e6) return (m/1e6).toFixed(1).replace(".",",")+" Bio. USD";
  if(m>=1e3) return (m/1e3).toFixed(1).replace(".",",")+" Mrd. USD";
  return Math.round(m).toLocaleString("de-DE")+" Mio. USD";
}
function kpiBox(list){
  return `<div class="fikpi">${list.map(([l,v])=>
    `<div class="k"><div class="kl">${l}</div><div class="kn">${v}</div></div>`).join("")}</div>`;
}
function compHTML(c){
  let h="";
  const eq=c.eq||0, bd=c.bd||0, ca=c.ca||0, ot=Math.max(0,+(100-eq-bd-ca).toFixed(1));
  if(eq+bd+ca>0){
    const seg=(v,cl)=> v>0?`<span class="${cl}" style="width:${v}%"></span>`:"";
    const leg=(v,col,l)=> v>0?`<span><i style="background:${col}"></i>${l} ${v.toFixed(1)} %</span>`:"";
    h+=`<div class="sec"><h3>Anlagemix</h3>
      <div class="alloc">${seg(eq,'aeq')}${seg(bd,'abd')}${seg(ca,'aca')}${seg(ot,'aot')}</div>
      <div class="alegend">${leg(eq,'#6366f1','Aktien')}${leg(bd,'#10b981','Anleihen')}${leg(ca,'#f59e0b','Kasse')}${leg(ot,'#6b7280','Sonstiges')}</div></div>`;
  }
  if(c.kind==="equity" || c.sEq || c.sec){
    if(c.sEq) h+=`<div class="sec"><h3>Morningstar Style-Box · Aktien</h3>${styleBoxEq(c.sEq)}</div>`;
    if(c.sec) h+=`<div class="sec"><h3>Sektoren</h3>${bars(c.sec,SEC_LBL,0)}</div>`;
    if(c.reg){
      const reg=Object.assign({},c.reg), em=reg.em; delete reg.em;
      h+=`<div class="sec"><h3>Regionen</h3>${bars(reg,REG_LBL,0)}
        ${em!=null?`<div class="catline">davon Schwellenländer: ${em.toFixed(1)} %</div>`:""}</div>`;
    }
    if(c.ctr) h+=`<div class="sec"><h3>Top-Länder (Aktien)</h3>${bars(c.ctr,CTR_LBL,6)}</div>`;
  }
  if(c.kind==="bond" || c.sFi || c.cr){
    if(c.sFi) h+=`<div class="sec"><h3>Morningstar Style-Box · Renten</h3>${styleBoxFi(c.sFi)}</div>`;
    const k=[];
    if(c.cr) k.push(["Ø Bonität (Rating)", esc(c.cr)]);
    if(c.du!=null) k.push(["Ø Duration", c.du.toFixed(2).replace(".",",")+" J"]);
    if(c.nb!=null) k.push(["Anzahl Anleihen", c.nb.toLocaleString("de-DE")]);
    if(c.t10!=null) k.push(["Top-10-Anteil", c.t10.toFixed(1).replace(".",",")+" %"]);
    if(k.length) h+=`<div class="sec"><h3>Renten-Kennzahlen</h3>${kpiBox(k)}</div>`;
  }
  const st=[];
  if(c.nh!=null) st.push(["Positionen gesamt", c.nh.toLocaleString("de-DE")]);
  if(c.mc!=null) st.push(["Ø Marktkap.", fmtMc(c.mc)]);
  if(c.kind!=="bond" && c.t10!=null) st.push(["Top-10-Anteil", c.t10.toFixed(1).replace(".",",")+" %"]);
  if(st.length) h+=`<div class="sec"><h3>Portfolio-Statistik</h3>${kpiBox(st)}</div>`;
  return h;
}

function openDetail(f){
  const c=f.comp;
  const kindLbl = c ? ({equity:"Aktienfonds",bond:"Rentenfonds",other:"Multi-Asset / Sonstige"}[c.kind]||"") : "";
  let head=`<h2>${esc(f.name)}</h2>
    <div class="isin"><span class="badge ${badgeClass(f.branding)}">${f.branding}</span>${f.rating?" "+stars(f.rating):""}${f.medalist?` <span class="medal">${esc(f.medalist)}</span>`:""}</div>
    <div class="catline">${esc(normCat(f.category))}${kindLbl?" · "+kindLbl:""}</div>`;

  let body = c ? compHTML(c)
    : `<div class="catline" style="margin-top:14px">Für dieses Wertpapier liegen keine Portfolio-Detaildaten vor (z. B. physisches Gold / ETC).</div>`;

  const pm=METRICS.performance;
  const pchips=pm.periods.filter(p=>f.metrics["performance_"+p]!=null)
    .map(p=>`<span class="chip"><b>${PLABEL[p]}</b>${fmtVal(f.metrics["performance_"+p],true)}</span>`).join("");
  if(pchips) body+=`<div class="sec"><h3>Performance (annualisiert p.a.)</h3><div class="chips">${pchips}</div></div>`;

  // Alpha sachgerecht: Mehrrendite ggü. Kategorie-Index (vergleichbar) + Jensen (Std.-Index)
  const per=["1y","3y","5y","10y"];
  const chipsFor=pre=>per.filter(p=>f.metrics[pre+p]!=null)
    .map(p=>`<span class="chip"><b>${PLABEL[p]}</b>${fmtVal(f.metrics[pre+p],true)}</span>`).join("");
  const acC=chipsFor("alphacat_"), ajC=chipsFor("alpha_");
  if(acC||ajC){
    let a=`<div class="sec"><h3>Alpha · Mehrrendite</h3>`;
    if(acC) a+=`<div class="mrow"><div class="ml">ggü. Kategorie-Index${f.benchcat?`<br><span style="font-size:10px;opacity:.8">${esc(f.benchcat)}</span>`:""}</div><div class="chips">${acC}</div></div>`;
    if(ajC) a+=`<div class="mrow"><div class="ml">Jensen<br><span style="font-size:10px;opacity:.8">Morningstar-Standardindex</span></div><div class="chips">${ajC}</div></div>`;
    body+=a+`</div>`;
  }

  const kv=(k,v,left)=> v!=null&&v!=="" ? `<dt>${k}</dt><dd class="${left?'l':''}">${v}</dd>` : "";
  let facts="";
  facts+=kv("Benchmark", f.bench?esc(f.bench):"", true);
  if(f.benchcat && f.benchcat!==f.bench) facts+=kv("Kategorie-Index", esc(f.benchcat), true);
  facts+=kv("Laufende Kosten", f.ter!=null?f.ter.toFixed(2).replace(".",",")+" % p.a.":"");
  facts+=kv("Ausschüttungsrendite", f.yield!=null?f.yield.toFixed(2).replace(".",",")+" %":"");
  facts+=kv("Fondsvolumen", fmtAum(f.aum));
  facts+=kv("Währung", esc(f.ccy));
  facts+=kv("Auflage", esc(f.incepdate));
  facts+=kv("ISIN", esc(f.isin));
  if(facts) body+=`<div class="sec"><h3>Stammdaten</h3><dl class="kv">${facts}</dl></div>`;

  $("ovbody").innerHTML=head+body;
  $("ov").hidden=false;
}
function closeDetail(){ $("ov").hidden = true; }

function exportCSV(){
  const rows = currentRows();
  const topn = parseInt($("topn").value,10);
  const {list:shown} = selectRows(rows, topn);
  const m = METRICS[$("metric").value];
  const col = `${m.label} ${PLABEL[$("period").value]}`;
  const lines = [["Rang","Wertpapier","Anbieter",col].join(";")]
    .concat(shown.map((r,i)=>[i+1, '"'+r.name.replace(/"/g,'""')+'"', r.branding,
            String(r.value).replace('.',',')].join(";")));
  const blob = new Blob(["﻿"+lines.join("\r\n")], {type:"text/csv"});
  const fname = `app2_${$("metric").value}_${$("period").value}.csv`;
  const file = new File([blob], fname, {type:"text/csv"});
  if (navigator.canShare && navigator.canShare({files:[file]})){
    navigator.share({files:[file], title:col}).catch(()=>{});
  } else {
    const a=document.createElement("a"); a.href=URL.createObjectURL(blob);
    a.download=fname; a.click();
  }
}

["metric","period","provider","assetclass","category","topn"].forEach(id=>$(id).addEventListener("change",render));
$("csv").addEventListener("click", exportCSV);
$("results").addEventListener("click", e=>{
  const li = e.target.closest("li.tap"); if(!li) return;
  const r = SHOWN[parseInt(li.dataset.i,10)]; if(r && r.fund) openDetail(r.fund);
});
$("ovclose").addEventListener("click", closeDetail);
$("ov").addEventListener("click", e=>{ if(e.target===$("ov")) closeDetail(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape") closeDetail(); });
$("srcline").textContent = `Quelle: Morningstar · Stand: ${DATA.meta.as_of} · ${DATA.meta.fund_count} Wertpapiere`;
$("foot").textContent = "Alpha (ggue. Kategorie-Index) = Mehrrendite p.a. gegenueber dem fuer alle Fonds einer Kategorie identischen Morningstar-Kategorie-Index und damit fair vergleichbar (Fondsrendite minus Index-Rendite; Index-Waehrung ggf. abweichend). Jensens Alpha nutzt dagegen den Morningstar-Standardindex (je Fonds verschieden, nur eingeschraenkt vergleichbar). Performance 3/5/10 J und seit Auflage annualisiert (p.a.). Treynor berechnet (Sharpe x StdAbw / Beta). Volatilitaet & Tracking Error: niedriger = besser. Daten-Snapshot, nicht live.";
fillProviders(); fillMetrics(); render();
</script>
</body>
</html>
"""


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    slim = {
        "meta": {"as_of": data["meta"].get("as_of"),
                 "fund_count": data["meta"].get("fund_count")},
        "funds": [{k: f[k] for k in
                   ("name", "branding", "isin", "category", "metrics",
                    "bench", "benchcat", "rating", "medalist", "ter",
                    "aum", "ccy", "incepdate", "yield", "comp") if k in f}
                  for f in data["funds"]],
    }
    payload = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("__DATA__", payload)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"{len(slim['funds'])} Wertpapiere eingebettet -> {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
