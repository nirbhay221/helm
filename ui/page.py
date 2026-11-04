"""The dashboard screen: Helm's agent compiling policies and paying creators worldwide.

One self-contained HTML string, no build step. Reads embedded `window.HELM_DATA`
(static build) or fetches `/api/data`. A world choropleth, a policy switcher that
shows the agent compiling each written policy into weights and hard constraints,
KPI cards, and per-country rollups. Chart.js and jsVectorMap from CDNs, both
guarded so the page still renders if a CDN is unavailable.
"""
from __future__ import annotations

import json

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
VMAP_CSS = "https://cdn.jsdelivr.net/npm/jsvectormap@1.5.3/dist/css/jsvectormap.min.css"
VMAP_JS = "https://cdn.jsdelivr.net/npm/jsvectormap@1.5.3/dist/jsvectormap.min.js"
VMAP_WORLD = "https://cdn.jsdelivr.net/npm/jsvectormap@1.5.3/dist/maps/world.js"

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
    --bg:#0b0f14; --panel:#131a23; --panel2:#182230; --line:#223042; --ink:#e7eef7;
    --muted:#8aa0b6; --accent:#4ea1ff; --good:#36d399; --warn:#f6c343; --bad:#f06868; --target:#9aa7b5;
  }
  * { box-sizing:border-box; }
  body { margin:0; color:var(--ink); font-family:'Inter',-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
    background:radial-gradient(1200px 500px at 20% -10%, rgba(78,161,255,.10), transparent 60%), var(--bg); }
  header { padding:28px 16px 6px; max-width:1200px; margin:0 auto; }
  .brand { display:flex; align-items:center; gap:11px; }
  .brand svg { flex:0 0 auto; }
  h1 { margin:0; font-size:26px; font-weight:800; letter-spacing:-.4px; }
  .badge { color:var(--accent); font-size:12px; font-weight:600; letter-spacing:.3px;
    border:1px solid rgba(78,161,255,.35); background:rgba(78,161,255,.08); border-radius:999px; padding:4px 11px; }
  .sub { color:var(--muted); font-size:14px; margin-top:8px; max-width:900px; }
  main { max-width:1200px; margin:0 auto; padding:16px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:16px; }
  .card { background:linear-gradient(180deg,var(--panel2),var(--panel)); border:1px solid var(--line);
    border-radius:14px; padding:15px 17px; }
  .card .k { color:var(--muted); font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:.7px; }
  .card .v { font-size:25px; font-weight:700; letter-spacing:-.5px; margin-top:5px; } .card .v.accent{color:var(--accent);} .card .v.good{color:var(--good);}
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  .panel h2 { margin:0 0 3px; font-size:15.5px; font-weight:700; letter-spacing:-.2px; } .panel p { margin:0 0 13px; color:var(--muted); font-size:13px; }
  tbody tr:hover { background:rgba(78,161,255,.05); }
  .grid2 { display:grid; grid-template-columns:1.3fr 1fr; gap:16px; } @media (max-width:900px){ .grid2{grid-template-columns:1fr;} }
  .grid3 { display:grid; grid-template-columns:1fr 1fr; gap:16px; } @media (max-width:820px){ .grid3{grid-template-columns:1fr;} }
  .tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
  .tab { background:var(--panel2); color:var(--muted); border:1px solid var(--line); border-radius:999px;
    padding:7px 14px; font-size:13px; font-weight:600; cursor:pointer; }
  .tab.on { background:var(--accent); color:#06121f; border-color:var(--accent); }
  .policy { background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:12px 14px; margin-bottom:12px; }
  .policy .q { color:var(--ink); font-style:italic; } .policy .c { color:var(--muted); font-size:13px; margin-top:6px; }
  .pill { display:inline-block; background:#0e1a27; border:1px solid var(--line); border-radius:7px; padding:2px 8px; margin:2px 4px 2px 0; font-size:12px; }
  .pill b { color:var(--accent); } .pill.bad b{ color:var(--bad);} .pill.good b{color:var(--good);}
  canvas { max-height:240px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th,td { text-align:right; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
  .foot { color:var(--muted); font-size:12px; padding:8px 16px 32px; max-width:1200px; margin:0 auto; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#4ea1ff" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.4" fill="#4ea1ff" stroke="none"/>
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
    <div class="panel" style="margin:0"><h2>Payouts by country</h2><p>How this policy spreads the cycle budget across the world.</p><canvas id="countryChart" style="max-height:320px"></canvas></div>
    <div class="panel" style="margin:0"><h2>Where the money goes</h2><p>Payout and creators paid per country, this policy.</p><div style="overflow-x:auto;max-height:300px"><table id="countries"></table></div></div>
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
  if (window.Chart){ Chart.defaults.color=C('--muted'); Chart.defaults.borderColor=C('--line');
    Chart.defaults.font.family=getComputedStyle(document.body).fontFamily; }

  const h=data.headline, S=data.scenarios, ctx=data.context;
  document.getElementById('cards').innerHTML = [
    ['creators', Number(h.creators).toLocaleString(), ''],
    ['owed to creators', money(h.total_owed), 'accent'],
    ['this cycle budget', money(h.budget), ''],
    ['countries', String(h.countries), ''],
    ['policies the agent ran', String(S.length), 'good'],
  ].map(c=>`<div class="card"><div class="k">${c[0]}</div><div class="v ${c[2]||''}">${c[1]}</div></div>`).join('');

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

  // payouts by country bar chart (reliable; replaces the vector map)
  let countryCh=null;
  if (window.Chart){ countryCh = new Chart(document.getElementById('countryChart'), {
    type:'bar', data:{labels:[], datasets:[{data:[], backgroundColor:C('--accent'), borderRadius:5}]},
    options:{ indexAxis:'y', responsive:true, animation:false, plugins:{legend:{display:false}},
      scales:{ x:{grid:{color:'rgba(34,48,66,.6)'}, ticks:{callback:v=>'$'+Math.round(v/1000)+'k'}},
               y:{grid:{display:false}} } } }); }
  const setCountryChart = byCountry => {
    if(!countryCh) return;
    const rows=Object.entries(byCountry).sort((a,b)=>b[1].amount-a[1].amount);
    countryCh.data.labels=rows.map(r=>r[0]);
    countryCh.data.datasets[0].data=rows.map(r=>r[1].amount);
    countryCh.update('none');
  };

  // scenario comparison: risk exposure per policy
  if (window.Chart){ new Chart(document.getElementById('riskChart'), { type:'bar',
    data:{ labels:S.map(s=>s.label), datasets:[{ data:S.map(s=>s.risk_exposure),
      backgroundColor:S.map(s=>s.label.toLowerCase().includes('fraud')?C('--good'):C('--target')), borderRadius:6 }]},
    options:{ responsive:true, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}}}}); }
  const bw=data.payout_engine.bulwark;
  if (window.Chart){ new Chart(document.getElementById('bulwarkChart'), { type:'bar',
    data:{ labels:['naive take','hardened','honest share'], datasets:[{ data:[bw.naive_cheater_take,bw.hardened_cheater_take,bw.honest_share],
      backgroundColor:[C('--bad'),C('--good'),C('--target')], borderRadius:6 }]},
    options:{ responsive:true, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}}}}); }

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
    setCountryChart(s.by_country);
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
    if (window.Chart){ new Chart(document.getElementById('navChart'), { type:'line',
      data:{ labels:ri.nav.dates, datasets:[{ label:'pool NAV (rebased to 100)', data:ri.nav.values,
        borderColor:C('--accent'), backgroundColor:'rgba(78,161,255,.08)', fill:true }]},
      options:{ responsive:true, animation:false, elements:{point:{radius:0}},
        plugins:{legend:{labels:{boxWidth:12}}}, scales:{x:{grid:{display:false}, ticks:{maxTicksLimit:6}}}}}); }
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
    `Tollgate withheld ${money(tg.withheld)} of ${money(tg.gross)} for global creators. Keystone ${ks.status}, conserved ${ks.conserved}.`;
})();
</script>
</body>
</html>
"""


def render_page(embedded_data: dict | None = None) -> str:
    html = (_TEMPLATE.replace("__CHART_JS__", CHART_JS).replace("__VMAP_CSS__", VMAP_CSS)
            .replace("__VMAP_JS__", VMAP_JS).replace("__VMAP_WORLD__", VMAP_WORLD))
    if embedded_data is not None:
        inject = f"<script>window.HELM_DATA={json.dumps(embedded_data)};</script>"
        html = html.replace("</head>", inject + "\n</head>")
    return html
