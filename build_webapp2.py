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
  .val{ font-variant-numeric:tabular-nums; font-weight:700; font-size:16px; text-align:right; }
  .pos{ color:#34d399; } .neg{ color:#f87171; }
  .empty{ color:var(--muted); text-align:center; padding:30px 10px; }
  footer{ color:var(--muted); font-size:11px; text-align:center; padding:18px; }
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

  <ol id="results"></ol>
</main>
<footer id="foot"></footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const METRICS = {
  performance:  {label:"Performance (Rendite)", periods:["1m","3m","6m","1y","3y","5y"], higher:true,  pct:true},
  sharpe:       {label:"Sharpe Ratio",          periods:["1y","3y","5y"],                higher:true,  pct:false},
  sortino:      {label:"Sortino Ratio",         periods:["1y","3y","5y"],                higher:true,  pct:false},
  information:  {label:"Information Ratio",      periods:["1y","3y","5y"],                higher:true,  pct:false},
  treynor:      {label:"Treynor Ratio",         periods:["1y","3y","5y"],                higher:true,  pct:false},
  alpha:        {label:"Jensens Alpha",         periods:["1y","3y","5y"],                higher:true,  pct:true},
  volatility:   {label:"Volatilität",           periods:["1y","3y","5y"],                higher:false, pct:true},
  beta:         {label:"Beta",                  periods:["1y","3y","5y"],                higher:true,  pct:false},
  trackingerror:{label:"Tracking Error",        periods:["3y","5y"],                     higher:false, pct:true},
};
const PLABEL = {"1m":"1 Monat","3m":"3 Monate","6m":"6 Monate",
                "1y":"1 Jahr","3y":"3 Jahre","5y":"5 Jahre"};
const $ = id => document.getElementById(id);

function normCat(c){ return (c||"").replace(/^EAA Fund /, "").trim(); }
// Anbieter-Bucket exakt vergleichen (Union Investment / Quoniam / Sonstige Fonds / ETF)
function providerMatch(f,p){ return p==="all" || f.branding===p; }

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
  const list = PROV_ORDER.filter(p=>present.has(p));
  $("provider").innerHTML = `<option value="all">Alle</option>` +
      list.map(p=>`<option value="${p}">${p}</option>`).join("");
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
    .map(f=>({name:f.name, branding:f.branding, value:f.metrics[key]}));
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
  const ol = $("results");
  if (!shown.length){ ol.innerHTML = `<div class="empty">Keine Wertpapiere mit Werten für diese Auswahl.</div>`; return; }
  ol.innerHTML = shown.map((r,i)=>{
    const cls = badgeClass(r.branding);
    const vcls = r.value>=0 ? "pos":"neg";
    const txt = m.pct ? r.value.toFixed(2)+" %" : r.value.toFixed(3);
    return `<li><div class="rank">${i+1}</div>
      <div><div class="name">${r.name}</div>
      <span class="badge ${cls}">${r.branding}</span></div>
      <div class="val ${vcls}">${txt}</div></li>`;
  }).join("");
}

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
$("srcline").textContent = `Quelle: Morningstar · Stand: ${DATA.meta.as_of} · ${DATA.meta.fund_count} Wertpapiere`;
$("foot").textContent = "Treynor berechnet (Sharpe×StdAbw÷Beta). Bei Volatilität & Tracking Error gilt: niedriger = besser. Daten-Snapshot, nicht live.";
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
        "funds": [{"name": f["name"], "branding": f["branding"],
                   "category": f["category"], "metrics": f["metrics"]}
                  for f in data["funds"]],
    }
    payload = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("__DATA__", payload)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"{len(slim['funds'])} Wertpapiere eingebettet -> {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
