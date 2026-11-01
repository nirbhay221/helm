"""The single dashboard screen: the control journal and the money shots.

One HTML string, no build step. It reads its data from an embedded
`window.HELM_DATA` (static build) or, if absent, fetches `/api/data` (live
server), so the same page works both ways. Charts are Chart.js from a CDN.
"""
from __future__ import annotations

import json

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helm Control Journal</title>
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
  canvas { max-height:260px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:right; padding:7px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th:first-child,td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
  .tag { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }
  .tag.good { background:rgba(54,211,153,.15); color:var(--good); }
  .tag.bad { background:rgba(240,104,104,.15); color:var(--bad); }
  .foot { color:var(--muted); font-size:12px; padding:8px 16px 32px; max-width:1180px; margin:0 auto; }
</style>
</head>
<body>
<header>
  <h1>Helm &mdash; control journal</h1>
  <div class="sub">Forecast variance opens, the controller acts, PayPal moves the money, the gap closes. Every number below is produced by the running system.</div>
</header>
<main>
  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2>The money shot: variance opens, then closes</h2>
    <p>Actual demand is a real recorded weekly sales series (UCI product P263), not synthetic. It surges well above the flat plan, then collapses. Helm restocks on the realized state; inventory holds near target while an uncontrolled business drifts and stocks out.</p>
    <div class="grid">
      <div><canvas id="varianceChart"></canvas></div>
      <div><canvas id="inventoryChart"></canvas></div>
    </div>
  </div>

  <div class="grid">
    <div class="panel"><h2>Cash vs floor</h2><p>Helm spends only cash it holds; the floor is never a soft suggestion.</p><canvas id="cashChart"></canvas></div>
    <div class="panel"><h2>Awardsmith: optimal buy vs naive</h2><p>Cheapest supplier mix under MOQ, capacity and volume discounts.</p><canvas id="awardChart"></canvas></div>
  </div>

  <div class="grid">
    <div class="panel"><h2>Bulwark: cheating earns nothing</h2><p>A Sybil cheat inflates the naive take; hardening collapses it to the honest share.</p><canvas id="bulwarkChart"></canvas></div>
    <div class="panel"><h2>Honest evaluation vs base-stock</h2><p>Across many randomized scenarios. Deviation is the controller's own objective (shown for context); the verifier eliminates cash breaches.</p><canvas id="evalChart"></canvas></div>
  </div>

  <div class="panel">
    <h2>Control journal</h2>
    <p>Per cycle: what the controller targeted, what Awardsmith bought and from whom, the cost, and the resulting state.</p>
    <div style="overflow-x:auto"><table id="journal"></table></div>
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

  // headline cards
  const cd = data.cumulative_deviation;
  const closed = Math.round(100*(1 - cd.helm/cd.uncontrolled));
  const aw = data.awardsmith, bw = data.payout_engine.bulwark, ev = data.evaluation;
  const cards = [
    ['variance closed', closed + '%', 'good'],
    ['Awardsmith saving', aw.savings!=null? money(aw.savings):'n/a', 'accent'],
    ['cheat defeated', bw.defeated? 'yes':'no', bw.defeated?'good':''],
    ['cash breaches (verifier)', ev.cash_breaches.raw_helm + ' → ' + ev.cash_breaches.verified_helm, 'good'],
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

  const v = data.variance;
  line('varianceChart', v.periods, [
    {label:'forecast demand', data:v.forecast_demand, borderColor:C('--target'), borderDash:[6,4]},
    {label:'actual demand', data:v.actual_demand, borderColor:C('--warn'), backgroundColor:'rgba(246,195,67,.08)', fill:true},
  ]);
  const inv = data.inventory;
  line('inventoryChart', inv.periods, [
    {label:'target', data:inv.target, borderColor:C('--target'), borderDash:[6,4]},
    {label:'Helm', data:inv.helm, borderColor:C('--good'), borderWidth:2},
    {label:'uncontrolled', data:inv.uncontrolled, borderColor:C('--bad')},
  ]);
  const cash = data.cash;
  line('cashChart', cash.periods, [
    {label:'Helm cash', data:cash.helm, borderColor:C('--accent'), backgroundColor:'rgba(78,161,255,.08)', fill:true},
    {label:'floor', data:cash.periods.map(()=>cash.floor), borderColor:C('--bad'), borderDash:[4,4]},
  ]);
  bar('awardChart', ['optimal mix','naive single'],
    [aw.optimal_cost, aw.naive_cost], [C('--good'), C('--muted')]);
  bar('bulwarkChart', ['naive take','hardened take','honest share'],
    [bw.naive_cheater_take, bw.hardened_cheater_take, bw.honest_share],
    [C('--bad'), C('--good'), C('--target')]);
  new Chart(document.getElementById('evalChart'), {type:'bar',
    data:{labels:['mean deviation','avg inventory'], datasets:[
      {label:'Helm', data:[ev.deviation.helm, ev.avg_inventory.helm], backgroundColor:C('--good'), borderRadius:6},
      {label:'base-stock', data:[ev.deviation.base_stock, ev.avg_inventory.base_stock], backgroundColor:C('--muted'), borderRadius:6}]},
    options:{responsive:true, scales:{x:{grid:{display:false}}}}});

  // journal table
  const head = ['Cycle','Target','Bought','From','Cost','Inv after','Cash after','Deviation'];
  const rows = data.journal.map(j => {
    const sup = j.suppliers.map(s=>`${s.name} ${s.qty}@${s.price}`).join(', ') || '—';
    return `<tr><td>${j.period}</td><td>${j.order_target}</td><td>${j.ordered_qty}</td>
      <td style="text-align:left">${sup}</td><td>${money(j.order_cost)}</td>
      <td>${j.inventory_after}</td><td>${money(j.cash_after)}</td><td>${j.deviation_after}</td></tr>`;
  }).join('');
  document.getElementById('journal').innerHTML =
    '<thead><tr>'+head.map(h=>`<th>${h}</th>`).join('')+'</tr></thead><tbody>'+rows+'</tbody>';

  const pe = data.payout_engine, ks = pe.keystone, tg = pe.tollgate;
  document.getElementById('foot').innerHTML =
    `Payout engine: Mete split fair by contribution · Bulwark hardening = ${bw.hardening_applied.join(', ')||'none needed'} · `+
    `Clearwright legal: ${pe.clearwright_ok} · Tollgate withheld ${money(tg.withheld)} of ${money(tg.gross)} · `+
    `Keystone ${ks.status}, batch ${ks.batch_id}, conserved ${ks.conserved}. Evaluation over ${ev.n} randomized scenarios.`;
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
