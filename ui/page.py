"""The dashboard screen: Helm's agent compiling policies and paying creators worldwide.

One self-contained HTML string, no build step. Reads embedded `window.HELM_DATA`
(static build) or fetches `/api/data`. A world choropleth, a policy switcher that
shows the agent compiling each written policy into weights and hard constraints,
KPI cards, and per-country rollups. Chart.js and jsVectorMap from CDNs, both
guarded so the page still renders if a CDN is unavailable.
"""
from __future__ import annotations

import os

import json

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
_WORLD_SVG = ""
try:
    with open(os.path.join(os.path.dirname(__file__), "world_map.svg"), encoding="utf-8") as _f:
        _WORLD_SVG = _f.read()
except Exception:
    _WORLD_SVG = "<div style='color:#8b9bb0;padding:40px;text-align:center'>world map unavailable</div>"

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helm: autonomous money layer on PayPal</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27%3E%3Ccircle cx=%2712%27 cy=%2712%27 r=%279%27 fill=%27none%27 stroke=%27%235b9dff%27 stroke-width=%272%27/%3E%3Ccircle cx=%2712%27 cy=%2712%27 r=%273%27 fill=%27%235b9dff%27/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<script src="__CHART_JS__"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/ag-grid/35.3.0/ag-grid-community.min.js"></script>
<style>
  :root {
    --bg:#0a0e14; --panel:#121824; --line:rgba(255,255,255,.07); --ink:#eef3fa; --muted:#8b9bb0;
    --accent:#5b9dff; --good:#3ddc97; --warn:#f6c454; --bad:#ff6b6b; --target:#9aa7b5;
    --shadow:0 12px 32px rgba(0,0,0,.32); --radius:16px;
  }
  * { box-sizing:border-box; }
  body { margin:0; color:var(--ink); font-family:'Inter',-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    font-size:15px; line-height:1.55; letter-spacing:-.1px; -webkit-font-smoothing:antialiased;
    background:radial-gradient(900px 480px at 10% -8%, rgba(91,157,255,.14), transparent 55%),
               radial-gradient(760px 520px at 100% -2%, rgba(61,220,151,.06), transparent 52%), var(--bg); }
  header { padding:34px 22px 8px; max-width:1180px; margin:0 auto; }
  .brand { display:flex; align-items:center; gap:12px; }
  .brand svg { flex:0 0 auto; }
  h1 { margin:0; font-size:27px; font-weight:800; letter-spacing:-.7px; }
  .badge { color:var(--accent); font-size:11px; font-weight:700; letter-spacing:.9px;
    border:1px solid rgba(91,157,255,.3); background:rgba(91,157,255,.1); border-radius:999px; padding:4px 12px; }
  .sub { color:var(--muted); font-size:14px; margin-top:9px; max-width:880px; line-height:1.6; }
  main { max-width:1180px; margin:0 auto; padding:18px 22px 44px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(178px,1fr)); gap:14px; margin-bottom:18px; }
  .card { background:linear-gradient(165deg,rgba(255,255,255,.04),rgba(255,255,255,0)), var(--panel);
    border:1px solid var(--line); border-radius:var(--radius); padding:18px 20px; box-shadow:var(--shadow); }
  .card .k { color:var(--muted); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.8px; }
  .card .v { font-size:27px; font-weight:800; letter-spacing:-.9px; margin-top:7px; }
  .card .v.accent{color:var(--accent);} .card .v.good{color:var(--good);}
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
    padding:20px 22px; margin-bottom:18px; box-shadow:var(--shadow); }
  .panel h2 { margin:0 0 4px; font-size:16px; font-weight:700; letter-spacing:-.3px; }
  .panel p { margin:0 0 15px; color:var(--muted); font-size:13px; line-height:1.55; }
  .grid2 { display:grid; grid-template-columns:1.25fr 1fr; gap:18px; } @media (max-width:900px){ .grid2{grid-template-columns:1fr;} }
  .grid3 { display:grid; grid-template-columns:1fr 1fr; gap:18px; } @media (max-width:820px){ .grid3{grid-template-columns:1fr;} }
  .tabs { display:flex; gap:9px; flex-wrap:wrap; margin-bottom:14px; }
  .tab { background:rgba(255,255,255,.04); color:var(--muted); border:1px solid var(--line); border-radius:11px;
    padding:8px 15px; font-size:13px; font-weight:600; cursor:pointer; transition:all .15s ease; }
  .tab:hover { color:var(--ink); border-color:rgba(91,157,255,.4); }
  .tab.on { background:var(--accent); color:#06121f; border-color:var(--accent); box-shadow:0 6px 18px rgba(91,157,255,.32); }
  .lanes { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px; }
  .lane { flex:1; min-width:150px; text-align:center; background:rgba(255,255,255,.03); color:var(--muted);
    border:1px solid var(--line); border-radius:12px; padding:12px 16px; font-size:14px; font-weight:700; cursor:pointer; transition:all .15s; }
  .lane .sub { display:block; font-size:11px; font-weight:500; color:var(--muted); margin-top:2px; }
  .lane:hover { color:var(--ink); border-color:rgba(91,157,255,.4); }
  .lane.on { background:rgba(91,157,255,.14); color:var(--ink); border-color:var(--accent); }
  .lane.on .sub { color:var(--accent); }
  .policy { background:rgba(255,255,255,.03); border:1px solid var(--line); border-radius:12px; padding:15px 17px; margin-bottom:14px; }
  .policy .q { color:var(--ink); font-style:italic; font-size:15px; } .policy .c { color:var(--muted); font-size:13px; margin-top:7px; }
  .pill { display:inline-block; background:rgba(255,255,255,.04); border:1px solid var(--line); border-radius:9px;
    padding:4px 10px; margin:3px 5px 3px 0; font-size:12px; color:var(--muted); }
  .pill b { color:var(--ink); font-weight:700; } .pill.bad b{ color:var(--bad);} .pill.good b{color:var(--good);}
  canvas { max-height:250px; max-width:100%; }
  html, body { overflow-x:hidden; }
  .worldmap svg { width:100%; height:auto; display:block; }
  .worldmap path { fill:rgba(255,255,255,.055); stroke:#0a0e14; stroke-width:.3; transition:fill .7s cubic-bezier(.4,0,.2,1); }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th,td { text-align:right; padding:9px 10px; border-bottom:1px solid rgba(255,255,255,.045); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:10.5px; text-transform:uppercase; letter-spacing:.6px; }
  tbody tr:hover { background:rgba(91,157,255,.06); }
  .foot { color:var(--muted); font-size:12px; padding:10px 22px 40px; max-width:1180px; margin:0 auto; line-height:1.6; }
  .live-tool { background:rgba(255,255,255,.03); border:1px solid var(--line); border-radius:12px; padding:16px 18px; }
  .live-tool label { display:block; color:var(--muted); font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.6px; margin:10px 0 5px; }
  .live-tool textarea, .live-tool input, .live-tool select { width:100%; background:var(--bg); border:1px solid var(--line);
    border-radius:9px; color:var(--ink); padding:9px 11px; font-size:13px; font-family:inherit; }
  .live-tool textarea { min-height:62px; resize:vertical; line-height:1.5; }
  .live-row { display:flex; gap:10px; flex-wrap:wrap; } .live-row > div { flex:1; min-width:120px; }
  .btn { background:var(--accent); color:#06121f; border:none; border-radius:10px; padding:9px 17px; font-size:13px;
    font-weight:700; cursor:pointer; margin-top:12px; margin-right:8px; transition:filter .15s; }
  .btn:hover { filter:brightness(1.08); } .btn:disabled { opacity:.45; cursor:default; }
  .btn.ghost { background:rgba(255,255,255,.06); color:var(--ink); border:1px solid var(--line); }
  .result { margin-top:14px; min-height:18px; }
  .result .muted { color:var(--muted); font-size:12.5px; } .result .err { color:var(--bad); font-size:12.5px; }
  .kv { font-size:13px; margin:4px 0; color:var(--muted); } .kv b { color:var(--ink); font-weight:700; }
  .chk { display:flex; align-items:center; gap:8px; margin-top:12px; color:var(--muted); font-size:12.5px; }
  .chk input { width:auto; }
  .verdict { display:inline-block; border-radius:8px; padding:3px 10px; font-size:12px; font-weight:700; margin:2px 6px 2px 0; }
  .verdict.ok { background:rgba(61,220,151,.14); color:var(--good); } .verdict.no { background:rgba(255,107,107,.14); color:var(--bad); }
  .verdict.hold { background:rgba(246,196,84,.14); color:var(--warn); }
  .tour { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; }
  .tour .go { background:rgba(255,255,255,.03); border:1px solid var(--line); border-radius:12px; padding:14px 16px;
    display:flex; flex-direction:column; gap:6px; }
  .tour .go b { font-size:14px; } .tour .go span { color:var(--muted); font-size:12.5px; line-height:1.5; flex:1; }
  .tour .go .btn { align-self:flex-start; margin-top:6px; }
  .tour .lane-tag { color:var(--accent); font-size:10.5px; font-weight:700; letter-spacing:.7px; text-transform:uppercase; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#5b9dff" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.4" fill="#5b9dff" stroke="none"/>
      <path d="M12 3v3.6M12 17.4V21M3 12h3.6M17.4 12H21M5.6 5.6l2.5 2.5M15.9 15.9l2.5 2.5M18.4 5.6l-2.5 2.5M8.1 15.9l-2.5 2.5"/>
    </svg>
    <h1>Helm</h1><span class="badge">AUTONOMOUS MONEY LAYER</span>
  </div>
  <div class="sub">An autonomous money layer for a creator marketplace, settled on PayPal. One account, three sides: creators <b>earn</b> and get paid, anyone can <b>spend</b> as a buyer through signed-mandate agents, and the <b>platform</b> runs the treasury and <b>proves it is safe</b>: a zero-knowledge proof that the safety fund covers every liability without revealing a balance, and a formal (Z3) proof that an agent can never outspend its signed budget. AI proposes the judgment; deterministic code and cryptography dispose the money and the limits. Everything below is live on the real PayPal sandbox.</div>
</header>
<main>
  <div class="panel" id="start">
    <h2>Start here: four things to try, each live in one click</h2>
    <p>Every button runs on the backend against the real PayPal sandbox and a live model. Nothing is a recording.</p>
    <div class="tour">
      <div class="go"><div class="lane-tag">Platform</div><b>Agents decide a payout</b><span>A risk analyst, a bull, a bear and a manager argue over who to pay this week. Code then moves only what the reserve allows.</span><button class="btn" data-go="2:operator">Run the agents</button></div>
      <div class="go"><div class="lane-tag">Spend</div><b>A buyer agent shops inside a signed budget</b><span>It finds a real product, screens listings for prompt injection, and settles through a PayPal hold that it cannot exceed.</span><button class="btn" data-go="1:buyer">Run the buyer</button></div>
      <div class="go"><div class="lane-tag">Platform</div><b>Prove the fund is solvent, revealing nothing</b><span>A zero-knowledge proof that the safety fund covers every liability. An insolvent fund cannot produce one.</span><button class="btn" data-go="2:reserves">Prove solvency</button></div>
      <div class="go"><div class="lane-tag">Platform</div><b>Prove an agent can never overspend</b><span>A Z3 proof that holds for every possible sequence of purchases, plus the counterexample when a guard is removed.</span><button class="btn" data-go="2:verify">Run the proof</button></div>
    </div>
  </div>
  <div class="panel" id="acct">
    <h2>Your account <button class="btn" id="acct-reset" style="float:right;font-size:12px">Start over</button></h2>
    <p>You are one creator in a live marketplace of 120 others. What the platform owes creators and your own earnings are computed from real sales in it, net of the 10% platform fee. One set of books behind every tool below. An advance leaves the safety fund, a purchase holds your earnings on PayPal until you confirm delivery, a payout reduces what the platform owes, and the solvency proof, the P&amp;L and the audit desk all read these same numbers.</p>
    <div class="result" id="acct-body"><span class="muted">loading...</span></div>
  </div>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>The creators <span id="dirCount" class="sub"></span></h2>
    <p>Thousands of individual creators across the world, the population the agent pays. Search the sample by name or country.</p>
    <input id="dirSearch" placeholder="search name or country..." style="width:100%;max-width:340px;background:var(--bg);border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:8px 10px;margin-bottom:10px;font-size:13px">
    <div id="directory" style="height:340px;width:100%"></div>
  </div>

  <div class="panel">
    <h2>Write a policy, the agent runs it</h2>
    <p>Each tab is a treasury policy stated in English. The agent compiled it with the live model; the allocation below obeys it.</p>
    <div class="tabs" id="tabs"></div>
    <div class="policy" id="policy"></div>
    <div id="pills"></div>
  </div>

  <div class="grid2">
    <div class="panel" style="margin:0"><h2>Payouts across the world</h2><p>Brighter means more paid under this policy. Watch it shift as the policy changes.</p><div id="worldmap" class="worldmap" role="img" aria-label="payouts by country">__WORLD_SVG__</div></div>
    <div class="panel" style="margin:0"><h2>Where the money goes</h2><p>Payout and creators paid per country, this policy.</p><div id="countries" style="height:340px;width:100%"></div></div>
  </div>

  <div class="panel">
    <h2>Creators can reinvest instead of cashing out</h2>
    <p>Opt-in: a creator keeps a payout in and owns a proportional unit of a pooled fund of real assets, which pulls them back to the platform. Priced on real market data as of <span id="rAsOf"></span>. Sandbox concept, no securities are actually bought.</p>
    <div class="grid2">
      <div><canvas id="navChart"></canvas></div>
      <div><div id="reinvestHead" style="margin-bottom:10px"></div><div style="overflow-x:auto"><table id="holdings"></table></div></div>
    </div>
  </div>

  <div class="grid3">
    <div class="panel"><h2>Risk exposure by policy</h2><p>Dollars of risk carried. The fraud policy pulls money off risky creators.</p><canvas id="riskChart"></canvas></div>
    <div class="panel"><h2>Payout engine: cheating earns nothing</h2><p>A Sybil creator's take collapses to the honest share under hardening.</p><canvas id="bulwarkChart"></canvas></div>
  </div>

  <div class="panel" id="opfeed" style="display:none">
    <h2>The operator agent's decisions, cycle by cycle</h2>
    <p>The autonomous operator reads each week, grounds itself in the financial principles, sizes a safe release under the reserve, then pays the steady creators and holds the risky ones. Driver: <b id="opDriver"></b>, settled on <b id="opRail"></b>.</p>
    <div style="overflow:auto;max-height:360px"><table id="opTable"></table></div>
  </div>

  <div class="panel" id="live">
    <h2>Run the engine live <span class="badge" style="margin-left:6px">LIVE</span></h2>
    <p>Nothing here is a recording. Every button calls the running backend. One person-account, three sides: <b>earn</b> as a seller, <b>spend</b> as a buyer, and the <b>platform</b> that runs the money and proves it is safe. Pick a side, then a capability.</p>
    <div class="lanes" id="liveLanes"></div>
    <div class="tabs" id="liveTabs"></div>
    <div id="liveBody"></div>
    <div id="liveOffline" class="result muted" style="display:none">Open this on the running app to use the live console (static preview cannot reach the backend).</div>
  </div>
</main>
<div class="foot" id="foot"></div>

<script>
(async function(){
  const data = window.HELM_DATA || await (await fetch('/api/data')).json();
  const css = getComputedStyle(document.documentElement);
  const C = n => css.getPropertyValue(n).trim();
  const money = v => '$' + Number(v).toLocaleString(undefined,{maximumFractionDigits:0});
  const FAINT='rgba(255,255,255,.055)';
  if (window.Chart){
    Chart.defaults.color=C('--muted');
    Chart.defaults.borderColor=FAINT;
    Chart.defaults.font.family=getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size=12;
    Chart.defaults.elements.bar.borderRadius=7;
    Chart.defaults.elements.bar.borderSkipped=false;
    Chart.defaults.elements.line.tension=0.4;
    Chart.defaults.elements.line.borderWidth=2.5;
    Chart.defaults.elements.point.radius=0;
    Chart.defaults.elements.point.hoverRadius=4;
    Chart.defaults.plugins.legend.labels.boxWidth=9;
    Chart.defaults.plugins.legend.labels.usePointStyle=true;
    Chart.defaults.plugins.legend.labels.pointStyle='circle';
    Object.assign(Chart.defaults.plugins.tooltip, {backgroundColor:'#0e1724', borderColor:'rgba(255,255,255,.1)',
      borderWidth:1, cornerRadius:9, padding:11, titleColor:'#eef3fa', displayColors:false});
  }
  // modern scales: faint value grid, no category grid, no axis borders
  const SV = {x:{grid:{display:false},border:{display:false}}, y:{grid:{color:FAINT},border:{display:false},ticks:{maxTicksLimit:6}}};
  const SH = {x:{grid:{color:FAINT},border:{display:false},ticks:{callback:v=>'$'+Math.round(v/1000)+'k'}}, y:{grid:{display:false},border:{display:false}}};

  const h=data.headline, S=data.scenarios, ctx=data.context;
  const countUp=(el,target,fmt,dur=1000)=>{ const t0=performance.now();
    (function f(now){ const t=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-t,3);
      el.textContent=fmt(target*e); if(t<1) requestAnimationFrame(f); })(t0); };
  const defs=[
    ['creators', h.creators, v=>Math.round(v).toLocaleString(), ''],
    ['owed to creators', h.total_owed, money, 'accent'],
    ['this cycle budget', h.budget, money, ''],
    ['countries', h.countries, v=>String(Math.round(v)), ''],
    ['policies the agent ran', S.length, v=>String(Math.round(v)), 'good'],
  ];
  document.getElementById('cards').innerHTML = defs.map(c=>`<div class="card"><div class="k">${c[0]}</div><div class="v ${c[3]||''}">0</div></div>`).join('');
  document.querySelectorAll('#cards .v').forEach((el,i)=>countUp(el, defs[i][1], defs[i][2]));

  // AG Grid powers the two data grids, themed to the dashboard (sortable, filterable).
  const gridTheme = agGrid.themeQuartz.withParams({
    backgroundColor:'#121824', foregroundColor:'#eef3fa',
    headerBackgroundColor:'#121824', headerTextColor:'#8b9bb0',
    borderColor:'rgba(255,255,255,.07)', rowHoverColor:'rgba(91,157,255,.08)',
    oddRowBackgroundColor:'rgba(255,255,255,.02)', accentColor:'#5b9dff',
    fontFamily:'inherit', fontSize:'13px', headerFontSize:'10.5px', wrapperBorderRadius:'12px',
  });
  const riskCell = p => { const r=p.value;
    const c = r>=0.6?'var(--bad)':(r>=0.3?'var(--warn)':'var(--good)');
    const t = r>=0.6?'high':(r>=0.3?'med':'low');
    return `<span style="color:${c};font-weight:600">${t}</span>`; };

  // per-country payouts grid, refreshed on every policy change
  let countriesGrid=null;
  const countryCols=[
    {headerName:'Country', field:'country', flex:1, filter:true, minWidth:110},
    {headerName:'Paid', field:'amount', flex:1, type:'rightAligned', sort:'desc', valueFormatter:p=>money(p.value)},
    {headerName:'Creators', field:'count', flex:1, type:'rightAligned'},
  ];
  function setCountries(byCountry){
    const el=document.getElementById('countries'); if(!el) return;
    const rows=Object.entries(byCountry).map(([k,v])=>({country:k, amount:v.amount, count:v.count}));
    if(!countriesGrid){ countriesGrid=agGrid.createGrid(el,{theme:gridTheme, columnDefs:countryCols,
      rowData:rows, defaultColDef:{sortable:true,resizable:true}, rowHeight:34, headerHeight:36}); }
    else { countriesGrid.setGridOption('rowData', rows); }
  }

  // creator directory grid, quick-filtered by the search box
  const dir=data.directory;
  if (dir){
    document.getElementById('dirCount').textContent =
      `(${Number(dir.total).toLocaleString()} total, ${Number(dir.reinvesting_count).toLocaleString()} reinvesting; showing ${dir.sample_size})`;
    const dirCols=[
      {headerName:'Creator', field:'display', flex:2, filter:true, minWidth:140},
      {headerName:'Country', field:'country', flex:1, filter:true, minWidth:100},
      {headerName:'Owed', field:'owed', flex:1, type:'rightAligned', valueFormatter:p=>money(p.value)},
      {headerName:'Risk', field:'risk', flex:1, cellRenderer:riskCell},
      {headerName:'Paid this cycle', field:'paid', flex:1, type:'rightAligned',
        valueFormatter:p=>p.value>0?money(p.value):'-'},
      {headerName:'Reinvest stake', field:'stake', flex:1, type:'rightAligned',
        valueFormatter:p=>p.data.reinvesting?money(p.value):'-'},
    ];
    const dirGrid=agGrid.createGrid(document.getElementById('directory'),{
      theme:gridTheme, columnDefs:dirCols, rowData:dir.sample,
      defaultColDef:{sortable:true, resizable:true}, rowHeight:38, headerHeight:38,
    });
    document.getElementById('dirSearch').addEventListener('input',
      e=>dirGrid.setGridOption('quickFilterText', e.target.value));
  }

  // world choropleth: colour the inline SVG; CSS transitions animate it on policy change
  const mapEl=document.getElementById('worldmap');
  const mix=(a,b,t)=>{ const h=x=>[parseInt(x.slice(0,2),16),parseInt(x.slice(2,4),16),parseInt(x.slice(4,6),16)];
    const A=h(a),B=h(b); return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join(''); };
  const setMap = byCountry => {
    if(!mapEl) return;
    const mx=Math.max(1,...Object.values(byCountry).map(v=>v.amount));
    mapEl.querySelectorAll('path').forEach(p=>{ p.style.fill=''; });
    Object.entries(byCountry).forEach(([code,v])=>{
      const el=mapEl.querySelector('#'+code.toLowerCase());
      if(el) el.style.fill=mix('17304a','5b9dff', Math.sqrt(v.amount/mx));
    });
  };

  // scenario comparison: risk exposure per policy
  if (window.Chart){ new Chart(document.getElementById('riskChart'), { type:'bar',
    data:{ labels:S.map(s=>s.label), datasets:[{ data:S.map(s=>s.risk_exposure), maxBarThickness:54,
      backgroundColor:S.map(s=>s.label.toLowerCase().includes('fraud')?C('--good'):'rgba(154,167,181,.45)') }]},
    options:{ responsive:true, plugins:{legend:{display:false}}, scales:{...SV, y:{...SV.y, ticks:{maxTicksLimit:6, callback:v=>'$'+Math.round(v/1000)+'k'}}} }}); }
  const bw=data.payout_engine.bulwark;
  if (window.Chart){ new Chart(document.getElementById('bulwarkChart'), { type:'bar',
    data:{ labels:['naive take','hardened','honest share'], datasets:[{ data:[bw.naive_cheater_take,bw.hardened_cheater_take,bw.honest_share],
      maxBarThickness:70, backgroundColor:[C('--bad'),C('--good'),'rgba(154,167,181,.45)'] }]},
    options:{ responsive:true, plugins:{legend:{display:false}}, scales:SV }}); }

  // tabs
  const tabsEl=document.getElementById('tabs');
  tabsEl.innerHTML = S.map((s,i)=>`<div class="tab${i===0?' on':''}" data-i="${i}">${s.label}</div>`).join('');

  function show(i){
    const s=S[i];
    [...tabsEl.children].forEach((t,j)=>t.classList.toggle('on', j===i));
    const w=s.weights, con=s.constraints;
    document.getElementById('policy').innerHTML =
      `<div class="q">&ldquo;${s.policy}&rdquo;</div>`+
      `<div class="c">compiled by the model: ${s.reading||'(weights and constraints)'}</div>`;
    const exc = con.exclude_countries&&con.exclude_countries.length ? con.exclude_countries.join(', ') : 'none';
    document.getElementById('pills').innerHTML =
      `<span class="pill">speed <b>${w.speed}</b></span><span class="pill">tax <b>${w.tax}</b></span>`+
      `<span class="pill">risk <b>${w.risk}</b></span><span class="pill">fx <b>${w.fx}</b></span>`+
      `<span class="pill">cap/creator <b>${Math.round(con.max_fraction_per_creator*100)}%</b></span>`+
      `<span class="pill bad">exclude <b>${exc}</b></span>`+
      `<span class="pill good">paid <b>${s.paid_count.toLocaleString()}</b></span>`+
      `<span class="pill">net <b>${money(s.net_delivered)}</b></span>`+
      `<span class="pill">tax withheld <b>${money(s.tax_withheld)}</b></span>`+
      `<span class="pill">risk exposure <b>${Math.round(s.risk_exposure).toLocaleString()}</b></span>`;
    setMap(s.by_country);
    setCountries(s.by_country);
  }
  tabsEl.addEventListener('click', e=>{ const t=e.target.closest('.tab'); if(t) show(+t.dataset.i); });
  show(0);
  let i=0; setInterval(()=>{ i=(i+1)%S.length; show(i); }, 3500);   // auto-tour the policies

  // reinvestment pool (real-priced)
  const ri=data.reinvest;
  if (ri){
    const asof=document.getElementById('rAsOf'); if(asof) asof.textContent=ri.as_of;
    if (window.Chart){
      const nctx=document.getElementById('navChart').getContext('2d');
      const ng=nctx.createLinearGradient(0,0,0,250); ng.addColorStop(0,'rgba(91,157,255,.30)'); ng.addColorStop(1,'rgba(91,157,255,0)');
      new Chart(document.getElementById('navChart'), { type:'line',
      data:{ labels:ri.nav.dates, datasets:[{ label:'pool NAV (rebased to 100)', data:ri.nav.values,
        borderColor:C('--accent'), backgroundColor:ng, fill:true }]},
      options:{ responsive:true, animation:{duration:900}, plugins:{legend:{display:false}},
        scales:{ x:{grid:{display:false},border:{display:false},ticks:{maxTicksLimit:6}},
                 y:{grid:{color:FAINT},border:{display:false},ticks:{maxTicksLimit:5}} }}}); }
    const p=ri.pool;
    document.getElementById('reinvestHead').innerHTML =
      `<span class="pill good">reinvested <b>${money(p.total_contributed)}</b></span>`+
      `<span class="pill">now worth <b>${money(p.current_value)}</b></span>`+
      `<span class="pill ${p.return_pct>=0?'good':'bad'}">6mo return <b>${p.return_pct>=0?'+':''}${p.return_pct}%</b></span>`+
      `<span class="pill">${Number(p.reinvesting_creators).toLocaleString()} creators opted in</span>`;
    document.getElementById('holdings').innerHTML =
      '<thead><tr><th>Asset</th><th>Weight</th><th>6mo</th><th>Price</th></tr></thead><tbody>'+
      ri.holdings.map(h=>`<tr><td>${h.ticker} &middot; ${h.label}</td><td>${Math.round(h.weight*100)}%</td>`+
        `<td style="color:${h.return_pct>=0?'var(--good)':'var(--bad)'}">${h.return_pct>=0?'+':''}${h.return_pct}%</td>`+
        `<td>$${h.end_price}</td></tr>`).join('')+'</tbody>';
  }

  const pe=data.payout_engine, tg=pe.tollgate, ks=pe.keystone;
  document.getElementById('foot').innerHTML =
    `Context: a ~$${ctx.market_size_b}B creator economy, ~${ctx.creators_m}M creators, up to ${ctx.late_pct}% paid late. `+
    `Payout engine checks: Sybil cheating defeated ${bw.defeated ? 'yes' : 'no'}; legality rules pass ${pe.clearwright_ok ? 'yes' : 'no'}; `+
    `cross-border withholding ${money(tg.withheld)} of ${money(tg.gross)}; batch reconciliation ${ks.status}, money conserved ${ks.conserved ? 'yes' : 'no'}. `+
    `World map: simple-world-map (CC BY-SA 3.0).`;

  // the operator agent's decision feed (a pre-computed real run; driver + rail shown)
  const op=data.operator_run;
  if(op && op.cycles && op.cycles.length){
    const esc=s=>String(s==null?'':s).replace(/</g,'&lt;');
    document.getElementById('opfeed').style.display='';
    document.getElementById('opDriver').textContent=op.driver||'model';
    document.getElementById('opRail').textContent=op.paypal||'sandbox';
    const why=c=>{ const h=(c.held||[]).map(x=>`<b>${esc(x.creator)}</b> <span class="muted">(${esc(String(x.context||'').split(',').slice(-1)[0].trim())})</span>`).join(', ');
      const sig=c.signal?`<span class="pill bad">signal</span> ${esc(c.signal)} `:'';
      const none=!(c.paid||[]).length && !(c.held||[]).length;
      return sig+(h?'held '+h:`<span class="muted">${none?'nothing was due yet':'everyone due was paid'}</span>`); };
    const rows=op.cycles.map(c=>`<tr><td>${c.period}</td><td style="text-align:left;white-space:normal;max-width:420px">${why(c)}</td>`+
      `<td>${c.risk_multiplier}x</td><td>${money(c.safe_release)}</td><td>${(c.paid||[]).length}</td><td>${(c.held||[]).length}</td>`+
      `<td>${money(c.paid_total)}</td><td>${c.reserve_ok_after?'<span style="color:var(--good)">ok</span>':'<span style="color:var(--warn)">low</span>'}</td></tr>`).join('');
    document.getElementById('opTable').innerHTML=
      '<thead><tr><th>Cycle</th><th style="text-align:left">Who was held, and why</th><th>Risk</th><th>Safe release</th><th>Paid</th><th>Held</th><th>Paid total</th><th>Reserve</th></tr></thead><tbody>'+rows+'</tbody>';
  }
})();
</script>

<script>
// The live engine console: each tool calls a real backend endpoint over HTTP.
(function(){
  const money = v => '$' + Number(v).toLocaleString(undefined,{maximumFractionDigits:2});
  const pct = v => (Number(v)*100).toFixed(1) + '%';
  const esc = s => String(s).replace(/</g,'&lt;');
  const kv = (k,v) => `<div class="kv">${k}: <b>${v}</b></div>`;
  // which model actually ran each agent step, or why that step fell back to its rules
  const steps = n => { const e=Object.entries(n||{}); if(!e.length) return '';
    return `<div class="kv" style="margin-top:4px">`+e.map(([k,v])=>v.driver==='model'
      ? `<span class="pill good" title="${esc(v.model||'')}">${esc(k.replace('_',' '))} &middot; model</span>`
      : `<span class="pill bad" title="${esc(v.error||'')}">${esc(k.replace('_',' '))} &middot; rules${v.error?': '+esc(v.error).slice(0,60):''}</span>`).join(' ')+`</div>`; };
  // one account per browser: every capability reads and writes the same books
  let SID = null;
  try { SID = localStorage.getItem('helm-sid'); } catch(e){}
  if(!SID){ SID = 's' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    try { localStorage.setItem('helm-sid', SID); } catch(e){} }
  async function call(path, opts){
    opts = opts || {}; opts.headers = Object.assign({'X-Helm-Session': SID}, opts.headers || {});
    const r = await fetch(path, opts);
    let body; try { body = await r.json(); } catch(e){ body = {error:'backend returned no JSON'}; }
    if(path.indexOf('/api/account') !== 0){
      if(body && body.account) renderAccount(body.account); else if(opts.method === 'POST') refreshAccount();
    }
    return {status:r.status, body};
  }
  const post = (p,o) => call(p, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(o)});
  const get  = (p)   => call(p);
  async function refreshAccount(){ const r = await call('/api/account'); if(r.status===200) renderAccount(r.body); }
  function renderAccount(a){
    const el = document.getElementById('acct-body'); if(!el || !a) return;
    const holds = (a.open_holds||[]).map(h=>`<div class="kv"><span class="pill">held ${money(h.amount)}</span> <b>${esc(h.title)}</b> <span class="muted">${esc(h.merchant)}</span> `+
      `<button class="btn" data-settle="${esc(h.escrow_id)}" data-ok="1">Confirm delivery</button> `+
      `<button class="btn" data-settle="${esc(h.escrow_id)}" data-ok="0">Not delivered</button></div>`).join('');
    const ev = (a.events||[]).map(e=>`<div class="kv muted">${esc(e.text)}</div>`).join('');
    show(el, `<span class="pill ${a.solvent?'good':'bad'}">safety fund <b>${money(a.reserves)}</b></span>`+
      `<span class="pill">owed to creators <b>${money(a.liabilities)}</b></span>`+
      `<span class="pill ${a.margin>=0?'good':'bad'}">solvency margin <b>${money(a.margin)}</b></span>`+
      `<span class="pill">your earnings <b>${money(a.my_earnings)}</b>${a.my_settled!=null?` <span class="muted">(${money(a.my_settled)} past the chargeback window)</span>`:''}</span>`+
      (a.mandate?`<span class="pill">spend mandate <b>${money(a.mandate.spent)}</b> of ${money(a.mandate.max_total)} used</span>`:'')+
      (a.market?`<span class="pill">marketplace <b>${a.market.creators}</b> creators, ${money(a.market.gmv_30d)} sales in 30 days${a.market.suspended?`, <b>${a.market.suspended}</b> suspended`:''}</span>`:'')+
      `<span class="pill">advances out <b>${money(a.advances_outstanding)}</b></span>`+
      `<span class="pill ${a.chain_intact?'good':'bad'}">${a.receipts} receipts, chain ${a.chain_intact?'intact':'broken'}</span>`+
      (holds?`<div style="margin-top:8px"><b>Waiting on delivery</b>${holds}</div>`:'')+
      (ev?`<div style="margin-top:8px"><b>Recent activity</b>${ev}</div>`:`<div class="kv muted" style="margin-top:8px">No activity yet. Take an advance, buy something, or run the operator, and watch these books move.</div>`));
    el.querySelectorAll('button[data-settle]').forEach(btn=>{ btn.onclick = async () => {
      busy(btn,true); await post('/api/escrow/settle',{escrow_id:btn.dataset.settle, delivered:btn.dataset.ok==='1'}); }; });
  }
  setTimeout(()=>{
    const r = document.getElementById('acct-reset');
    if(r) r.onclick = async () => { const x = await call('/api/account/reset',{method:'POST'}); if(x.status===200) renderAccount(x.body); };
    refreshAccount();
  }, 0);
  const show = (el,html) => { el.innerHTML = html; };
  const err  = (el,r)   => show(el, `<div class="err">error (${r.status}): ${esc(r.body.error||'failed')}</div>`);
  const busy = (btn,on) => { btn.disabled = on; btn.dataset.t = btn.dataset.t||btn.textContent; btn.textContent = on?'working...':btn.dataset.t; };

  let mandate = null;   // the issued demo credential pair

  const TOOLS = [
  { id:'creator', label:'Your creator page', html:`
      <p class="muted" style="margin:0 0 6px">Your page as a creator, from your real sales in this marketplace: earnings by window, a Holt-Winters forecast, what to make next, money moves that each need your approval, and your tax statement. A personal manager agent writes the briefing.</p>
      <button class="btn" id="cr-run">Open my page</button>
      <div class="result" id="cr-out"></div>`,
    wire(){ const b=document.getElementById('cr-run'), o=document.getElementById('cr-out');
      b.onclick = async () => { busy(b,true); const r=await get('/api/creator?brief=1'); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body, e=d.earnings||{}, t=d.tax||{}, f=d.forecast||{}, rc=d.recommendations||{};
        const w=k=>`<span class="pill">${k} <b>${money((e[k]||{}).net)}</b> net</span>`;
        const props=(d.proposals||[]).map(p=>`<div class="kv"><span class="pill">${esc(p.action.replace('_',' '))}</span> ${p.up_to!=null?'up to '+money(p.up_to):money(p.suggested)} <span class="muted">${esc(p.why||'')}</span> <span class="pill">needs your approval</span></div>`).join('');
        show(o, (d.briefing?`<div class="kv" style="margin-bottom:8px">${esc(d.briefing)}</div>`:'')+
          w('week')+w('month')+w('year')+
          `<span class="pill">owed now <b>${money(d.creator.owed)}</b> (${money(d.creator.settled)} settled)</span>`+
          `<div class="kv" style="margin-top:6px"><b>forecast</b> ${esc(f.text||f.summary||JSON.stringify(f).slice(0,160))}</div>`+
          `<div class="kv"><b>make next</b> ${(rc.suggested_focus||[]).map(x=>`<span class="pill good">${esc(x)}</span>`).join('')} <span class="muted">${esc(rc.text||'')}</span></div>`+
          `<div style="margin-top:6px"><b>proposals</b>${props}</div>`+
          `<div class="kv" style="margin-top:6px"><b>tax</b> ${esc(t.summary||'')}</div>`); }; } },

  { id:'market', label:'Your marketplace', html:`
      <p class="muted" style="margin:0 0 6px">The two-sided marketplace your account lives in: 120 creators who sell and buy, two coordinated fraud rings planted in the history (never labeled). Scan it with the abuse and ring engines and the suspended creators' earnings freeze: the operator cannot pay them and buyers cannot buy from them. Let model-driven agent customers trade for a cycle, or have a buyer dispute one of your sales and watch it claw back.</p>
      <button class="btn" id="mk-view">Show the marketplace</button> <button class="btn" id="mk-scan">Scan for abuse and rings</button>
      <button class="btn" id="mk-agents">Run agent customers</button> <button class="btn" id="mk-dispute">A buyer disputes my latest sale</button>
      <div class="result" id="mk-out"></div>`,
    wire(){ const o=document.getElementById('mk-out');
      const row=c=>`<div class="kv"><b>${esc(c.name)}</b> <span class="muted">${esc(c.id)} &middot; ${esc(c.country)}</span> <span class="pill">owed ${money(c.owed)}</span><span class="pill">${c.sales_30d} sales / 30d</span><span class="pill ${c.bad_rate>0.2?'bad':''}">bad ${pct(c.bad_rate)}</span>${c.status!=='active'?'<span class="pill bad">suspended</span>':''}<span class="pill">payee ${esc(c.payee)}</span></div>`;
      const v=document.getElementById('mk-view'); v.onclick = async () => { busy(v,true); const r=await get('/api/market'); busy(v,false);
        if(r.status!==200) return err(o,r); const d=r.body, ov=d.overview, st=d.settlement;
        show(o, `<span class="pill">${ov.creators} creators</span><span class="pill">${ov.listings} listings</span><span class="pill">${ov.orders} orders</span><span class="pill">${money(ov.gmv_30d)} sales in 30 days</span><span class="pill">platform fee ${pct(ov.take_rate)}</span>`+
          `<div class="kv muted" style="margin-top:6px">money settles to ${esc(st.payee)}; Multiparty ${st.multiparty?'on':'off (needs an approved PayPal partner)'}</div>`+
          `<div style="margin-top:8px"><b>You</b>${row(d.me)}</div><div style="margin-top:8px"><b>Owed the most</b>${d.top_creators.filter(c=>c.id!=='me').map(row).join('')}</div>`+
          (d.suspended.length?`<div style="margin-top:8px"><b>Suspended</b>${d.suspended.map(row).join('')}</div>`:'')+
          `<div style="margin-top:8px"><b>Your listings</b> ${d.my_listings.map(l=>`<span class="pill">${esc(l.title)} ${money(l.price)}</span>`).join('')}</div>`); };
      const sc=document.getElementById('mk-scan'); sc.onclick = async () => { busy(sc,true); const r=await post('/api/market/scan',{apply:true}); busy(sc,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        show(o, `<div class="kv"><b>${d.suspended.length}</b> accounts suspended, <b>${money(d.frozen_earnings)}</b> of earnings frozen</div>`+
          d.rings.map(g=>`<div class="kv"><span class="verdict no">ring ${esc(g.id)}</span> <span class="pill">${g.members.length} accounts</span> <span class="pill">${esc(Object.keys(g.shared||{}).join(', '))}</span> <span class="muted">${esc(g.reason)}</span></div>`).join('')+
          d.verdicts.map(x=>`<div class="kv"><span class="pill bad">${esc(x.action)}</span> <span class="muted">${esc(x.reason)}</span></div>`).join('')); };
      const ag=document.getElementById('mk-agents'); ag.onclick = async () => { busy(ag,true); const r=await post('/api/market/agents',{ticks:1}); busy(ag,false);
        if(r.status!==200) return err(o,r); const d=r.body, ev=((d.ticks||[])[0]||{}).events||[];
        show(o, `<div class="kv muted">model ${esc(d.model)} &middot; ${d.sales} sales, ${d.returns} returns booked to the sellers' earnings</div>`+
          ev.map(e=>`<div class="kv"><b>${esc(e.agent)}</b> <span class="pill">${esc(e.persona)}</span> <span class="pill">${esc(e.action)}</span> ${esc(e.outcome)} <span class="muted">${esc(e.reason||'')}</span></div>`).join('')); };
      const dp=document.getElementById('mk-dispute'); dp.onclick = async () => { busy(dp,true); const r=await post('/api/disputes/simulate',{}); busy(dp,false);
        if(r.status!==200) return err(o,r); const d=r.body, cb=d.chargeback||{}, ev=d.evidence||{};
        if(!cb.status) return show(o, `<div class="kv muted">${esc(d.reason||d.status)}</div>`);
        show(o, `<span class="verdict no">dispute ${esc(d.dispute_id)}</span> <span class="pill">simulated CUSTOMER.DISPUTE.CREATED</span>`+
          `<div class="kv" style="margin-top:6px">order ${esc(d.order_id)}: clawed back <b>${money(cb.clawed)}</b> from the seller's earnings${cb.recoup_due?`, ${money(cb.recoup_due)} owed back from future sales`:''}</div>`+
          `<div class="kv">abuse engines re-ran: seller ${d.seller_suspended?'<b>suspended</b>':'still active'}</div>`+
          `<div class="kv"><b>evidence</b> ${esc(((ev.evidences||[])[0]||{}).notes||'')} <span class="muted">${esc(d.evidence_note||'')}</span></div>`); };
    } },

  { id:'negotiate', label:'Agent negotiates', html:`
      <p class="muted" style="margin:0 0 6px">Agent-to-agent commerce on your marketplace. Your agent negotiates another creator's listing under the mandate your owner key signed: if the ask is over your per-item cap it counters (the seller's floor is 80% of ask), a deterministic fit check blocks anything outside the mandate, and the deal settles on PayPal paid to that creator.</p>
      <div class="live-row"><div><label>listing id (from Spend earnings or Your marketplace)</label><input id="ng-l" value="l00018"></div>
        <div style="flex:0 0 150px"><label>per-item cap you sign</label><input id="ng-c" type="number" value="10"></div></div>
      <button class="btn" id="ng-run">Negotiate and buy</button>
      <div class="result" id="ng-out"></div>`,
    wire(){ const b=document.getElementById('ng-run'), o=document.getElementById('ng-out');
      b.onclick = async () => { busy(b,true); const r=await post('/api/market/negotiate',{listing:document.getElementById('ng-l').value, max_per_item:+document.getElementById('ng-c').value||null}); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        show(o, `<span class="verdict ${d.status==='settled'?'ok':'no'}">${esc(d.status)}</span> `+
          (d.seller_name?`<span class="pill">${esc(d.seller_name)}</span>`:'')+(d.ask!=null?`<span class="pill">ask ${money(d.ask)}</span><span class="pill good">agreed ${money(d.agreed)}</span>`:'')+
          `<div class="kv muted" style="margin-top:4px">${esc(d.reason||'')}</div>`+
          (d.sale?`<div class="kv">${money(d.sale.seller_net)} to the creator's earnings, ${money(d.sale.platform_fee)} platform fee &middot; payee ${esc(d.payee)}${d.order_id?' &middot; PayPal order '+esc(d.order_id):''}</div>`:'')+
          (d.mandate?`<div class="kv muted">mandate: ${money(d.mandate.spent)} of ${money(d.mandate.max_total)} used, per item ${money(d.mandate.max_per_item)}</div>`:'')); }; } },
  { id:'policy', label:'Policy compiler', html:`
      <label>Treasury policy, in plain English</label>
      <textarea id="pol-in">Pay the longest-waiting creators first, never send more than 20 percent to any one creator, and hold anyone high risk.</textarea>
      <button class="btn" id="pol-run">Compile with the model</button>
      <div class="result" id="pol-out"></div>`,
    wire(){ const b=document.getElementById('pol-run'), o=document.getElementById('pol-out');
      b.onclick = async () => { busy(b,true); const r = await post('/api/policy',{text:document.getElementById('pol-in').value}); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body, w=d.weights, c=d.constraints;
        show(o, `<div class="kv">model read it as: <b>${esc(d.reading||'')}</b></div>`+
          `<span class="pill">speed <b>${w.speed}</b></span><span class="pill">tax <b>${w.tax}</b></span>`+
          `<span class="pill">risk <b>${w.risk}</b></span><span class="pill">fx <b>${w.fx}</b></span>`+
          `<span class="pill">cap/creator <b>${Math.round(c.max_fraction_per_creator*100)}%</b></span>`+
          `<span class="pill">max risk <b>${c.max_risk}</b></span>`+
          (c.exclude_countries.length?`<span class="pill bad">exclude <b>${c.exclude_countries.join(', ')}</b></span>`:'')+
          (d.compiled?`<div class="kv" style="margin-top:8px">the solver will enforce: <b>${esc(d.compiled)}</b></div>`:'')+
          ((d.violations||[]).length?d.violations.map(v=>`<div class="kv"><span class="pill bad">flagged</span> ${esc(v)}</div>`).join(''):'')+
          `<div class="kv" style="margin-top:8px">compiled by: <b>${d.source}</b></div>`); }; } },

  { id:'signal', label:'Signal reader', html:`
      <label>An operational signal the agent should react to</label>
      <textarea id="sig-in">A hurricane warning just hit the US southeast; expect a demand spike next week.</textarea>
      <div class="live-row"><div><label>baseline demand</label><input id="sig-base" type="number" value="1000"></div>
        <div><label>horizon (periods)</label><input id="sig-h" type="number" value="6"></div></div>
      <button class="btn" id="sig-run">Read the signal</button>
      <div class="result" id="sig-out"></div>`,
    wire(){ const b=document.getElementById('sig-run'), o=document.getElementById('sig-out');
      b.onclick = async () => { busy(b,true);
        const r = await post('/api/signal',{text:document.getElementById('sig-in').value,
          baseline_demand:+document.getElementById('sig-base').value, horizon:+document.getElementById('sig-h').value});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const deltas = Object.entries(d.period_deltas).map(([k,v])=>`<span class="pill">+${k} <b>${v>=0?'+':''}${Math.round(v)}</b></span>`).join('')||'<span class="muted">no change proposed</span>';
        show(o, kv('cited signal', esc(d.cited||'none'))+kv('rationale', esc(d.rationale))+
          `<span class="pill">confidence <b>${pct(d.confidence)}</b></span><span class="pill">disagreement <b>${pct(d.disagreement)}</b></span>`+
          `<div class="kv" style="margin-top:8px">demand deltas by period:</div>${deltas}`+
          `<div class="kv" style="margin-top:6px">source: <b>${d.source}</b></div>`); }; } },

  { id:'advance', label:'Advance pricing', html:`
      <div class="live-row"><div><label>proven unpaid earnings</label><input id="adv-earn" type="number" value="2000"></div>
        <div><label>your name</label><input id="adv-who" value="you"></div></div>
      <label>past payout history (comma separated, oldest first)</label>
      <input id="adv-hist" value="800, 1200, 900, 1100, 1000, 950">
      <p class="muted" style="margin:4px 0 0">Priced against your account's live safety fund.</p>
      <button class="btn" id="adv-run">Price an advance</button>
      <div class="result" id="adv-out"></div>`,
    wire(){ const b=document.getElementById('adv-run'), o=document.getElementById('adv-out');
      const ask = (take) => {
        const hist = document.getElementById('adv-hist').value.split(',').map(x=>parseFloat(x.trim())).filter(x=>!isNaN(x));
        return post('/api/advance',{creator:document.getElementById('adv-who').value||'you',
          proven_earnings:+document.getElementById('adv-earn').value, history:hist, take:take}); };
      b.onclick = async () => { busy(b,true); const r = await ask(false); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        show(o, `<span class="verdict ${d.eligible?'ok':'no'}">${d.eligible?'eligible':'declined'}</span>`+
          `<span class="pill good">offer <b>${money(d.offer!=null?d.offer:d.max_amount)}</b></span>`+
          `<span class="pill">point-estimate cap <b>${money(d.max_amount)}</b></span>`+
          `<span class="pill">default prob <b>${pct(d.pd)}</b></span>`+
          `<span class="pill">fee <b>${pct(d.fee_rate)}</b></span>`+
          `<span class="pill">binding cap <b>${d.binding_cap}</b></span>`+
          (d.pd_band?`<span class="pill">PD band <b>${pct(d.pd_band.low)}–${pct(d.pd_band.high)}</b> @ ${pct(d.pd_band.coverage)}</span>`:'')+
          `<div class="kv" style="margin-top:8px">${esc(d.reason)}</div>`+
          (d.eligible?`<button class="btn" id="adv-take" style="margin-top:8px">Take this advance</button><div id="adv-taken"></div>`:''));
        const t=document.getElementById('adv-take'); if(t) t.onclick = async () => { busy(t,true); const x = await ask(true); busy(t,false);
          const tk=(x.body||{}).taken||{}, el=document.getElementById('adv-taken');
          if(x.status!==200) return err(el,x);
          show(el, tk.status==='advanced'
            ? `<span class="verdict ok">advanced</span><span class="pill">${money(tk.amount)} paid out</span><span class="pill">fee ${money(tk.fee)}</span><span class="pill">fund now ${money(tk.fund_after)}</span><div class="kv muted">25% of future payouts repay it. See your account above: the margin and the solvency proof moved.</div>`
            : `<span class="verdict no">${esc(tk.status||'refused')}</span> <span class="muted">${esc(tk.reason||'')}</span>`); }; }; } },

  { id:'rladvance', label:'RL advance-sizer', html:`
      <p class="muted" style="margin:0 0 6px">How much of a creator's earnings to advance is a credit-limit decision: advance more and earn fee, lose the principal if they default. A <b>reinforcement-learning</b> agent, trained <b>offline on simulated outcomes</b> (not stock-picking, where LLM agents lose), learns per risk estimate how much to advance, beating fixed and rule-of-thumb lenders. RL proposes the fraction; the advance engine still applies the caps.</p>
      <button class="btn" id="rl-run">Train and compare the policy</button>
      <div class="result" id="rl-out"></div>`,
    wire(){ const b=document.getElementById('rl-run'), o=document.getElementById('rl-out');
      b.onclick = async () => { busy(b,true); const r=await get('/api/rl/advance'); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        const pol=(d.policy||[]).map(x=>`<div class="kv"><span class="pill">PD ${esc(x.risk_estimate)}</span> <span class="pill ${x.advance_fraction>0?'good':'bad'}">advance ${Math.round(x.advance_fraction*100)}%</span></div>`).join('');
        const row=(k,lbl)=>{const e=d[k]||{};return `<div class="kv"><b>${lbl}</b> <span class="pill ${e.avg_net_profit>0?'good':'bad'}">net ${money(e.avg_net_profit)}/creator</span></div>`;};
        show(o, `<div class="kv muted">learned policy (risk estimate &rarr; advance fraction):</div>${pol}`+
          `<div class="kv" style="margin-top:8px"><b>Held-out net profit per creator</b></div>`+
          row('learned','RL (learned)')+row('rule_of_thumb','rule of thumb')+row('always_max_1.0','always advance max')+row('conservative_0.25','always conservative')+
          `<div class="kv muted" style="margin-top:4px">${esc(d.note||'')}</div>`); }; } },

  { id:'tax', label:'Tax regime', html:`
      <div class="live-row">
        <div><label>country</label><select id="tax-c"><option>US</option><option>DE</option><option>FR</option><option>GB</option><option>IN</option></select></div>
        <div><label>gross for the year</label><input id="tax-g" type="number" value="25000"></div>
        <div><label>transactions</label><input id="tax-t" type="number" value="250"></div></div>
      <button class="btn" id="tax-run">Check the regime</button>
      <div class="result" id="tax-out"></div>`,
    wire(){ const b=document.getElementById('tax-run'), o=document.getElementById('tax-out');
      b.onclick = async () => { busy(b,true);
        const r = await get(`/api/tax?country=${document.getElementById('tax-c').value}&gross=${+document.getElementById('tax-g').value}&transactions=${+document.getElementById('tax-t').value}`);
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const rows = Object.entries(d).map(([k,v])=>kv(esc(k.replace(/_/g,' ')), esc(v))).join('');
        show(o, rows); }; } },

  { id:'invest', label:'Invest at live prices', html:`
      <label>ticker</label>
      <div class="live-row"><div><input id="iv-tk" value="SPY"></div><div style="flex:0"><button class="btn ghost" id="iv-q">Live quote</button></div></div>
      <div class="result" id="iv-qout"></div>
      <label style="margin-top:14px">amount to invest across the basket</label>
      <input id="iv-amt" type="number" value="1000">
      <button class="btn" id="iv-run">Invest at live prices</button>
      <div class="result" id="iv-out"></div>`,
    wire(){ const q=document.getElementById('iv-q'), qo=document.getElementById('iv-qout'),
        b=document.getElementById('iv-run'), o=document.getElementById('iv-out');
      q.onclick = async () => { busy(q,true); const r=await get('/api/quote?ticker='+encodeURIComponent(document.getElementById('iv-tk').value)); busy(q,false);
        if(r.status!==200) return err(qo,r); show(qo, `<span class="pill">${esc(r.body.ticker)} <b>${money(r.body.price)}</b></span><span class="pill">via <b>${r.body.backend}</b></span>`); };
      b.onclick = async () => { busy(b,true); const r=await post('/api/invest',{amount:+document.getElementById('iv-amt').value}); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        const fills = d.fills.map(f=>`<span class="pill">${f.ticker} <b>${f.units} @ ${money(f.price)}</b></span>`).join('');
        show(o, fills+`<div class="kv" style="margin-top:8px">backend: <b>${d.backend}</b> &middot; cost <b>${money(d.cost_basis)}</b> &middot; marked to market <b>${money(d.market_value)}</b></div>`+
          (d.backend==='alpaca-paper'?'<div class="kv">routed as a real Alpaca paper order</div>':'')); }; } },

  { id:'mandate', label:'Agent mandate (crypto)', html:`
      <p class="muted" style="margin:0 0 6px">The owner signs a mandate once. The agent may then spend inside it with no human in the loop, and any deal outside it, or any forged mandate, is refused by the signature, not by a rule you can bypass.</p>
      <button class="btn ghost" id="mn-issue">Issue an owner-signed mandate</button>
      <div class="result" id="mn-info"></div>
      <div id="mn-controls" style="display:none">
        <div class="live-row">
          <div><label>category the agent wants to buy</label><select id="mn-cat"><option>stock_photos</option><option>music_license</option><option>fonts</option><option>weapons</option></select></div>
          <div><label>price</label><input id="mn-price" type="number" value="30"></div></div>
        <div class="chk"><input type="checkbox" id="mn-tamper"><label for="mn-tamper" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">forge it: raise the per-item cap without re-signing</label></div>
        <button class="btn" id="mn-run">Verify and decide</button>
        <div class="result" id="mn-out"></div>
      </div>`,
    wire(){ const iss=document.getElementById('mn-issue'), info=document.getElementById('mn-info'),
        ctl=document.getElementById('mn-controls'), b=document.getElementById('mn-run'), o=document.getElementById('mn-out');
      iss.onclick = async () => { busy(iss,true); const r=await get('/api/a2a/demo'); busy(iss,false);
        if(r.status!==200) return err(info,r); mandate=r.body;
        show(info, `<span class="pill good">signed <b>ES256</b></span>`+
          `<span class="pill">allowed <b>${mandate.allowed_categories.join(', ')}</b></span>`+
          `<span class="pill">per-item cap <b>${money(mandate.max_per_item)}</b></span>`+
          `<span class="pill">auto-approve under <b>${money(mandate.approval_threshold)}</b></span>`);
        ctl.style.display=''; };
      b.onclick = async () => { if(!mandate) return; busy(b,true);
        const cred = document.getElementById('mn-tamper').checked ? mandate.tampered : mandate.valid;
        const r = await post('/api/a2a/check',{intent_credential:cred, category:document.getElementById('mn-cat').value, price:+document.getElementById('mn-price').value, spent:0});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const v = !d.verified ? '<span class="verdict no">signature rejected</span>'
          : d.needs_approval ? '<span class="verdict hold">needs owner approval</span>'
          : d.fits ? '<span class="verdict ok">agent may proceed</span>'
          : '<span class="verdict no">outside the mandate</span>';
        show(o, v+`<div class="kv" style="margin-top:6px">${esc(d.reason)}</div>`); }; } },

  { id:'identity', label:'Agent identity', html:`
      <p class="muted" style="margin:0 0 6px">A mandate says what an agent may do; an identity says who it is. The agent presents a signed identity (id, owner, capabilities); a counterparty verifies the signature, expiry and required capability before transacting. Forge the owner or ask for a capability it lacks, and it is refused.</p>
      <div class="live-row"><div><label>agent id</label><input id="id-aid" value="agent-7"></div>
        <div><label>owner</label><input id="id-own" value="ava"></div>
        <div style="flex:0 0 160px"><label>require capability</label><input id="id-req" value="buy"></div></div>
      <div class="chk"><input type="checkbox" id="id-tamper"><label for="id-tamper" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">forge: change the owner without re-signing</label></div>
      <button class="btn" id="id-run">Verify identity</button>
      <div class="result" id="id-out"></div>`,
    wire(){ const b=document.getElementById('id-run'), o=document.getElementById('id-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/identity/demo',{agent_id:document.getElementById('id-aid').value,
          owner:document.getElementById('id-own').value, require:document.getElementById('id-req').value,
          tamper:document.getElementById('id-tamper').checked, capabilities:['buy','pool']});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const v = d.verified ? '<span class="verdict ok">identity verified</span>' : '<span class="verdict no">rejected</span>';
        show(o, v+(d.agent_id?`<span class="pill">${esc(d.agent_id)}</span><span class="pill">owner ${esc(d.owner)}</span><span class="pill">${esc((d.capabilities||[]).join(', '))}</span>`:'')+
          `<div class="kv" style="margin-top:6px">${esc(d.reason)}</div>`); }; } },

  { id:'pool', label:'Pool together', html:`
      <p class="muted" style="margin:0 0 6px">Anyone can band together with others, to co-own one position or to buy in bulk. Each person's share is funded only up to the budget they signed, a forged mandate is dropped, and the economics are split by rules that are provably fair.</p>
      <label>Pool to co-own one position (one real order, units split pro-rata)</label>
      <div class="live-row"><div style="flex:0 0 90px"><label>asset</label><input id="pl-asset" value="SPY"></div>
        <div><label>Ava puts in</label><input id="pl-a" type="number" value="300"></div>
        <div><label>Ben puts in</label><input id="pl-b" type="number" value="150"></div>
        <div><label>Chen puts in</label><input id="pl-c" type="number" value="50"></div></div>
      <div class="chk"><input type="checkbox" id="pl-forge"><label for="pl-forge" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">forge Ava's mandate: raise her budget without re-signing</label></div>
      <button class="btn" id="pl-run">Pool and co-buy</button>
      <div class="result" id="pl-out"></div>
      <label style="margin-top:16px">Group buy to unlock a volume discount none could reach alone</label>
      <div class="live-row"><div><label>item</label><input id="gb-item" value="preset pack"></div>
        <div style="flex:0 0 110px"><label>unit price</label><input id="gb-price" type="number" value="20"></div></div>
      <div class="live-row"><div><label>Ava qty</label><input id="gb-a" type="number" value="2"></div>
        <div><label>Ben qty</label><input id="gb-b" type="number" value="2"></div>
        <div><label>Chen qty</label><input id="gb-c" type="number" value="1"></div>
        <div><label>Dia qty</label><input id="gb-d" type="number" value="1"></div>
        <div><label>Eli qty</label><input id="gb-e" type="number" value="1"></div></div>
      <button class="btn" id="gb-run">Buy in bulk together</button>
      <div class="result" id="gb-out"></div>`,
    wire(){ const b=document.getElementById('pl-run'), o=document.getElementById('pl-out');
      b.onclick = async () => { busy(b,true);
        const members=[{member:'Ava',amount:+document.getElementById('pl-a').value},
          {member:'Ben',amount:+document.getElementById('pl-b').value},
          {member:'Chen',amount:+document.getElementById('pl-c').value}];
        const r=await post('/api/pool/invest',{asset:document.getElementById('pl-asset').value,members:members,forge:document.getElementById('pl-forge').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const rows=d.allocations.map(a=>`<div class="kv">${a.ok?'<span class="pill good">in</span>':'<span class="pill bad">dropped</span>'} <b>${esc(a.member)}</b> `+
          `<span class="pill">${a.signed?'signed':'unsigned'}</span>`+
          (a.ok?`<span class="pill">owns <b>${pct(a.share)}</b></span><span class="pill">${a.units} units</span><span class="pill">${money(a.value)}</span>`:'')+
          ` <span class="muted">${esc(a.reason)}</span></div>`).join('');
        show(o, `<span class="pill">asset <b>${esc(d.asset)}</b></span><span class="pill">pooled <b>${money(d.funded_total)}</b></span>`+
          `<span class="pill">${d.total_units} units @ ${money(d.price)}</span><span class="pill">via <b>${esc(d.backend)}</b></span>`+
          (d.routed_to_alpaca?'<span class="pill good">real Alpaca paper order</span>':'')+
          `<div style="margin-top:8px">${rows}</div>`); };
      const g=document.getElementById('gb-run'), go=document.getElementById('gb-out');
      g.onclick = async () => { busy(g,true);
        const price=+document.getElementById('gb-price').value;
        const members=[['Ava','gb-a'],['Ben','gb-b'],['Chen','gb-c'],['Dia','gb-d'],['Eli','gb-e']]
          .map(([n,id])=>({member:n,qty:+document.getElementById(id).value}));
        const r=await post('/api/pool/groupbuy',{item:document.getElementById('gb-item').value,unit_price:price,members:members});
        busy(g,false); if(r.status!==200) return err(go,r); const d=r.body;
        const rows=d.lines.filter(l=>l.ok&&l.qty>0).map(l=>`<div class="kv"><b>${esc(l.member)}</b> `+
          `<span class="pill">${l.qty}x</span><span class="pill">alone ${money(l.solo_cost)}</span>`+
          `<span class="pill good">pooled ${money(l.pooled_cost)}</span>`+
          `<span class="pill">fair saving <b>${money(l.saving_shapley)}</b></span></div>`).join('');
        show(go, `<span class="verdict ok">${pct(d.discount_rate)} off</span>`+
          `<span class="pill">${d.pooled_qty} units together</span>`+
          `<span class="pill">unit ${money(d.unit_price)} &rarr; <b>${money(d.discounted_unit_price)}</b></span>`+
          `<span class="pill">list ${money(d.total_list)}</span><span class="pill good">paid ${money(d.total_paid)}</span>`+
          `<span class="pill good">saved <b>${money(d.total_saved)}</b></span>`+
          `<div class="kv" style="margin-top:4px;" class="muted">saving split by the Shapley value (shares sum to the total saved):</div>`+
          `<div style="margin-top:6px">${rows}</div>`); }; } },

  { id:'verify', label:'Proven safe (Z3)', html:`
      <p class="muted" style="margin:0 0 6px">Most entries check an agent's spend against a rule. This <b>proves</b> with the Z3 solver that the agent can never exceed its signed budget over <b>any</b> sequence of deals, then shows the proof has teeth by busting the budget when a guard is removed. The result is an ES256-signed verdict.</p>
      <div class="live-row"><div><label>total budget the owner signs</label><input id="vf-t" type="number" value="500"></div>
        <div><label>per-item cap</label><input id="vf-m" type="number" value="100"></div></div>
      <div class="chk"><input type="checkbox" id="vf-forge"><label for="vf-forge" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">forge it: widen the budget without re-signing</label></div>
      <button class="btn" id="vf-run">Prove the mandate is bounded</button>
      <div class="result" id="vf-out"></div>`,
    wire(){ const b=document.getElementById('vf-run'), o=document.getElementById('vf-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/verify/mandate',{max_total:+document.getElementById('vf-t').value,
          max_per_item:+document.getElementById('vf-m').value, forge:document.getElementById('vf-forge').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        if(!d.verified_signature) return show(o, `<span class="verdict no">signature rejected</span><div class="kv" style="margin-top:6px">a tampered mandate never reaches the prover</div>`);
        const bs=d.budget_soundness, nc=d.guard_necessity;
        const ce = nc&&nc.busts ? `<div class="kv" style="margin-top:8px">guard necessity: without the running-total guard, Z3 finds <b>${nc.n_deals}</b> deals each within the ${'$'}${document.getElementById('vf-m').value} cap that total <b>${money(nc.total)}</b>, busting the budget</div>` : '';
        show(o, `<span class="verdict ok">${esc(d.result)}</span><span class="pill good">signature ES256</span><span class="pill good">verdict signed ${esc(d.verdict_alg||'ES256')}</span>`+
          `<div class="kv" style="margin-top:8px">${esc(bs.statement)}</div>`+
          `<span class="pill">Z3 inductive step <b>${esc(bs.inductive_step)}</b></span><span class="pill">proven <b>${bs.proven}</b></span>`+
          `<div class="kv muted" style="margin-top:4px">${esc(bs.method)}</div>`+ce); }; } },

  { id:'reserves', label:'Zero-knowledge reserves', html:`
      <p class="muted" style="margin:0 0 6px">The platform <b>proves</b> the safety fund covers every liability (advances, pool commitments) without revealing a single balance. Pedersen commitments on the bn128 curve plus a bit-decomposition range proof; the verifier learns only "reserves &ge; liabilities".</p>
      <p class="muted" style="margin:0 0 6px">Leave both empty to prove your account's live books; type numbers to try your own (a liability above the lots cannot be proven).</p>
      <label>safety-fund lots (comma separated)</label>
      <input id="rs-lots" placeholder="your account's lots">
      <label style="margin-top:10px">total liabilities outstanding</label>
      <input id="rs-liab" type="number" placeholder="what your platform owes creators">
      <button class="btn" id="rs-run">Prove solvency in zero knowledge</button>
      <div class="result" id="rs-out"></div>`,
    wire(){ const b=document.getElementById('rs-run'), o=document.getElementById('rs-out');
      b.onclick = async () => { busy(b,true);
        const lots=document.getElementById('rs-lots').value.split(',').map(x=>parseFloat(x.trim())).filter(x=>!isNaN(x));
        const lv=document.getElementById('rs-liab').value.trim(), q={bits:32};
        if(lots.length) q.lots=lots; if(lv!=='') q.liabilities=+lv;
        const r=await post('/api/reserves/prove',q);
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        if(!d.provable) return show(o, `<span class="verdict no">not provable</span><div class="kv" style="margin-top:6px">${esc(d.reason||'the fund is below its liabilities, so no sound proof exists')}</div>`);
        show(o, `<span class="verdict ${d.solvent?'ok':'no'}">${d.solvent?'SOLVENT, proven':'proof failed'}</span>`+
          `<span class="pill good">identity ${d.identity_ok}</span><span class="pill good">all ${d.bit_proofs} bit-proofs ${d.bits_ok}</span>`+
          `<div class="kv" style="margin-top:8px">${esc(d.statement)}</div>`+
          `<span class="pill">${d.lot_commitments} hidden lot commitments</span><span class="pill">range ${d.range_bits} bits</span>`+
          `<span class="pill">liability commitment <b>${esc(d.liability_commitment_sha256)}</b></span>`+
          `<div class="kv muted" style="margin-top:4px">reveals ${esc(d.reveals)}</div>`+
          (d.from_account?`<div class="kv muted">proved over your account's live books: published liabilities ${money(d.published_liabilities)}, bound to the commitment ${d.liabilities_bound?'yes':'no'}</div>`:'')); }; } },

  { id:'escrow', label:'Pay on proof', html:`
      <p class="muted" style="margin:0 0 6px">PayPal <b>authorizes and holds</b> the money, then deterministic acceptance criteria decide: capture on proof, void on failure. A model may draft the criteria, but code alone releases, and criteria an empty delivery could pass are refused before any funds are held.</p>
      <div class="live-row"><div><label>deal amount</label><input id="es-amt" type="number" value="200"></div></div>
      <div class="chk"><input type="checkbox" id="es-cheat"><label for="es-cheat" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">cheat: deliver nothing and try to get paid</label></div>
      <button class="btn" id="es-run">Hold, check, settle</button>
      <div class="result" id="es-out"></div>`,
    wire(){ const b=document.getElementById('es-run'), o=document.getElementById('es-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/escrow/demo',{amount:+document.getElementById('es-amt').value, cheat:document.getElementById('es-cheat').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const s=d.settled, st=s.status;
        const v = st==='released' ? '<span class="verdict ok">released, proof met</span>'
          : st==='refunded' ? '<span class="verdict hold">refunded, hold voided</span>'
          : '<span class="verdict no">'+esc(st)+'</span>';
        const crit=(s.criteria_results||[]).map(c=>`<span class="pill ${c.passed?'good':'bad'}">${esc(c.key)} ${c.passed?'met':'failed'}</span>`).join('');
        const mv=(d.movements||[]).map(m=>`<span class="pill">${esc(m.kind)}${m.ref_type&&m.ref_type!==m.kind?' &middot; '+esc(m.ref_type):''}</span>`).join('');
        show(o, v+`<span class="pill">held ${money(d.held.amount)}</span><span class="pill">via ${esc(d.backend)}</span>`+
          `<div class="kv" style="margin-top:8px">${esc(s.reason)}</div>`+
          `<div style="margin-top:6px">${crit}</div>`+
          `<div class="kv muted" style="margin-top:6px">ledger moves: ${mv}</div>`); }; } },

  { id:'buyer', label:'Buyer (multi-agent)', html:`
      <p class="muted" style="margin:0 0 6px">The buyer is a <b>LangGraph supervisor</b> dispatching worker agents across the journey: <b>understand</b> the need, <b>search</b> real products, <b>quarantine</b> injected listings, <b>select</b> within budget, <b>authorize</b> against the owner-signed mandate, and <b>settle</b> via pay-on-proof escrow. The agents propose; cryptography and PayPal dispose, so a hijacked buyer still cannot pay outside the signed budget.</p>
      <div class="live-row"><div><label>what the buyer needs</label><input id="cg-need" value="I need a trap beat pack for my next video"></div>
        <div style="flex:0 0 150px"><label>signed budget</label><input id="cg-b" type="number" value="80"></div></div>
      <button class="btn" id="cg-run">Run the buyer journey</button>
      <div class="result" id="cg-out"></div>`,
    wire(){ const b=document.getElementById('cg-run'), o=document.getElementById('cg-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/customer/graph',{need:document.getElementById('cg-need').value, budget:+document.getElementById('cg-b').value});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const steps=(d.trace||[]).map(s=>`<span class="pill good">${esc(s)}</span>`).join(' &rarr; ');
        const q=(d.quarantined||[]).map(x=>`<div class="kv bad">quarantined: ${esc(x.title||'')}</div>`).join('');
        const c=d.choice||{}, au=d.authorization||{}, se=d.settlement||{};
        show(o, `<div class="kv muted">driver <b>${esc(d.driver||'')}</b> &middot; model ${esc(d.model||'')} &middot; search ${esc(d.backend||'')}</div>`+steps(d.nodes)+
          `<div class="kv" style="margin-top:6px">${steps}</div>`+
          `<div class="kv" style="margin-top:8px"><b>understood</b> <span class="pill">${esc((d.intent||{}).query||'')}</span><span class="pill">${esc((d.intent||{}).category||'')}</span><span class="pill">&le; ${money((d.intent||{}).max_price)}</span></div>`+
          q+
          `<div class="kv" style="margin-top:6px"><b>chose</b> ${esc(c.title||c.reason||'nothing')} ${c.price!=null?money(c.price):''} <span class="muted">${esc(c.reason||'')}</span></div>`+
          ((d.grounding&&d.grounding.length)?`<div class="kv" style="margin-top:6px"><b>grounded in</b> ${d.grounding.map(g=>`<span class="pill">${esc(g.topic)}</span>`).join('')}</div>`:'')+
          `<span class="pill ${au.allowed?'good':'bad'}">mandate ${au.allowed?'admits':'refuses'}</span> <span class="muted">${esc(au.reason||'')}</span>`+
          (c.declined?`<div style="margin-top:6px"><span class="verdict no">nothing bought</span> <span class="muted">no listing fit the need, so the buyer declined instead of buying the wrong thing</span></div>`:'')+
          (c.source?`<div class="kv"><span class="pill ${c.source==='marketplace'?'good':''}">${c.source==='marketplace'?'a creator on your marketplace':'outside store'}</span></div>`:'')+
          (se && se.status?`<div style="margin-top:6px"><span class="verdict ok">${se.status==='held'?'held until delivery':'settled: '+esc(se.status)}</span> <span class="pill">${esc(se.backend||'')}</span>${se.payee?`<span class="pill">payee ${esc(se.payee)}</span>`:''}${se.authorization_id?`<span class="muted"> auth ${esc(se.authorization_id)}</span>`:''}</div>`:'')); }; } },

  { id:'shop', label:'Spend earnings', html:`
      <p class="muted" style="margin:0 0 6px">The same account that earns can spend. Listings from other creators on your marketplace come first (buying one pays that creator, minus the platform fee); outside gear comes from Channel3. The agent finds a real product, every listing is screened for prompt injection, a single-use token binds the charge to exactly what was reviewed, the owner's signed budget authorizes the buy, and PayPal escrow settles it.</p>
      <div class="live-row"><div><label>what to buy</label><input id="sh-q" value="lo-fi beat pack"></div>
        <div style="flex:0 0 150px"><label>budget to spend</label><input id="sh-b" type="number" value="120"></div></div>
      <div class="chk"><input type="checkbox" id="sh-inj"><label for="sh-inj" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">plant a prompt-injection listing to show it is quarantined</label></div>
      <div class="chk"><input type="checkbox" id="sh-tamper"><label for="sh-tamper" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">tamper: try to charge 10x the reviewed amount with the same token</label></div>
      <button class="btn" id="sh-run">Search real products</button>
      <div class="result" id="sh-out"></div>`,
    wire(){ const b=document.getElementById('sh-run'), o=document.getElementById('sh-out');
      const buy = async (p, i) => {
        const el=document.getElementById('buy-'+i); if(!el) return;
        const tamper=document.getElementById('sh-tamper').checked;
        const charge = tamper ? p.price*10 : p.price;      // token binds p.price; a tampered charge must be refused
        const r = await post('/api/shop/buy',{title:p.title, price:charge, merchant:p.merchant,
          category:p.category, budget:+document.getElementById('sh-b').value, intent_token:p.intent_token,
          listing:p.listing||null});
        if(r.status!==200) return err(el,r); const d=r.body;
        if(!d.authorized) return show(el, `<span class="verdict no">refused</span> <span class="muted">${esc(d.reason)}</span>`);
        show(el, `<span class="verdict ok">held</span><span class="pill">${money(d.price)} for ${esc(d.merchant)}</span>`+
          ((d.held||{}).seller?`<span class="pill good">pays creator ${esc(d.merchant)}: payee ${esc((d.held||{}).payee)}</span>`:'')+
          `<span class="pill">via ${esc(d.backend)}</span><span class="pill">confirm delivery in Your account</span>`+
          `<div class="kv muted" style="margin-top:4px">${esc(d.reason)}</div>`);
      };
      b.onclick = async () => { busy(b,true);
        const r = await post('/api/shop/search',{query:document.getElementById('sh-q').value,
          budget:+document.getElementById('sh-b').value, demo_injection:document.getElementById('sh-inj').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const cards = d.products.map((p,i)=>`<div class="live-tool" style="margin-bottom:8px">`+
          `<div class="kv"><b>${esc(p.title)}</b> <span class="muted">${esc(p.brand)}${p.merchant&&p.source!=='marketplace'?' &middot; '+esc(p.merchant):''}</span></div>`+
          (p.source==='marketplace'?`<span class="pill good">creator on your marketplace</span>`:`<span class="pill">outside store</span>`)+
          `<span class="pill">${money(p.price)}</span>`+
          (p.affordable?`<span class="pill good">within budget</span>`:`<span class="pill bad">over budget</span>`)+
          (p.intent_token?`<span class="pill">intent token issued</span>`:'')+
          (p.affordable?`<button class="btn" data-idx="${i}" style="margin-top:8px">Buy within mandate</button>`:'')+
          `<div class="result" id="buy-${i}"></div></div>`).join('');
        const quar=(d.quarantined||[]).map(q=>`<div class="kv"><span class="pill bad">quarantined</span> <b>${esc((q.title||'').slice(0,60))}</b> <span class="muted">prompt injection blocked before the model</span></div>`).join('');
        show(o, `<div class="kv">agent searched <b>${esc(d.query)}</b> &middot; source: <b>${esc(d.backend)}</b>${d.live?'':' (add CHANNEL3_API_KEY for live results)'}</div>`+
          (quar?`<div style="margin:6px 0">${quar}</div>`:'')+cards);
        o.querySelectorAll('button[data-idx]').forEach(btn=>{ const i=+btn.dataset.idx;
          btn.onclick=()=>{ btn.disabled=true; btn.textContent='buying...'; buy(d.products[i], i); }; });
      }; } },

  { id:'operator', label:'Operator (multi-agent)', html:`
      <p class="muted" style="margin:0 0 6px">The money-out operator is not one model in a loop; it is a <b>LangGraph of role agents that collaborate</b>. A signal analyst reads the week, a risk analyst judges each creator pay-vs-hold, a bull and a bear <b>debate</b> how aggressive to be, a manager proposes, compliance screens, and then deterministic code disposes the money under every guardrail. The agents only propose.</p>
      <label>the week's signal</label>
      <textarea id="og-sig">Risk alert: a fraud and chargeback wave is hitting brand-new viral accounts this week.</textarea>
      <div class="live-row"><div style="flex:0 0 160px"><label>debate rounds</label><input id="og-r" type="number" value="1" min="1" max="3"></div></div>
      <button class="btn" id="og-run">Run the operator cycle</button>
      <div class="result" id="og-out"></div>`,
    wire(){ const b=document.getElementById('og-run'), o=document.getElementById('og-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/operator/graph',{signal:document.getElementById('og-sig').value, debate_rounds:+document.getElementById('og-r').value});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const rv=(d.risk_views||[]).map(v=>`<div class="kv"><span class="pill ${v.verdict==='pay'?'good':'bad'}">${esc((v.verdict||'').toUpperCase())}</span> <b>${esc(v.creator)}</b> <span class="muted">${esc(v.reason||'')}</span></div>`).join('');
        const deb=(d.debate||[]).map(x=>`<div class="kv" style="margin-bottom:5px"><span class="pill ${x.role==='bull'?'good':'bad'}">${esc(x.role)} &middot; pushes ${x.pushes_multiplier}&times;</span> ${esc(x.argument)}</div>`).join('');
        const cm=(d.compliance||[]).map(c=>`<span class="pill ${c.decision==='allow'?'good':'bad'}">${esc(c.creator)}: ${esc(c.decision)}</span>`).join('') || '<span class="muted">nothing proposed to screen</span>';
        const dec=d.decision||{};
        const paid=(dec.paid||[]).map(p=>`${esc(p.creator)} ${money(p.amount)}`).join(', ')||'none';
        const fb=d.driver==='fallback'?`<div class="kv muted">The hosted model did not answer for part of this cycle (rate limit or network), so those agents used their deterministic rules. The money still moved only within every guardrail. Run again in a few seconds for the full model debate.</div>`:'';
        show(o, `<div class="kv muted">driver <b>${esc(d.driver||'')}</b> &middot; model ${esc(d.model||'')}</div>`+fb+steps(d.nodes)+
          `<div class="kv" style="margin-top:8px"><b>1 &middot; Risk analyst</b> (pay vs hold)</div>${rv}`+
          `<div class="kv" style="margin-top:8px"><b>2 &middot; Bull vs bear debate</b></div>${deb}`+
          `<span class="pill" style="margin-top:6px">3 &middot; manager sets risk multiplier <b>${d.risk_multiplier}&times;</b></span>`+
          `<div class="kv" style="margin-top:8px"><b>4 &middot; Compliance screen</b> ${cm}</div>`+
          ((d.grounding&&d.grounding.length)?`<div class="kv" style="margin-top:8px"><b>Grounded in</b> ${d.grounding.map(g=>`<span class="pill">${esc(g.topic)}</span>`).join('')}</div>`:'')+
          `<div class="kv" style="margin-top:8px"><b>5 &middot; Deterministic dispose</b></div>`+
          `<span class="pill ${dec.status==='completed'?'good':''}">decision: ${esc(dec.status||'')}</span> <span class="pill">paid ${esc(paid)}</span>`+
          (dec.safe_release_total!=null?`<div class="kv" style="margin-top:6px">The ${d.risk_multiplier}&times; multiplier sets a safe release of <b>${money(dec.safe_release_total)}</b>; the manager proposed ${money(dec.proposed_total)}${dec.proposed_total>dec.safe_release_total+0.005?', so code scaled it down to fit':', which fits'}.</div>`:'')+
          `<div class="kv muted" style="margin-top:4px">cash after ${money(dec.cash_after)} &middot; reserve ${dec.reserve_ok_after?'ok':'short'}${(dec.guardrail_overrides&&dec.guardrail_overrides.length)?' &middot; '+dec.guardrail_overrides.map(esc).join('; '):''}</div>`); }; } },

  { id:'pnl', label:'Platform P&L', html:`
      <p class="muted" style="margin:0 0 6px">How the platform makes money, safely, made quantitative. Expected revenue comes from a conformal demand forecast; expected loss is PD &times; LGD &times; EAD on the advance book plus chargebacks; profit carries a band, the fund holds a CECL-style provision, and RAROC checks the book earns its risk.</p>
      <div class="live-row"><div><label>safety fund balance</label><input id="pn-fund" type="number" placeholder="your account's fund"></div>
        <div style="flex:0 0 140px"><label>horizon</label><input id="pn-h" type="number" value="4"></div></div>
      <button class="btn" id="pn-run">Forecast P&L</button>
      <div class="result" id="pn-out"></div>`,
    wire(){ const b=document.getElementById('pn-run'), o=document.getElementById('pn-out');
      b.onclick = async () => { busy(b,true);
        const fv=document.getElementById('pn-fund').value.trim(), q={horizon:+document.getElementById('pn-h').value};
        if(fv!=='') q.fund=+fv;
        const r=await post('/api/pnl',q);
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const rev=d.expected_revenue, pf=d.risk_adjusted_profit, el=d.expected_loss;
        const rows=(d.book||[]).map(l=>`<div class="kv"><b>${esc(l.creator)}</b> <span class="pill">PD ${(l.pd*100).toFixed(0)}%</span><span class="pill">EAD ${money(l.ead)}</span><span class="pill bad">EL ${money(l.expected_loss)}</span></div>`).join('');
        show(o, `<span class="pill">expected revenue <b>${money(rev.mean)}</b> <span class="muted">[${money(rev.low)} to ${money(rev.high)}]</span></span>`+
          `<span class="pill bad">expected loss <b>${money(el.total)}</b></span>`+
          `<span class="verdict ${pf.mean>=0?'ok':'no'}">risk-adjusted profit ${money(pf.mean)}</span>`+
          `<div class="kv" style="margin-top:6px">profit band ${money(pf.low)} to ${money(pf.high)} &middot; RAROC ${d.raroc!=null?(d.raroc*100).toFixed(1)+'%':'n/a'} &middot; book ${money(d.book_exposure)}</div>`+
          `<span class="pill">loss = advances ${money(el.advances)} + chargebacks ${money(el.chargebacks)}</span>`+
          `<span class="pill ${d.fund_covers_provision?'good':'bad'}">provision ${money(d.provision_needed)} ${d.fund_covers_provision?'covered':'short'}</span>`+
          `<div class="kv" style="margin-top:8px">advance book <span class="muted">(${esc(d.book_source||'')})</span>:</div>${rows}`+
          `<div class="kv muted" style="margin-top:6px">${esc(d.method)}</div>`); }; } },

  { id:'grounding', label:'Agent grounding', html:`
      <p class="muted" style="margin:0 0 6px">The agents are not bare LLMs. Before they decide, they retrieve the relevant financial principles from a curated knowledge base (also served over MCP), so the reasoning is financially literate, not generic. Ask what the agent is about to do.</p>
      <label>a decision the agent faces</label>
      <textarea id="kn-q">how much should we lend to a creator whose income is volatile</textarea>
      <button class="btn" id="kn-run">Retrieve grounding</button>
      <div class="result" id="kn-out"></div>`,
    wire(){ const b=document.getElementById('kn-run'), o=document.getElementById('kn-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/knowledge',{query:document.getElementById('kn-q').value, k:4});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        const rows=d.principles.map(p=>`<div class="kv" style="margin-bottom:6px"><span class="pill good">${esc(p.topic)}</span> ${esc(p.statement)} <span class="muted">(${esc(p.source)})</span></div>`).join('');
        show(o, `<div class="kv">retrieved ${d.principles.length} of ${d.available_topics.length} principles the agent will apply <span class="muted">via ${esc(d.retrieval||'')}</span>:</div>${rows}`); }; } },

  { id:'audit', label:'Audit & reconcile', html:`
      <p class="muted" style="margin:0 0 6px">Every money action is chained into a tamper-evident receipt, and nothing is reported as done until the processor's own record agrees. Try to alter a settled receipt, or inject a discrepancy, and watch it get caught.</p>
      <label>Hash-chained receipts</label>
      <div class="chk"><input type="checkbox" id="rc-tamper"><label for="rc-tamper" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">tamper: edit a captured amount after the fact</label></div>
      <button class="btn" id="rc-run">Build and verify the chain</button>
      <div class="result" id="rc-out"></div>
      <label style="margin-top:16px">Reconcile against PayPal's record</label>
      <div class="chk"><input type="checkbox" id="rec-inj"><label for="rec-inj" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">inject a discrepancy (mismatch, duplicate, unexpected, missing)</label></div>
      <button class="btn" id="rec-run">Reconcile</button>
      <div class="result" id="rec-out"></div>
      <label style="margin-top:16px">Outbound screening (AML)</label>
      <p class="muted" style="margin:0 0 6px">Every payout is screened for sanctions, structuring, velocity and duplicates before it moves.</p>
      <button class="btn" id="cm-run">Screen a batch of payouts</button>
      <div class="result" id="cm-out"></div>`,
    wire(){ const b=document.getElementById('rc-run'), o=document.getElementById('rc-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/receipts/demo',{tamper:document.getElementById('rc-tamper').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body; const v=d.verification;
        const rows=d.receipts.map(x=>`<div class="kv"><span class="pill">#${x.seq}</span> <b>${esc(x.action)}</b> <span class="pill">${esc(x.ref)}</span> ${money(x.amount)} <span class="muted">hash ${esc(x.hash)}…</span></div>`).join('');
        const verdict = v.intact ? '<span class="verdict ok">chain intact</span>'
          : `<span class="verdict no">tamper detected at #${v.broken_at}</span>`;
        show(o, verdict+`<div style="margin-top:6px">${rows}</div>`+`<div class="kv muted" style="margin-top:4px">${esc(v.reason||('head '+(v.head||'').slice(0,16)))}</div>`); };
      const g=document.getElementById('rec-run'), go=document.getElementById('rec-out');
      g.onclick = async () => { busy(g,true);
        const r=await post('/api/reconcile/demo',{inject_discrepancy:document.getElementById('rec-inj').checked});
        busy(g,false); if(r.status!==200) return err(go,r); const d=r.body;
        const verdict = d.clean ? `<span class="verdict ok">reconciled, ${d.matched_count} matched (${money(d.matched_value)})</span>`
          : `<span class="verdict no">${d.discrepancy_count} discrepancies</span>`;
        const rows=(d.discrepancies||[]).map(x=>`<div class="kv"><span class="pill bad">${esc(x.type)}</span> <span class="pill">${esc(x.ref)}</span> <span class="muted">${esc(x.detail)}</span></div>`).join('');
        show(go, verdict+`<div style="margin-top:6px">${rows}</div>`); };
      const c=document.getElementById('cm-run'), co=document.getElementById('cm-out');
      c.onclick = async () => { busy(c,true); const r=await get('/api/compliance/demo'); busy(c,false);
        if(r.status!==200) return err(co,r);
        const rows=r.body.results.map(x=>{ const cls=x.decision==='allow'?'ok':(x.decision==='hold'?'hold':'no');
          return `<div class="kv"><span class="verdict ${cls}">${esc(x.decision)}</span> <b>${esc(x.payee)}</b> ${money(x.amount)} <span class="muted">${esc(x.reasons.join('; '))}</span></div>`; }).join('');
        show(co, rows); }; } },

  { id:'x402', label:'x402 micropayment', html:`
      <p class="muted" style="margin:0 0 6px">Pay-per-request the x402 way: the server answers an unpaid request with HTTP 402 and its price, the agent pays the exact amount, and the resource unlocks. Settled on PayPal. A tampered amount is refused.</p>
      <div class="live-row"><div><label>resource</label><input id="x4-res" value="premium-signal"></div>
        <div style="flex:0 0 120px"><label>price</label><input id="x4-amt" type="number" step="0.01" value="0.25"></div></div>
      <div class="chk"><input type="checkbox" id="x4-pay" checked><label for="x4-pay" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">pay (uncheck to see the raw 402 challenge)</label></div>
      <div class="chk"><input type="checkbox" id="x4-tamper"><label for="x4-tamper" style="margin:0;text-transform:none;letter-spacing:0;font-size:12.5px">tamper: pay 10x the agreed amount</label></div>
      <button class="btn" id="x4-run">Request the resource</button>
      <div class="result" id="x4-out"></div>`,
    wire(){ const b=document.getElementById('x4-run'), o=document.getElementById('x4-out');
      b.onclick = async () => { busy(b,true);
        const r=await post('/api/x402/demo',{resource:document.getElementById('x4-res').value,
          amount:+document.getElementById('x4-amt').value, pay:document.getElementById('x4-pay').checked,
          tamper:document.getElementById('x4-tamper').checked});
        busy(b,false); if(r.status!==200) return err(o,r); const d=r.body;
        if(d.status===402 && !d.granted && d.requirements){ const opt=d.requirements.accepts[0];
          return show(o, `<span class="verdict hold">HTTP 402 Payment Required</span><div class="kv" style="margin-top:6px">${esc(d.note||'')}</div>`+
            `<span class="pill">${esc(opt.scheme)}</span><span class="pill">${money(opt.maxAmountRequired)} ${esc(opt.currency)}</span>`+
            `<span class="pill">payTo ${esc(opt.payTo)}</span><span class="pill">${esc(opt.network)}</span>`); }
        if(!d.granted) return show(o, `<span class="verdict no">payment refused</span> <span class="muted">${esc(d.reason)}</span>`);
        show(o, `<span class="verdict ok">200 OK, resource unlocked</span><span class="pill">${esc(d.resource)}</span>`+
          `<span class="pill">paid ${money(d.payment_response.amount)}</span><span class="pill">via ${esc(d.backend)}</span>`+
          `<span class="pill">${esc(d.payment_response.settled)}</span>`); }; } },

  { id:'graphfraud', label:'Fraud graph', html:`
      <p class="muted" style="margin:0 0 6px">The linkage engine finds rings from shared signals; this adds the graph lens. An organic group is sparse; a ring run by one actor is near a clique (almost everyone links to everyone). Higher edge density is stronger structural evidence of a single actor.</p>
      <button class="btn" id="gf-run">Score the inferred rings</button>
      <div class="result" id="gf-out"></div>
      <label style="margin-top:16px">In a graph database (Kùzu, embedded)</label>
      <p class="muted" style="margin:0 0 6px">The marketplace is loaded as a property graph (accounts and the device, card and IP nodes they share) into an embedded graph database, then rings are found by <b>multi-hop Cypher traversal</b>. This catches rings whose members share <b>no single identifier</b> but are chained across several (a device links A&ndash;B, a card links B&ndash;C, an IP links C&ndash;D), which is invisible to a pairwise or GROUP BY check, native to a graph.</p>
      <button class="btn" id="fg-run">Detect rings by graph traversal</button>
      <div class="result" id="fg-out"></div>`,
    wire(){ const b=document.getElementById('gf-run'), o=document.getElementById('gf-out');
      b.onclick = async () => { busy(b,true); const r=await get('/api/graphfraud/demo'); busy(b,false);
        if(r.status!==200) return err(o,r); const d=r.body;
        const rows=d.rings.map(x=>`<div class="kv" style="margin-bottom:6px"><span class="verdict ${x.near_clique?'no':'hold'}">${x.near_clique?'near-clique':'cluster'}</span> `+
          `<span class="pill">${x.members} members</span><span class="pill">density ${pct(x.density)}</span>`+
          `<span class="pill">mean link ${pct(x.mean_link_prob)}</span><span class="pill bad">structural risk ${pct(x.structural_risk)}</span> `+
          `<span class="muted">${esc(x.interpretation)}</span></div>`).join('');
        show(o, `<div class="kv">${d.count} inferred rings scored by graph structure:</div>${rows}`); };
      const g=document.getElementById('fg-run'), go=document.getElementById('fg-out');
      g.onclick = async () => { busy(g,true); const r=await get('/api/fraud/graph'); busy(g,false);
        if(r.status!==200) return err(go,r); const d=r.body;
        const rows=(d.rings||[]).map(x=>`<div class="kv" style="margin-bottom:6px"><span class="verdict ${x.multi_hop?'no':'hold'}">${x.multi_hop?'multi-hop ring':'ring'}</span> `+
          `<span class="pill">${x.size} members</span><span class="pill">${esc((x.kinds||[]).join(' + '))}</span>`+
          `<span class="pill">${x.hops} hops</span><span class="pill bad">risk ${pct(x.risk)}</span> `+
          `<span class="muted">${esc(x.reason)}</span></div>`).join('');
        show(go, `<div class="kv">engine <b>${esc(d.engine)}</b> &middot; ${d.accounts} accounts &middot; ${d.count} rings, <b>${d.multi_hop_rings}</b> chained across several identifiers:</div>${rows}`); }; } },
  ];

  const lanesEl=document.getElementById('liveLanes'), tabsEl=document.getElementById('liveTabs'), bodyEl=document.getElementById('liveBody');
  if(!tabsEl) return;
  // Three sides, one account: group the capabilities into coherent lanes.
  const LANES=[
    {label:'Earn', sub:'you are a seller', ids:['creator','policy','signal','advance','rladvance','tax','invest']},
    {label:'Spend', sub:'you are a buyer', ids:['shop','buyer','negotiate','mandate','identity','pool','escrow','x402']},
    {label:'Platform', sub:'it runs & proves the money', ids:['market','operator','pnl','grounding','verify','reserves','graphfraud','audit']},
  ];
  const byId=Object.fromEntries(TOOLS.map((t,i)=>[t.id,i]));
  function openTool(id){ [...tabsEl.children].forEach(t=>t.classList.toggle('on', t.dataset.id===id));
    const i=byId[id]; bodyEl.innerHTML = `<div class="live-tool">${TOOLS[i].html}</div>`; TOOLS[i].wire(); }
  function renderLane(li){ [...lanesEl.children].forEach((e,j)=>e.classList.toggle('on', j===li));
    const ids=LANES[li].ids.filter(id=>id in byId);
    tabsEl.innerHTML = ids.map((id,k)=>`<div class="tab${k===0?' on':''}" data-id="${id}">${TOOLS[byId[id]].label}</div>`).join('');
    if(ids.length) openTool(ids[0]); }
  lanesEl.innerHTML = LANES.map((L,j)=>`<div class="lane${j===0?' on':''}" data-l="${j}">${L.label}<span class="sub">${L.sub}</span></div>`).join('');
  lanesEl.addEventListener('click', e=>{ const t=e.target.closest('.lane'); if(t) renderLane(+t.dataset.l); });
  tabsEl.addEventListener('click', e=>{ const t=e.target.closest('.tab'); if(t) openTool(t.dataset.id); });
  // if the page is a static file with no backend, show the offline note instead
  if(location.protocol==='file:'){ document.getElementById('liveOffline').style.display=''; lanesEl.style.display='none'; tabsEl.style.display='none'; }
  else renderLane(0);
  document.querySelectorAll('[data-go]').forEach(btn=>btn.addEventListener('click',()=>{
    const [li,id]=btn.dataset.go.split(':'); renderLane(+li); openTool(id);
    document.getElementById('live').scrollIntoView({behavior:'smooth', block:'start'});
    const run=bodyEl.querySelector('.btn'); if(run) setTimeout(()=>run.click(), 350); }));
  if(location.protocol==='file:') document.getElementById('start').style.display='none';
})();
</script>
</body>
</html>
"""


def render_page(embedded_data: dict | None = None) -> str:
    html = _TEMPLATE.replace("__CHART_JS__", CHART_JS).replace("__WORLD_SVG__", _WORLD_SVG)
    if embedded_data is not None:
        inject = f"<script>window.HELM_DATA={json.dumps(embedded_data)};</script>"
        html = html.replace("</head>", inject + "\n</head>")
    return html
