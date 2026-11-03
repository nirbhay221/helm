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
<link rel="stylesheet" href="__VMAP_CSS__">
<script src="__CHART_JS__"></script>
<script src="__VMAP_JS__"></script>
<script src="__VMAP_WORLD__"></script>
<style>
  :root {
    --bg:#0b0f14; --panel:#131a23; --panel2:#182230; --line:#223042; --ink:#e7eef7;
    --muted:#8aa0b6; --accent:#4ea1ff; --good:#36d399; --warn:#f6c343; --bad:#f06868; --target:#9aa7b5;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
  header { padding:24px 16px 4px; max-width:1200px; margin:0 auto; }
  h1 { margin:0 0 4px; font-size:26px; letter-spacing:.2px; }
  .sub { color:var(--muted); font-size:14px; }
  main { max-width:1200px; margin:0 auto; padding:16px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:16px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
  .card .k { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.6px; }
  .card .v { font-size:23px; font-weight:650; margin-top:4px; } .card .v.accent{color:var(--accent);} .card .v.good{color:var(--good);}
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; margin-bottom:16px; }
  .panel h2 { margin:0 0 2px; font-size:15px; } .panel p { margin:0 0 12px; color:var(--muted); font-size:13px; }
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
  #worldmap { height:340px; } .mapwrap { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:8px; }
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
  <h1>Helm &mdash; global payout operator</h1>
  <div class="sub">An AI agent runs payouts for a creator platform with thousands of creators across the world. You write the treasury policy in plain English; the agent compiles it into objective weights and hard constraints; a solver allocates the cycle budget across everyone, net of each country's tax and FX; guardrails clamp it.</div>
</header>
<main>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>Write a policy, the agent runs it</h2>
    <p>Each tab is a treasury policy stated in English. The agent compiled it with the live model; the allocation below obeys it.</p>
    <div class="tabs" id="tabs"></div>
    <div class="policy" id="policy"></div>
    <div id="pills"></div>
  </div>

  <div class="grid2">
    <div class="mapwrap"><div id="worldmap" role="img" aria-label="payouts by country"></div></div>
    <div class="panel" style="margin:0"><h2>Where the money goes</h2><p>Payout by country for this policy.</p><div style="overflow-x:auto;max-height:300px"><table id="countries"></table></div></div>
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

  // world map (guarded)
  let map=null;
  if (window.jsVectorMap){ try {
    map = new jsVectorMap({ selector:'#worldmap', map:'world', zoomButtons:false,
      backgroundColor:'transparent',
      regionStyle:{ initial:{ fill:C('--line') }, hover:{ fill:C('--accent') } },
      series:{ regions:[{ attribute:'fill', scale:['#17304a', C('--accent')],
        normalizeFunction:'polynomial', values:{} }] } });
  } catch(e){ map=null; } }
  const setMap = vals => { if(map&&map.series&&map.series.regions[0]){ try{ map.series.regions[0].setValues(vals);}catch(e){} } };

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
    const vals={}; Object.entries(s.by_country).forEach(([k,v])=>vals[k]=v.amount);
    setMap(vals);
    const rows=Object.entries(s.by_country).sort((a,b)=>b[1].amount-a[1].amount)
      .map(([k,v])=>`<tr><td>${k}</td><td>${money(v.amount)}</td><td>${v.count}</td></tr>`).join('');
    document.getElementById('countries').innerHTML =
      '<thead><tr><th>Country</th><th>Paid</th><th>Creators</th></tr></thead><tbody>'+rows+'</tbody>';
  }
  tabsEl.addEventListener('click', e=>{ const t=e.target.closest('.tab'); if(t) show(+t.dataset.i); });
  show(0);
  let i=0; setInterval(()=>{ i=(i+1)%S.length; show(i); }, 3500);   // auto-tour the policies

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
