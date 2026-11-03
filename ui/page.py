"""The single dashboard screen: Helm's agent running a creator-marketplace treasury.

One HTML string, no build step. Reads embedded `window.HELM_DATA` (static build)
or fetches `/api/data` (live server). Charts are Chart.js from a CDN.
"""
from __future__ import annotations

import json

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helm Money-Out Operator</title>
<script src="__CHART_JS__"></script>
<style>
  :root {
    --bg:#0b0f14; --panel:#131a23; --line:#223042; --ink:#e7eef7; --muted:#8aa0b6;
    --accent:#4ea1ff; --good:#36d399; --warn:#f6c343; --bad:#f06868; --target:#9aa7b5;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
  header { padding:24px 16px 8px; max-width:1180px; margin:0 auto; }
  h1 { margin:0 0 4px; font-size:26px; letter-spacing:.2px; }
  .sub { color:var(--muted); font-size:14px; }
  main { max-width:1180px; margin:0 auto; padding:16px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:16px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
  .card .k { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.6px; }
  .card .v { font-size:24px; font-weight:650; margin-top:4px; }
  .card .v.good { color:var(--good); } .card .v.accent { color:var(--accent); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media (max-width:820px){ .grid { grid-template-columns:1fr; } }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; margin-bottom:16px; }
  .panel h2 { margin:0 0 2px; font-size:15px; }
  .panel p { margin:0 0 12px; color:var(--muted); font-size:13px; }
  canvas { max-height:250px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th,td { text-align:right; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; } td.l,th.l { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
  .tag { display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px; }
  .tag.good { background:rgba(54,211,153,.15); color:var(--good); }
  .tag.hold { background:rgba(246,195,67,.15); color:var(--warn); }
  .tag.sig { background:rgba(240,104,104,.15); color:var(--bad); }
  .foot { color:var(--muted); font-size:12px; padding:8px 16px 32px; max-width:1180px; margin:0 auto; }
</style>
</head>
<body>
<header>
  <h1>Helm &mdash; money-out operator</h1>
  <div class="sub">An AI agent runs a creator platform's payouts: each cycle it forecasts, reads the signal, chooses a risk posture, and decides which creators to pay and which to hold, on PayPal. The solver sizes the safe release; guardrails clamp the agent. Every number below is produced by the running system.</div>
</header>
<main>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>The agent forecasts, and stays solvent through the swing</h2>
    <p>The ETS forecast tracks a viral spike and collapse with an uncertainty band; cash is held above the floor-plus-reserve line throughout.</p>
    <div class="grid">
      <div><canvas id="gmvChart"></canvas></div>
      <div><canvas id="cashChart"></canvas></div>
    </div>
  </div>

  <div class="grid">
    <div class="panel"><h2>The agent's risk posture</h2><p>How conservative the agent chose to be each cycle. It raises the reserve when a fraud signal lands.</p><canvas id="riskChart"></canvas></div>
    <div class="panel"><h2>Payout frontier: reserve shortfall</h2><p>Dollars under-reserved against chargebacks. Helm versus the naive extremes.</p><canvas id="frontierChart"></canvas></div>
  </div>

  <div class="panel">
    <h2>The agent's decision journal</h2>
    <p>Per cycle: the forecast, the risk posture it chose, the safe release the solver sized, who it paid, who it held, and any guardrail that clamped it. This is the AI steering, bounded.</p>
    <div style="overflow-x:auto"><table id="journal"></table></div>
  </div>

  <div class="panel">
    <h2>Payout engine: cheating earns nothing</h2>
    <p>A Sybil creator inflates the naive split; hardening collapses it to the honest share. Global creators are withheld at treaty rates (Tollgate), batches settle atomically (Keystone).</p>
    <canvas id="bulwarkChart"></canvas>
  </div>
</main>
<div class="foot" id="foot"></div>

<script>
(async function(){
  const data = window.HELM_DATA || await (await fetch('/api/data')).json();
  const css = getComputedStyle(document.documentElement);
  const C = n => css.getPropertyValue(n).trim();
  Chart.defaults.color = C('--muted'); Chart.defaults.borderColor = C('--line');
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  const money = v => '$' + Number(v).toLocaleString(undefined,{maximumFractionDigits:0});

  const h = data.headline, ctx = data.context;
  const cards = [
    ['paid to creators', money(h.creators_paid_total), 'accent'],
    ['cycles run by the agent', String(h.cycles), ''],
    ['raised caution on a signal', h.caution_raised + 'x', h.caution_raised? 'good':''],
    ['recoupment engaged', h.recoupment_used? 'yes':'not needed', ''],
  ];
  document.getElementById('cards').innerHTML = cards.map(c =>
    `<div class="card"><div class="k">${c[0]}</div><div class="v ${c[2]||''}">${c[1]}</div></div>`).join('');

  const line = (id, labels, sets) => new Chart(document.getElementById(id), {
    type:'line', data:{labels, datasets:sets},
    options:{responsive:true, interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{boxWidth:12}}}, elements:{point:{radius:0}},
      scales:{x:{grid:{display:false}}}}});
  const bar = (id, labels, values, colors) => new Chart(document.getElementById(id), {
    type:'bar', data:{labels, datasets:[{data:values, backgroundColor:colors, borderRadius:6}]},
    options:{responsive:true, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}}}});

  const g = data.gmv;
  line('gmvChart', g.periods, [
    {label:'forecast band', data:g.upper, borderColor:'transparent', backgroundColor:'rgba(78,161,255,.12)', fill:'+1'},
    {label:'_lower', data:g.lower, borderColor:'transparent', backgroundColor:'transparent', fill:false},
    {label:'forecast (ETS)', data:g.forecast, borderColor:C('--accent'), borderDash:[6,4]},
    {label:'actual GMV', data:g.actual, borderColor:C('--warn'), borderWidth:2},
  ]);
  const cf = data.cashflow;
  line('cashChart', cf.periods, [
    {label:'cash', data:cf.cash, borderColor:C('--good'), backgroundColor:'rgba(54,211,153,.08)', fill:true},
    {label:'floor + reserve', data:cf.floor_plus_reserve, borderColor:C('--bad'), borderDash:[4,4]},
  ]);
  const rk = data.risk;
  new Chart(document.getElementById('riskChart'), {type:'bar',
    data:{labels:rk.periods, datasets:[{label:'risk multiplier', data:rk.risk_multiplier,
      backgroundColor:rk.periods.map(p=>p===rk.signal_cycle?C('--bad'):C('--target')), borderRadius:5}]},
    options:{responsive:true, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}, y:{suggestedMin:1}}}});
  const fr = data.frontier;
  bar('frontierChart', ['pay everyone','monthly','Helm'],
    [fr.pay_all.reserve_shortfall, fr.monthly.reserve_shortfall, fr.helm.reserve_shortfall],
    [C('--bad'), C('--target'), C('--good')]);
  const bw = data.payout_engine.bulwark;
  bar('bulwarkChart', ['naive take','hardened take','honest share'],
    [bw.naive_cheater_take, bw.hardened_cheater_take, bw.honest_share],
    [C('--bad'), C('--good'), C('--target')]);

  const head = ['Cycle','Forecast','Risk x','Safe release','Paid','Held','PayPal batch','Guardrail'];
  const rows = data.journal.map(j => {
    const paid = j.paid.map(p=>`${p.creator} ${money(p.amount)}`).join(', ') || '&mdash;';
    const held = (j.held||[]).join(', ') || '&mdash;';
    const sig = j.signal ? ' <span class="tag sig">signal</span>' : '';
    const gr = (j.overrides&&j.overrides.length)? `<span class="tag hold">${j.overrides.length}</span>` : '&mdash;';
    const fc = j.forecast!=null ? money(j.forecast)+' &plusmn;'+Math.round(j.sigma||0) : '&mdash;';
    return `<tr><td>wk${j.period}${sig}</td><td>${fc}</td><td>${j.risk_multiplier}</td>
      <td>${money(j.safe_release)}</td><td class="l">${paid}</td><td class="l">${held}</td>
      <td>${j.batch_id||'&mdash;'}</td><td>${gr}</td></tr>`;
  }).join('');
  document.getElementById('journal').innerHTML =
    '<thead><tr>'+head.map((x,i)=>`<th class="${i>=4&&i<=5?'l':''}">${x}</th>`).join('')+'</tr></thead><tbody>'+rows+'</tbody>';

  const pe = data.payout_engine, tg = pe.tollgate, ks = pe.keystone;
  document.getElementById('foot').innerHTML =
    `Context: a ~$${ctx.market_size_b}B creator economy, ~${ctx.creators_m}M creators, up to ${ctx.late_pct}% paid late. `+
    `Bulwark hardening: ${bw.hardening_applied.join(', ')||'none needed'} (cheat defeated: ${bw.defeated}). `+
    `Clearwright legal: ${pe.clearwright_ok}. Tollgate withheld ${money(tg.withheld)} of ${money(tg.gross)}. `+
    `Keystone ${ks.status}, conserved ${ks.conserved}.`;
})();
</script>
</body>
</html>
"""


def render_page(embedded_data: dict | None = None) -> str:
    html = _TEMPLATE.replace("__CHART_JS__", CHART_JS)
    if embedded_data is not None:
        inject = f"<script>window.HELM_DATA={json.dumps(embedded_data)};</script>"
        html = html.replace("</head>", inject + "\n</head>")
    return html
