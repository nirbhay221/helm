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
<title>Helm Global Payout Operator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<script src="__CHART_JS__"></script>
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
  .policy { background:rgba(255,255,255,.03); border:1px solid var(--line); border-radius:12px; padding:15px 17px; margin-bottom:14px; }
  .policy .q { color:var(--ink); font-style:italic; font-size:15px; } .policy .c { color:var(--muted); font-size:13px; margin-top:7px; }
  .pill { display:inline-block; background:rgba(255,255,255,.04); border:1px solid var(--line); border-radius:9px;
    padding:4px 10px; margin:3px 5px 3px 0; font-size:12px; color:var(--muted); }
  .pill b { color:var(--ink); font-weight:700; } .pill.bad b{ color:var(--bad);} .pill.good b{color:var(--good);}
  canvas { max-height:250px; }
  .worldmap svg { width:100%; height:auto; display:block; }
  .worldmap path { fill:rgba(255,255,255,.055); stroke:#0a0e14; stroke-width:.3; transition:fill .7s cubic-bezier(.4,0,.2,1); }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th,td { text-align:right; padding:9px 10px; border-bottom:1px solid rgba(255,255,255,.045); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:10.5px; text-transform:uppercase; letter-spacing:.6px; }
  tbody tr:hover { background:rgba(91,157,255,.06); }
  .foot { color:var(--muted); font-size:12px; padding:10px 22px 40px; max-width:1180px; margin:0 auto; line-height:1.6; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#5b9dff" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.4" fill="#5b9dff" stroke="none"/>
      <path d="M12 3v3.6M12 17.4V21M3 12h3.6M17.4 12H21M5.6 5.6l2.5 2.5M15.9 15.9l2.5 2.5M18.4 5.6l-2.5 2.5M8.1 15.9l-2.5 2.5"/>
    </svg>
    <h1>Helm</h1><span class="badge">GLOBAL PAYOUT OPERATOR</span>
  </div>
  <div class="sub">An AI agent runs payouts for a creator platform with thousands of creators across the world. You write the treasury policy in plain English; the agent compiles it into objective weights and hard constraints; a solver allocates the cycle budget across everyone, net of each country's tax and FX; guardrails clamp it.</div>
</header>
<main>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>The creators <span id="dirCount" class="sub"></span></h2>
    <p>Thousands of individual creators across the world, the population the agent pays. Search the sample by name or country.</p>
    <input id="dirSearch" placeholder="search name or country..." style="width:100%;max-width:340px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:8px 10px;margin-bottom:10px;font-size:13px">
    <div style="overflow:auto;max-height:320px"><table id="directory"></table></div>
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
    <div class="panel" style="margin:0"><h2>Where the money goes</h2><p>Payout and creators paid per country, this policy.</p><div style="overflow-x:auto;max-height:340px"><table id="countries"></table></div></div>
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

  // creator directory: scale + individuals
  const dir=data.directory;
  if (dir){
    document.getElementById('dirCount').textContent =
      `(${Number(dir.total).toLocaleString()} total, ${Number(dir.reinvesting_count).toLocaleString()} reinvesting; showing ${dir.sample_size})`;
    const riskTag = r => r>=0.6?'<span style="color:var(--bad)">high</span>'
      : (r>=0.3?'<span style="color:var(--warn)">med</span>':'<span style="color:var(--good)">low</span>');
    const draw = q => {
      q=(q||'').toLowerCase();
      const rows = dir.sample.filter(c=>!q||c.display.toLowerCase().includes(q)||c.country.toLowerCase().includes(q))
        .map(c=>`<tr><td>${c.display}</td><td>${c.country}</td><td>${money(c.owed)}</td><td>${riskTag(c.risk)}</td>`+
          `<td>${c.paid>0?money(c.paid):'&mdash;'}</td><td>${c.reinvesting?money(c.stake):'&mdash;'}</td></tr>`).join('');
      document.getElementById('directory').innerHTML =
        '<thead><tr><th>Creator</th><th>Country</th><th>Owed</th><th>Risk</th><th>Paid this cycle</th><th>Reinvest stake</th></tr></thead><tbody>'+rows+'</tbody>';
    };
    draw('');
    document.getElementById('dirSearch').addEventListener('input', e=>draw(e.target.value));
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
    options:{ responsive:true, plugins:{legend:{display:false}}, scales:SV }}); }
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
    const rows=Object.entries(s.by_country).sort((a,b)=>b[1].amount-a[1].amount)
      .map(([k,v])=>`<tr><td>${k}</td><td>${money(v.amount)}</td><td>${v.count}</td></tr>`).join('');
    document.getElementById('countries').innerHTML =
      '<thead><tr><th>Country</th><th>Paid</th><th>Creators</th></tr></thead><tbody>'+rows+'</tbody>';
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
    `Bulwark cheat defeated: ${bw.defeated}. Clearwright legal: ${pe.clearwright_ok}. `+
    `Tollgate withheld ${money(tg.withheld)} of ${money(tg.gross)} for global creators. Keystone ${ks.status}, conserved ${ks.conserved}. `+
    `World map: simple-world-map (CC BY-SA 3.0).`;
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
