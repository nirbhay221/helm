"""The single dashboard screen: Helm running a creator-marketplace treasury.

One HTML string, no build step. It reads its data from an embedded
`window.HELM_DATA` (static build) or, if absent, fetches `/api/data` (live
server). Charts are Chart.js from a CDN.
"""
from __future__ import annotations

import json

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helm Creator Treasury</title>
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
  .card .v.good { color:var(--good); } .card .v.accent { color:var(--accent); } .card .v.bad { color:var(--bad); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media (max-width:820px){ .grid { grid-template-columns:1fr; } }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; margin-bottom:16px; }
  .panel h2 { margin:0 0 2px; font-size:15px; }
  .panel p { margin:0 0 12px; color:var(--muted); font-size:13px; }
  canvas { max-height:260px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:right; padding:7px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
  .tag { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }
  .tag.good { background:rgba(54,211,153,.15); color:var(--good); }
  .tag.hold { background:rgba(246,195,67,.15); color:var(--warn); }
  .foot { color:var(--muted); font-size:12px; padding:8px 16px 32px; max-width:1180px; margin:0 auto; }
</style>
</head>
<body>
<header>
  <h1>Helm &mdash; creator marketplace treasury</h1>
  <div class="sub">A platform collects buyer money, owes creators their earnings, and must stay reserved against chargebacks. Helm decides what to pay each creator and when, and moves it on PayPal. Every number below is produced by the running system.</div>
</header>
<main>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>The money shot: revenue variance opens, the controller stays solvent</h2>
    <p>A viral spike pushes actual GMV far above the flat plan, then it collapses as the spike's chargebacks land. Helm keeps cash above the floor-plus-reserve line throughout.</p>
    <div class="grid">
      <div><canvas id="gmvChart"></canvas></div>
      <div><canvas id="cashChart"></canvas></div>
    </div>
  </div>

  <div class="grid">
    <div class="panel"><h2>Creators get paid fast</h2><p>Periods the oldest unpaid creator balance has waited, under Helm.</p><canvas id="waitChart"></canvas></div>
    <div class="panel"><h2>The payout frontier: reserve shortfall</h2><p>Total dollars under-reserved against chargebacks. Paying everyone immediately is reckless; Helm carries a fraction of it.</p><canvas id="frontierChart"></canvas></div>
  </div>

  <div class="panel">
    <h2>Payout engine: cheating earns nothing</h2>
    <p>A Sybil creator inflates the naive split; hardening collapses it to the honest share. Global creators are withheld at treaty rates (Tollgate) and the batch settles atomically (Keystone).</p>
    <canvas id="bulwarkChart"></canvas>
  </div>

  <div class="panel">
    <h2>Payout batches to creators (PayPal Payouts)</h2>
    <p>What Helm paid each creator per cycle, the PayPal batch id, and whether the human-approval gate held a large batch.</p>
    <div style="overflow-x:auto"><table id="runs"></table></div>
  </div>
</main>
<div class="foot" id="foot"></div>

<script>
(async function(){
  const data = window.HELM_DATA || await (await fetch('/api/data')).json();
  const css = getComputedStyle(document.documentElement);
  const C = n => css.getPropertyValue(n).trim();
  Chart.defaults.color = C('--muted');
  Chart.defaults.borderColor = C('--line');
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  const money = v => '$' + Number(v).toLocaleString(undefined,{maximumFractionDigits:0});

  const h = data.headline, ctx = data.context;
  const cut = Math.round(100*(1 - h.shortfall_helm/Math.max(1,h.shortfall_pay_all)));
  const cards = [
    ['paid to creators', money(h.creators_paid_total), 'accent'],
    ['avg creator wait', h.helm_avg_wait + ' wk', 'good'],
    ['reserve risk cut vs reckless', cut + '%', 'good'],
    ['cash floor breaches', String(h.floor_breaches_helm), h.floor_breaches_helm? 'bad':'good'],
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
    {label:'planned GMV', data:g.forecast, borderColor:C('--target'), borderDash:[6,4]},
    {label:'actual GMV', data:g.actual, borderColor:C('--warn'), backgroundColor:'rgba(246,195,67,.08)', fill:true},
  ]);
  const cf = data.cashflow;
  line('cashChart', cf.periods, [
    {label:'cash', data:cf.cash, borderColor:C('--accent'), backgroundColor:'rgba(78,161,255,.08)', fill:true},
    {label:'floor + reserve', data:cf.floor_plus_reserve, borderColor:C('--bad'), borderDash:[4,4]},
    {label:'owed to creators', data:cf.owed, borderColor:C('--muted')},
  ]);
  line('waitChart', data.creator_wait.periods, [
    {label:'oldest unpaid (weeks)', data:data.creator_wait.oldest_wait, borderColor:C('--good'), borderWidth:2},
  ]);
  const fr = data.frontier;
  bar('frontierChart', ['pay everyone','monthly','Helm'],
    [fr.pay_all.reserve_shortfall, fr.monthly.reserve_shortfall, fr.helm.reserve_shortfall],
    [C('--bad'), C('--target'), C('--good')]);
  const bw = data.payout_engine.bulwark;
  bar('bulwarkChart', ['naive take','hardened take','honest share'],
    [bw.naive_cheater_take, bw.hardened_cheater_take, bw.honest_share],
    [C('--bad'), C('--good'), C('--target')]);

  const rows = data.payout_runs.map(r => {
    const who = r.recipients.map(x=>`${x.creator} ${money(x.amount)}`).join(', ') || '—';
    const held = r.status !== 'completed';
    return `<tr><td>wk${r.period}</td><td style="text-align:left">${who}</td>
      <td>${money(r.total)}</td><td>${r.batch_id||'—'}</td>
      <td><span class="tag ${held?'hold':'good'}">${r.status}</span></td></tr>`;
  }).join('');
  document.getElementById('runs').innerHTML =
    '<thead><tr><th>Cycle</th><th>Creators paid</th><th>Total</th><th>PayPal batch</th><th>Status</th></tr></thead><tbody>'+rows+'</tbody>';

  const pe = data.payout_engine, tg = pe.tollgate, ks = pe.keystone;
  document.getElementById('foot').innerHTML =
    `Context: a ~$${ctx.market_size_b}B creator economy, ~${ctx.creators_m}M creators, up to ${ctx.late_pct}% paid late. `+
    `Bulwark hardening: ${bw.hardening_applied.join(', ')||'none needed'} (cheat defeated: ${bw.defeated}). `+
    `Clearwright legal: ${pe.clearwright_ok}. Tollgate withheld ${money(tg.withheld)} of ${money(tg.gross)} for global creators. `+
    `Keystone ${ks.status}, batch ${ks.batch_id}, conserved ${ks.conserved}.`;
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
