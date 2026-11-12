"""The control room: act as a buyer, a creator or the operator and watch every agent, every dollar
and every guardrail respond live. Served at /live; fed by /api/live/act and /api/live/stream."""

LIVE_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Helm control room</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Ccircle cx='12' cy='12' r='9' fill='none' stroke='%235b9dff' stroke-width='2'/%3E%3Ccircle cx='12' cy='12' r='3' fill='%235b9dff'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/ag-grid/35.3.0/ag-grid-community.min.js"></script>
<script>try{const t=localStorage.getItem("helm-theme");if(t==="dark")document.documentElement.dataset.theme="dark";}catch(e){}</script>
<style>
:root[data-theme=dark]{color-scheme:dark;--bg:#0b0f17;--panel:#131a27;--panel2:#182131;--line:#243045;--line2:#33405a;--ink:#e8ecf3;--ink2:#c4ccd9;--muted:#94a0b4;--dim:#66728a;--accent:#8b95ff;--accentbg:#1f2347;--good:#34d399;--goodbg:#0e2a22;--warn:#fbbf24;--warnbg:#2a2110;--bad:#f87171;--badbg:#2e1618;--pp:#facc15;--ppbg:#2a2410;--buyer:#60a5fa;--creator:#34d399;--operator:#a78bfa;--market:#fb923c;--soft:#1b2436;--edge:#2f3b52;--onaccent:#0b0f17;--badln:#7f1d1d;--goodln:#065f46;--warnln:#78350f;--accentln:#3730a3;--accent2:#aab3ff;--violet:#c4b5fd;--violetbg:#241c3d;--buyerbg:#172554;--buyer2:#93c5fd;--marketbg:#2d1c0f;--market2:#fdba74;--hdr:#182131;--odd:#151d2b;--sh:0 1px 2px rgba(0,0,0,.4),0 1px 3px rgba(0,0,0,.3);--sh2:0 10px 28px rgba(0,0,0,.55),0 2px 6px rgba(0,0,0,.4)}
.themebtn{background:var(--panel);border:1px solid var(--line);color:var(--ink2);border-radius:999px;padding:4px 10px;font-size:12px;font-weight:500;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;cursor:pointer}.themebtn:hover{border-color:var(--accent);color:var(--accent)}
body{transition:background-color .2s,color .2s}

:root{--soft:#f1f5f9;--edge:#d5dce6;--onaccent:#fff;--badln:#fecaca;--goodln:#a7f3d0;--warnln:#fde68a;--accentln:#c7d2fe;--accent2:#4338ca;--violet:#6d28d9;--violetbg:#f5f3ff;--buyerbg:#dbeafe;--buyer2:#1d4ed8;--marketbg:#ffedd5;--market2:#c2410c;--hdr:#ffffff;--odd:#fcfdfe;color-scheme:light;--bg:#f4f6fa;--panel:#ffffff;--panel2:#f8fafc;--line:#e5e9f0;--line2:#d4dae4;--ink:#0f172a;--ink2:#334155;--muted:#64748b;--dim:#94a3b8;
--accent:#4f46e5;--accentbg:#eef2ff;--good:#047857;--goodbg:#ecfdf5;--warn:#b45309;--warnbg:#fffbeb;--bad:#dc2626;--badbg:#fef2f2;--pp:#a16207;--ppbg:#fef9c3;
--buyer:#2563eb;--creator:#059669;--operator:#7c3aed;--market:#ea580c;
--sh:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(50,50,93,.07);--sh2:0 8px 24px rgba(50,50,93,.12),0 2px 6px rgba(16,24,40,.06)}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:13px/1.5 Inter,system-ui,-apple-system,'Segoe UI',sans-serif;overflow:hidden;-webkit-font-smoothing:antialiased}
button{font:inherit;cursor:pointer}
.app{display:grid;grid-template-rows:auto 1fr;height:100vh}
header{display:flex;align-items:center;gap:16px;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:8px;font-weight:600;font-size:15px;white-space:nowrap;letter-spacing:-.01em}
.conn{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;color:var(--muted);background:var(--panel2);border:1px solid var(--line);padding:2px 9px;border-radius:999px}
.conn i{width:7px;height:7px;border-radius:50%;background:var(--dim)}.conn.on{color:var(--good);background:var(--goodbg);border-color:var(--goodln)}.conn.on i{background:#10b981;animation:ping 1.8s infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(16,185,129,.5)}100%{box-shadow:0 0 0 8px rgba(16,185,129,0)}}
.kpis{display:flex;gap:8px;flex:1;overflow:hidden}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:5px 12px;min-width:0;transition:border-color .4s,background .4s}
.kpi .k{font-size:11px;color:var(--muted);white-space:nowrap;font-weight:500}
.kpi .v{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap;letter-spacing:-.01em}
.kpi .d{font-size:11px;font-weight:600;margin-left:5px}.d.up{color:var(--good)}.d.down{color:var(--bad)}
.kpi.flash{border-color:var(--accentln);background:var(--accentbg)}.kpi.badk .v{color:var(--bad)}
header a{color:var(--muted);text-decoration:none;font-size:12.5px;white-space:nowrap;font-weight:500}header a:hover{color:var(--accent)}
.body{display:grid;grid-template-columns:296px 1fr 360px;gap:12px;padding:12px;min-height:0}
.pnl{background:var(--panel);border:1px solid var(--line);border-radius:12px;display:flex;flex-direction:column;min-height:0;overflow:hidden;box-shadow:var(--sh)}
.pnl>h3{margin:0;padding:9px 14px;font-size:12.5px;font-weight:600;color:var(--ink);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px;flex:none}
.pnl>h3 .r{margin-left:auto;font-size:12px;color:var(--muted);font-weight:500}
.pnl>h3 .max{margin-left:6px;background:var(--panel);border:1px solid var(--line);color:var(--muted);border-radius:6px;padding:0 6px;font-size:12px}
.left{display:flex;flex-direction:column;gap:12px;min-height:0}
.roles{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:10px;padding:3px;background:var(--panel2);border:1px solid var(--line);border-radius:10px}
.roles button{background:none;border:0;color:var(--muted);border-radius:7px;padding:6px 4px;font-weight:500;font-size:12.5px}
.roles button.on{background:var(--panel);color:var(--ink);font-weight:600;box-shadow:var(--sh)}
.roles button.on[data-r=buyer]{color:var(--buyer)}.roles button.on[data-r=creator]{color:var(--creator)}.roles button.on[data-r=operator]{color:var(--operator)}
.acts{padding:0 10px 10px;overflow-y:auto;flex:1}
.act{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:12px;margin-bottom:8px}
.act b{display:block;font-size:13px;font-weight:600}.act p{margin:3px 0 10px;color:var(--muted);font-size:12px;line-height:1.45}
.act input,.act textarea,.act select{width:100%;background:var(--panel);border:1px solid var(--line2);color:var(--ink);border-radius:8px;padding:7px 9px;font:12.5px inherit;margin-bottom:8px;outline:none}
.act input:focus,.act textarea:focus,.act select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(79,70,229,.12)}
.act textarea{resize:none;height:48px}
.row2{display:flex;gap:6px;align-items:center}
.go{background:var(--accent);color:var(--onaccent);border:0;border-radius:8px;padding:7px 13px;font-weight:600;font-size:12.5px;white-space:nowrap;box-shadow:0 1px 2px rgba(16,24,40,.08)}
.go:hover{filter:brightness(1.07)}.go.c{background:var(--creator)}.go.o{background:var(--operator)}.go.m{background:var(--market)}.go:disabled{opacity:.45;cursor:default}
.chk{display:flex;gap:6px;align-items:center;color:var(--ink2);font-size:12px;margin:0 0 8px}
.queue{max-height:38%;flex:none}
#approvals{overflow-y:auto;padding:10px}
.appr{border:1px solid var(--warnln);background:var(--warnbg);border-radius:10px;padding:10px 12px;margin-bottom:8px;animation:in .35s}
.appr .t{font-weight:600}.appr .m{color:var(--ink2);font-size:12px}.appr .w{font-size:11.5px;color:var(--warn);font-weight:500}
.appr .row2{margin-top:8px}.appr button{flex:1;border:0;border-radius:7px;padding:6px;font-weight:600;font-size:12px}
.appr .dv{margin-top:6px;font-size:12px;color:var(--ink2)}.appr .dv .hash{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--muted)}.appr .dv .fl{font-size:11.5px;color:var(--muted);line-height:1.35}.appr .iv{margin-top:5px;font-size:12px;line-height:1.35}.appr .o{background:var(--panel);color:var(--accent);border:1px solid var(--accentln)!important}
.appr .y{background:var(--good);color:var(--onaccent)}.appr .n{background:var(--panel);color:var(--bad);border:1px solid var(--badln)}
.empty{color:var(--dim);padding:18px;text-align:center;font-size:12.5px}
.mkt{display:flex;align-items:center;gap:8px;padding:10px 12px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
.sw{position:relative;width:34px;height:19px;border-radius:999px;background:var(--line2);border:0;flex:none}.sw:after{content:'';position:absolute;top:2px;left:2px;width:15px;height:15px;border-radius:50%;background:var(--panel);box-shadow:0 1px 2px rgba(0,0,0,.2);transition:.2s}
.sw.on{background:var(--market)}.sw.on:after{left:17px}
.center{display:grid;grid-template-columns:1.25fr 1fr;grid-template-rows:1.12fr 1fr;gap:12px;min-height:0}
.center.zoom{grid-template-columns:1fr;grid-template-rows:1fr}.center.zoom>.pnl:not(.z){display:none}
.view{flex:1;position:relative;min-height:0}
.view svg{width:100%;height:100%;display:block}
.ticker{flex:none;padding:7px 14px;font-size:12px;color:var(--ink2);border-bottom:1px solid var(--line);background:var(--panel2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-height:32px}
.ticker b{color:var(--ink);font-weight:600}
.legend{flex:none;display:flex;gap:14px;padding:7px 14px;font-size:11.5px;color:var(--muted);border-top:1px solid var(--line);flex-wrap:wrap}
.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.mnode circle.c{stroke-width:1.5}.mnode text{fill:var(--ink2);font-size:11px;font-weight:500;text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-width:4px;stroke-linejoin:round}
.mnode{cursor:pointer}.mnode.me circle.c{stroke-width:3}.mnode.frozen circle.c{fill:var(--badbg)!important;stroke:var(--bad)!important;stroke-width:2}
.mnode.sel circle.c{stroke:var(--ink)!important;stroke-width:3}.mnode.dim{opacity:.18}
.mnode.hub circle.c{stroke-width:2.5}.mnode.hub text{font-weight:600;fill:var(--ink)}
.mnode.act circle.c{animation:glow 1s infinite alternate}@keyframes glow{to{stroke-width:5}}
.mnode.st-good circle.c{stroke:#10b981!important;stroke-width:4}.mnode.st-bad circle.c{stroke:var(--bad)!important;stroke-width:4}
.mnode.st-money circle.c{stroke:#f59e0b!important;stroke-width:4}.mnode.st-busy circle.c{stroke:var(--accent)!important;stroke-width:4}
.medge{stroke:var(--edge);stroke-opacity:.9}.medge.bad{stroke:var(--badln)}.medge.hot{stroke:#f59e0b;stroke-opacity:1}.medge.dim{stroke-opacity:.15}
.ring{fill:rgba(220,38,38,.06);stroke:var(--bad);stroke-dasharray:5 4;stroke-width:1.5}.ringl{stroke:#f87171;stroke-width:1.5;stroke-dasharray:3 3}
.ringtxt{fill:var(--bad);font-size:11px;font-weight:600;paint-order:stroke;stroke:var(--panel);stroke-width:4px;stroke-linejoin:round}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);box-shadow:var(--sh2);border-radius:10px;padding:8px 10px;font-size:12px;max-width:260px;opacity:0;transition:opacity .12s;z-index:5}
.tip.on{opacity:1}.tip b{display:block;font-weight:600}.tip .s{color:var(--muted)}
.dot{pointer-events:none}
.gtabs{display:flex;gap:2px;margin-left:auto;padding:2px;background:var(--panel2);border:1px solid var(--line);border-radius:8px}
.gtabs button{background:none;border:0;color:var(--muted);border-radius:6px;padding:2px 9px;font-size:12px;font-weight:500;white-space:nowrap}
.gtabs button.on{background:var(--panel);color:var(--ink);box-shadow:var(--sh)}.gtabs button.live{color:var(--good)}
.gn rect{fill:var(--panel);stroke:var(--line2);stroke-width:1.2;filter:drop-shadow(0 1px 2px rgba(16,24,40,.06))}.gn text{fill:var(--ink);font-size:12px;font-weight:600;text-anchor:middle;pointer-events:none}
.gn .sub{fill:var(--muted);font-size:10px;font-weight:500}.gn.code rect{stroke-dasharray:4 3}.gn{cursor:pointer}
.gn.running rect{stroke:var(--accent);stroke-width:2;fill:var(--accentbg)}.gn.done rect{stroke:#10b981;fill:var(--goodbg)}.gn.fallback rect{stroke:#f59e0b;fill:var(--warnbg)}
.gn.blocked rect{stroke:var(--bad);fill:var(--badbg)}.gn.sel rect{stroke:var(--ink);stroke-width:2.5}
.gn.pp rect{stroke:#eab308;fill:var(--ppbg)}.gn.pp text{fill:var(--pp)}.gn.guard rect{stroke:var(--badln);fill:var(--badbg)}.gn.guard text{fill:var(--bad)}
.gn.flash rect{stroke-width:3}
.gedge{stroke:var(--edge);stroke-width:1.6;fill:none}.gedge.taken{stroke:#818cf8;stroke-width:2.2}.gedge.hot{stroke:var(--accent);stroke-width:3}.gedge.back{stroke-dasharray:5 5}
.tb{fill:var(--accent);font-size:10.5px;font-weight:600}
.mfn rect{fill:var(--panel);stroke:var(--line2);filter:drop-shadow(0 1px 2px rgba(16,24,40,.06))}.mfn text{fill:var(--muted);font-size:11px;font-weight:500;text-anchor:middle}.mfn .amt{fill:var(--ink);font-size:13px;font-weight:600}
.mfn.pp rect{stroke:#eab308;fill:var(--ppbg)}.mfn.bad rect{stroke:var(--badln);fill:var(--badbg)}.mfn.good rect{stroke:var(--goodln);fill:var(--goodbg)}
.mfn.flash rect{stroke:#f59e0b;stroke-width:2.5}
.mfe{fill:none;stroke:var(--edge);stroke-linecap:round}.mfe.pp{stroke:var(--warnln)}.mfe.bad{stroke:var(--badln)}.mfe.good{stroke:var(--goodln)}
#trace{flex:1;overflow-y:auto;font-size:12.5px}
.run{border-bottom:1px solid var(--line)}
.rh{display:flex;align-items:center;gap:8px;padding:7px 12px;cursor:pointer;background:var(--panel2);position:sticky;top:0;z-index:1;border-bottom:1px solid var(--line)}
.rh .lbl{font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rh .ms{color:var(--muted);font-variant-numeric:tabular-nums;font-size:12px}
.role{font-size:10.5px;font-weight:600;padding:1px 7px;border-radius:999px;text-transform:capitalize}
.role.buyer{background:var(--buyerbg);color:var(--buyer2)}.role.creator{background:var(--goodbg);color:var(--good)}.role.operator{background:var(--violetbg);color:var(--violet)}.role.market{background:var(--marketbg);color:var(--market2)}
.sp{display:grid;grid-template-columns:minmax(0,1fr) 36% 50px;align-items:center;gap:8px;padding:3px 12px 3px 24px;cursor:pointer}
.sp:hover{background:var(--panel2)}.sp.sel{background:var(--accentbg)}
.sp .n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink2)}.sp .n .ic{display:inline-block;width:16px;text-align:center;margin-right:3px;color:var(--muted)}
.sp .bar{position:relative;height:8px;background:var(--soft);border-radius:4px}
.sp .bar i{position:absolute;top:0;height:8px;border-radius:4px;background:#a5b4fc}
.sp.model .bar i{background:#818cf8}.sp.code .bar i{background:#c4b5fd}.sp.pp .bar i{background:#facc15}.sp.bad .bar i{background:#f87171}.sp.actor .bar i{background:#fdba74}
.sp.running .bar i{animation:pl 1s infinite}@keyframes pl{50%{opacity:.45}}
.sp .t{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums;font-size:11.5px}
.sp.pp .n{color:var(--pp)}.sp.bad .n{color:var(--bad)}
.right{display:grid;grid-template-rows:1.25fr 1fr;gap:12px;min-height:0}
#insp{flex:1;overflow-y:auto;padding:12px 14px}
.ih{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:6px}.ih b{font-size:15px;font-weight:600}
.chip{display:inline-block;font-size:11px;font-weight:500;padding:1px 8px;border-radius:999px;background:var(--soft);color:var(--ink2);white-space:nowrap}
.chip.model{background:var(--accentbg);color:var(--accent2)}.chip.code{background:var(--violetbg);color:var(--violet)}.chip.ok{background:var(--goodbg);color:var(--good)}
.chip.no{background:var(--badbg);color:var(--bad)}.chip.hold{background:var(--warnbg);color:var(--warn)}.chip.pp{background:var(--ppbg);color:var(--pp)}
.sec{margin-top:12px}.sec>.k{font-size:11px;font-weight:600;color:var(--muted);margin-bottom:4px}
.stream{font:12px/1.55 'JetBrains Mono',ui-monospace,Consolas,monospace;color:var(--ink2);background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;max-height:170px;overflow-y:auto;white-space:pre-wrap;word-break:break-word}
.cur{display:inline-block;width:6px;height:12px;background:var(--accent);vertical-align:-2px;animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}
.vrow{display:flex;gap:8px;align-items:baseline;padding:3px 0}.vrow .nm{font-weight:500;min-width:120px}.vrow .rs{color:var(--muted);font-size:12px}
.quote{border-left:3px solid var(--line2);padding:3px 10px;color:var(--ink2)}.quote.bull{border-color:#10b981}.quote.bear{border-color:var(--bad)}
.big{font-size:20px;font-weight:600}.what{color:var(--muted);font-size:12px}
pre.raw{font:11px/1.45 'JetBrains Mono',ui-monospace,Consolas,monospace;color:var(--muted);background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px;max-height:160px;overflow:auto;white-space:pre-wrap;word-break:break-word}
#feed{flex:1;overflow-y:auto;padding:4px 12px}
.fe{display:grid;grid-template-columns:42px 1fr;gap:8px;padding:6px 0;border-bottom:1px solid var(--soft);animation:in .3s;cursor:pointer}
.fe:hover .tx{color:var(--ink)}
.fe .tm{color:var(--dim);font-size:11px;font-variant-numeric:tabular-nums;padding-top:1px}
.fe .tx{font-size:12.5px;color:var(--ink2)}.fe .tx b{color:var(--ink);font-weight:600}.fe.pp .tx b{color:var(--pp)}.fe.bad .tx{color:var(--bad)}.fe.bad .tx b{color:var(--bad)}.fe.good .tx b{color:var(--good)}
@keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.src{display:inline-block;font-size:10px;font-weight:600;padding:0 6px;border-radius:999px;margin-left:6px;vertical-align:1px}
.src.pp{background:var(--ppbg);color:var(--pp)}.src.ai{background:var(--accentbg);color:var(--accent2)}.src.sim{background:var(--soft);color:var(--muted)}.src.code{background:var(--violetbg);color:var(--violet)}.src.alp{background:var(--goodbg,#dcfce7);color:var(--good,#15803d)}.src.mcp{background:var(--violetbg);color:var(--violet)}
.real{position:relative}.real>button{background:var(--panel);border:1px solid var(--line);color:var(--ink2);border-radius:999px;padding:4px 11px;font-size:12px;font-weight:500;white-space:nowrap}
.real>button:hover{border-color:var(--accent);color:var(--accent)}
.realp{display:none;position:absolute;right:0;top:34px;width:360px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;z-index:20;box-shadow:var(--sh2);font-size:12.5px;color:var(--ink2)}
.realp.on{display:block}.realp b{display:block;margin:8px 0 4px;font-size:12px;font-weight:600;color:var(--ink)}.realp li{margin:3px 0}.realp ul{margin:0;padding-left:18px}
.ptabs{display:flex;gap:2px;padding:2px;background:var(--panel2);border:1px solid var(--line);border-radius:8px}
.ptabs button{background:none;border:0;color:var(--muted);border-radius:6px;padding:2px 10px;font-size:12px;font-weight:500}.ptabs button.on{background:var(--panel);color:var(--ink);box-shadow:var(--sh)}
#ledger{flex:1;min-height:0;display:none}#ledger.on{display:block}#trace.off{display:none}
.ag-row.bad{background:var(--badbg)!important}
.toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:var(--ink);color:var(--onaccent);padding:8px 16px;border-radius:10px;font-size:12.5px;opacity:0;transition:.3s;pointer-events:none;box-shadow:var(--sh2)}
.toast.on{opacity:1}
.center.wide>#pMap{grid-row:1 / span 2}.center.wide>#pMoney{display:none}
.vpane{display:none;flex-direction:column;flex:1;min-height:0}.vpane.on{display:flex}
.bar{display:flex;gap:6px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.bar input,.bar select{background:var(--panel);border:1px solid var(--line2);color:var(--ink);border-radius:8px;padding:6px 9px;font:12.5px inherit;outline:none}
.bar input:focus,.bar select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(79,70,229,.12)}
.bar .chk{margin:0}.note{padding:7px 12px;font-size:12px;color:var(--muted);border-bottom:1px solid var(--line);background:var(--panel2)}
.note b{color:var(--ink);font-weight:600}
.shop{flex:1;overflow-y:auto;padding:12px}
.shop h4{margin:4px 0 8px;font-size:12px;font-weight:600;color:var(--muted)}
.pgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin-bottom:14px}
.pc{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--panel);display:flex;flex-direction:column;gap:5px;transition:box-shadow .15s,border-color .15s}
.pc:hover{box-shadow:var(--sh2);border-color:var(--line2)}
.pc img{width:100%;height:96px;object-fit:contain;background:var(--panel2);border-radius:7px}
.pc .pt{font-weight:600;font-size:12.5px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:34px}
.pc .pm{font-size:11.5px;color:var(--muted);line-height:1.4}.pc .pm b{color:var(--ink2);font-weight:500}
.pc .pr{font-size:16px;font-weight:600;letter-spacing:-.01em}
.pc .pa{display:flex;gap:5px;margin-top:auto}
.sm{padding:5px 9px!important;font-size:11.5px!important}
.ghost{background:var(--panel);border:1px solid var(--line2);color:var(--ink2);border-radius:8px;font-weight:500}.ghost:hover{border-color:var(--accent);color:var(--accent)}
.pc.off{opacity:.55}.tag{font-size:10.5px;font-weight:600;padding:0 6px;border-radius:999px}
.tag.new{background:var(--accentbg);color:var(--accent2)}.tag.mine{background:var(--buyerbg);color:var(--buyer2)}.tag.sus{background:var(--badbg);color:var(--bad)}.tag.pp{background:var(--ppbg);color:var(--pp)}
.mini{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}
.mini>div{background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:6px 10px}.mini .k{font-size:11px;color:var(--muted)}.mini .v{font-weight:600;font-size:14px}
.gridbox{flex:1;min-height:140px}
.seg{display:flex;gap:2px;padding:2px;background:var(--panel2);border:1px solid var(--line);border-radius:8px}
.seg button{background:none;border:0;color:var(--muted);border-radius:6px;padding:3px 9px;font-size:12px;font-weight:500}.seg button.on{background:var(--panel);color:var(--ink);box-shadow:var(--sh)}
.riskb{display:inline-block;height:7px;border-radius:4px;vertical-align:middle;margin-right:6px}
.cellbtn{border:1px solid var(--line2);background:var(--panel);border-radius:7px;padding:1px 9px;font-size:11.5px;font-weight:500;color:var(--ink2);line-height:22px}
.cellbtn.bad{color:var(--bad);border-color:var(--badln)}.cellbtn.good{color:var(--good);border-color:var(--goodln)}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:var(--edge);border-radius:8px}::-webkit-scrollbar-track{background:transparent}
@media (max-width:1250px){html,body{overflow:auto}.app{height:auto}.body{grid-template-columns:1fr}.center{grid-template-columns:1fr;grid-template-rows:repeat(4,440px)}.right{grid-template-rows:420px 360px}.kpis{flex-wrap:wrap}}
</style></head><body><div class="app">
<header>
  <div class="brand"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.6" fill="#4f46e5" stroke="none"/></svg>Helm control room</div>
  <span class="conn" id="conn"><i></i><span id="connTxt">Connecting</span></span>
  <div class="kpis" id="kpis"></div>
  <button class="themebtn" id="themeBtn" title="Switch light or dark"><span id="themeIco">&#9790;</span><span id="themeTxt">Dark</span></button>
  <div class="real"><button id="realBtn">What is real?</button><div class="realp" id="realP">
    <b>Real, live calls</b><ul><li>Every PayPal call: Orders, holds, captures, voids, Payouts and Catalog products, on the PayPal sandbox (test money)</li><li>Every AI agent: a live OpenAI model, streamed token by token</li><li>Store search: Channel3's real product catalog</li><li>The fraud engines, the solver, the signatures and the zero-knowledge proof</li></ul>
    <b>Simulated, tagged SIM</b><ul><li>The 120 other creators and their four months of sales history (generated)</li><li>The AI customers' wallets. When one buys from a creator who has a sandbox seller account, PayPal is still paid for real</li><li>The dispute button (a simulated PayPal webhook; the real receiver is /api/paypal/webhook)</li></ul>
    <div class="what" style="margin-top:8px">Every Activity line and every ledger row is tagged: <span class="src pp">PayPal</span><span class="src ai">AI</span><span class="src code">code</span><span class="src sim">sim</span></div></div></div>
  <a href="/">full console &rarr;</a>
</header>
<div class="body">
  <div class="left">
    <section class="pnl" style="flex:1">
      <h3>You act as <span class="r" id="roleHint">a buyer</span></h3>
      <div class="roles" id="roles"><button data-r="buyer" class="on">Buyer</button><button data-r="creator">Creator</button><button data-r="operator">Operator</button></div>
      <div class="acts" id="acts"></div>
      <div class="mkt"><button class="sw" id="mktSw" title="AI customers trade on the marketplace every 30 seconds"></button><span id="mktTxt">Market closed. Turn on to let AI customers trade.</span></div>
    </section>
    <section class="pnl queue"><h3>Needs your approval <span class="r" id="apprN"></span></h3><div id="approvals"><div class="empty">Money your agents put on hold waits here until you confirm the delivery.</div></div></section>
  </div>
  <div class="center" id="center">
    <section class="pnl" id="pMap"><h3><span class="ptabs" id="vtabs"><button data-v="map" class="on">Live map</button><button data-v="shop">Shop</button><button data-v="mine">My shop</button><button data-v="accts">Accounts</button></span><span class="r" id="mapStat"></span><button class="max" data-z="pMap">&#x2922;</button></h3>
      <div class="vpane on" id="vMap">
      <div class="ticker" id="mapCap">Every account, live. Hover a dot for who it is and what it just did.</div>
      <div class="view" id="mapView"><svg id="map"></svg><div class="tip" id="tip"></div></div>
      <div class="legend"><span><i style="background:var(--buyer)"></i>You</span><span><i style="background:#94a3b8"></i>Creator</span><span><i style="background:var(--market)"></i>AI customer</span><span><i style="background:var(--bad)"></i>Frozen or ring</span><span><i style="background:#f59e0b"></i>Money moving</span></div></div>
      <div class="vpane" id="vShop">
        <div class="bar"><input id="q" placeholder="Search: beats, presets, a camera strap…" style="flex:1;min-width:150px"><select id="qCat"><option value="">All categories</option></select>
          <input id="qMax" type="number" placeholder="Max $" style="width:76px"><label class="chk"><input type="checkbox" id="qStores" style="width:auto;margin:0"> real stores (Channel3)</label><button class="go sm" id="qGo">Search</button></div>
        <div class="note" id="shopNote">Browse what creators sell. Buy it yourself, or hand it to your buyer agent; either way PayPal holds the money until you confirm delivery.</div>
        <div class="shop" id="shopGrid"><div class="empty">Loading the catalog…</div></div></div>
      <div class="vpane" id="vMine">
        <div class="mini" id="mineSum"></div>
        <div class="note">Your listings. Click a price to change it; buyers and AI customers see the new price at once. <a href="#" id="mineNew" style="color:var(--accent)">List something new</a></div>
        <div class="gridbox" id="mineGrid"></div>
        <div class="note"><b>Recent sales</b></div>
        <div class="gridbox" id="salesGrid"></div></div>
      <div class="vpane" id="vAccts">
        <div class="bar"><input id="aq" placeholder="Search accounts, countries, signals…" style="flex:1;min-width:150px"><span class="seg" id="aseg"><button data-f="all" class="on">All</button><button data-f="review">Needs review</button><button data-f="frozen">Frozen</button></span></div>
        <div class="note" id="acctNote">Every account ranked by risk from its own record: shared device, card or IP, and return rates. Freeze one and its earnings stop moving; payday will hold it.</div>
        <div class="gridbox" id="acctGrid"></div></div>
      </section>
    <section class="pnl" id="pGraph"><h3>Agents <span class="gtabs" id="gtabs"></span><button class="max" data-z="pGraph">&#x2922;</button></h3>
      <div class="ticker" id="gCap">Do something on the left. The agents it wakes up light up here, and the path they took stays lit.</div>
      <div class="view"><svg id="graph" viewBox="0 0 540 500" preserveAspectRatio="xMidYMid meet"></svg></div></section>
    <section class="pnl" id="pMoney"><h3>Money flow <span class="r">PayPal sandbox</span><button class="max" data-z="pMoney">&#x2922;</button></h3>
      <div class="view"><svg id="flow" viewBox="0 0 560 300" preserveAspectRatio="xMidYMid meet"></svg></div></section>
    <section class="pnl" id="pTrace"><h3><span class="ptabs" id="ptabs"><button data-p="trace" class="on">Trace</button><button data-p="ledger">Money ledger</button></span> <span class="r" id="traceStat"></span><button class="max" data-z="pTrace">&#x2922;</button></h3><div id="ledger"></div><div id="trace"><div class="empty">Every run, each agent step inside it, its model and timing, every PayPal call and guardrail. Click any row to inspect it.</div></div></section>
  </div>
  <div class="right">
    <section class="pnl"><h3>Inspector <span class="r" id="inspWhat"></span></h3><div id="insp"><div class="empty">Click an agent, a trace row or an account on the map to see exactly what it saw, said and decided.</div></div></section>
    <section class="pnl"><h3>Activity <span class="r" id="actN"></span></h3><div id="feed"></div></section>
  </div>
</div></div>
<div class="toast" id="toast"></div>

<script>
(() => {
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const money = v => v == null || isNaN(v) ? '' : '$' + Number(v).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
let SID = null; try { SID = localStorage.getItem('helm-sid'); } catch (e) {}
if (!SID) { SID = 'cr-' + Math.random().toString(36).slice(2, 10); try { localStorage.setItem('helm-sid', SID); } catch (e) {} }
const H = {'X-Helm-Session': SID, 'Content-Type': 'application/json'};
function toast(t) { const el = $('#toast'); el.textContent = t; el.classList.add('on'); clearTimeout(toast.h); toast.h = setTimeout(() => el.classList.remove('on'), 2600); }
const clock = () => new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});

const runs = {}, spans = {};
let books = null, replaying = false, selected = null, active = 0, lastUserAct = 0;

// ================= KPIs =================
const KP = [['reserves', 'Safety fund'], ['liabilities', 'Owed to creators'], ['margin', 'Solvency margin'], ['my_earnings', 'Your earnings'],
            ['held', 'On hold (PayPal)'], ['frozen', 'Frozen (fraud)'], ['suspended', 'Suspended'], ['orders', 'Orders']];
function kv(a, k) { if (!a) return null; if (k === 'held') return (a.holds || []).reduce((s, h) => s + (+h.amount || 0), 0); return a[k]; }
function renderBooks(a) {
  const prev = books; books = a;
  $('#kpis').innerHTML = KP.map(([k, l]) => {
    const v = kv(a, k), p = prev ? kv(prev, k) : null, d = (p != null && v != null) ? v - p : 0, isM = !['suspended', 'orders'].includes(k);
    const dd = Math.abs(d) > 0.004 && !replaying ? `<span class="d ${d > 0 ? 'up' : 'down'}">${d > 0 ? '+' : '&minus;'}${isM ? money(Math.abs(d)) : Math.abs(d)}</span>` : '';
    return `<div class="kpi ${dd ? 'flash' : ''} ${(k === 'margin' && v < 0) ? 'badk' : ''}"><div class="k">${l}</div><div class="v">${isM ? money(v) : (v ?? 0)}${dd}</div></div>`;
  }).join('');
  renderApprovals(a.holds || []);
}

// ================= approvals (human in the loop) =================
const holdSeen = {}, autoTried = {};
const VERD = {matches: ['ok', 'matches the listing'], mismatch: ['no', 'does not match'], incomplete: ['no', 'incomplete'], unverified: ['hold', 'not verified']};
function deliveryHtml(h) {
  const d = h.delivery || {}, ins = h.inspection || {}, acc = h.accessed || [];
  let ev = '';
  if (d.kind === 'download') ev = `<div class="dv"><b>Delivered:</b> ${esc(d.archive)} &middot; ${(d.files || []).length} files &middot; ${(d.bytes / 1e6).toFixed(d.bytes < 1e6 ? 3 : 1)} MB<div class="hash">sha256 ${esc((d.sha256 || '').slice(0, 16))}&hellip;</div>
      <div class="fl">${(d.files || []).slice(0, 4).map(f => esc(f.name) + ' (' + (f.bytes >= 1e6 ? (f.bytes / 1e6).toFixed(1) + ' MB' : f.bytes >= 1e3 ? Math.round(f.bytes / 1e3) + ' KB' : f.bytes + ' B') + ')').join(', ')}${(d.files || []).length > 4 ? ', &hellip;' : ''}</div></div>`;
  else if (d.kind === 'shipment') ev = `<div class="dv"><b>Shipped:</b> ${esc(d.carrier)} ${esc(d.tracking)} &middot; ${esc(d.status)} <span class="src sim">sim</span></div>`;
  else ev = '<div class="dv">Nothing delivered yet.</div>';
  const v = VERD[ins.verdict] || VERD.unverified;
  const insp = ins.verdict ? `<div class="iv"><span class="chip ${v[0]}">AI inspector: ${v[1]}</span> <span class="what">${esc(ins.reason || '')}</span></div>` : '';
  const seen = acc.length ? `<div class="what">You opened it at ${new Date(acc[acc.length - 1].at * 1000).toTimeString().slice(0, 5)} from ${esc(acc[acc.length - 1].ip)} (logged as proof of delivery)</div>` : '';
  return ev + insp + seen;
}
function renderApprovals(holds) {
  $('#apprN').textContent = holds.length ? holds.length + ' waiting' : '';
  if (!holds.length) { $('#approvals').innerHTML = '<div class="empty">Money your agents put on hold waits here. The seller delivers, the AI inspector checks it, and you accept or reject.</div>'; return; }
  $('#approvals').innerHTML = holds.map(h => { holdSeen[h.escrow_id] = holdSeen[h.escrow_id] || Date.now(); const ins = h.inspection || {};
    return `<div class="appr"><div class="t">${esc(h.title)}</div><div class="m">${money(h.amount)} held by PayPal for ${esc(h.merchant)} &middot; payee ${esc(h.payee)}</div>
    ${deliveryHtml(h)}
    <div class="w" data-e="${esc(h.escrow_id)}" data-end="${ins.window_ends || 0}" data-ok="${ins.verdict === 'matches' ? 1 : 0}">waiting</div>
    <div class="row2">${h.delivery && h.delivery.kind === 'download' ? `<button class="o" data-a="open_delivery" data-e="${esc(h.escrow_id)}">Open it</button>` : ''}<button class="y" data-a="confirm" data-e="${esc(h.escrow_id)}">Accept</button><button class="n" data-a="reject" data-e="${esc(h.escrow_id)}">Reject</button></div></div>`; }).join('');
}
setInterval(() => document.querySelectorAll('.appr .w').forEach(w => {
  const left = Math.round(+w.dataset.end + 4 - Date.now() / 1000), ok = w.dataset.ok === '1';
  if (!+w.dataset.end) { w.textContent = 'waiting on you'; return; }
  if (left > 0) { w.textContent = ok ? `auto-releases in ${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')} unless you reject` : `inspector flagged it: waits for your decision`; return; }
  if (!ok) { w.textContent = 'inspector flagged it: waits for your decision'; return; }
  w.textContent = 'inspection window over: releasing'; const e = w.dataset.e;
  if (!autoTried[e] || Date.now() - autoTried[e] > 15000) { autoTried[e] = Date.now(); act('auto_release', {escrow_id: e}); } }), 1000);
$('#approvals').addEventListener('click', e => { const b = e.target.closest('button[data-a]'); if (!b) return; if (b.dataset.a !== 'open_delivery') b.disabled = true; act(b.dataset.a, {escrow_id: b.dataset.e}); });

// ================= actions per role =================
const ACTS = {
  buyer: `
    <div class="act"><b>Buy something</b><p>Your buyer agents understand, search creators then real stores, screen for attacks, pick inside your signed budget, and PayPal holds the money.</p>
      <textarea id="need">I need a trap beat pack for my next video</textarea>
      <div class="row2"><input id="budget" type="number" value="80" style="width:80px;margin:0"><span class="what">signed budget</span></div>
      <label class="chk" style="margin-top:6px"><input type="checkbox" id="attack" checked style="width:auto;margin:0"> a seller hid a hijack in a listing</label>
      <button class="go" data-act="buy">Send my buyer agent</button></div>
    <div class="act"><b>Or browse and pick it yourself</b><p>The <span style="font-weight:600;color:var(--ink)">Shop</span> tab lists every creator's items with their sales, return rates and a trust score, plus real stores through Channel3. Buy directly or hand any item to your agent.</p><button class="ghost sm" data-view="shop">Open the shop</button></div>
    <div class="act"><b>Approve or void the money</b><p>Every hold lands in &ldquo;Needs your approval&rdquo; below. Release pays the creator; void returns it.</p></div>`,
  creator: `
    <div class="act"><b>Sell something</b><p>It becomes a real PayPal Catalog product and a live listing. Buyer agents and AI customers can buy it, and their payments to you go through PayPal.</p>
      <input id="sTitle" value="Neon city LUT pack for night video">
      <div class="row2"><input id="sPrice" type="number" value="29" style="width:70px;margin:0"><select id="sCat" style="flex:1;min-width:0;margin:0">${['presets', 'beats', 'prints', 'ebooks', 'merch', 'templates'].map(c => `<option>${c}</option>`).join('')}</select><button class="go c" data-act="sell">List it</button></div></div>
    <div class="act"><b>Ask my AI manager</b><p>Reads your real sales, forecasts next month and writes you a briefing with what to do.</p><button class="go c" data-act="my_page">Brief me</button></div>
    <div class="act"><b>Get paid early</b><p>Borrow against your proven earnings. The amount is priced from your sales ledger and capped by the safety fund, not by what you type.</p>
      <div class="row2"><input id="advAmt" type="number" placeholder="amount (blank = best offer)" style="margin:0"><button class="go c" data-act="advance">Take it</button></div></div>
    <div class="act"><b>Invest with my club</b><p>You and three community members invest together in real companies. Each of you has an AI agent that reads live prices and news over MCP, picks on its own, then sees the others and revises. Code caps any company at 35% and each person at the limit they signed.</p>
      <textarea id="clubNote" placeholder="Tell your agent what you want, e.g. steady growth, no oil companies">I'm a creator. I want to grow my earnings, not gamble them.</textarea>
      <div class="row2"><input id="clubAmt" type="number" value="200" style="width:90px;margin:0"><span class="what" style="flex:1;align-self:center">my share, $</span><button class="go c" data-act="club">Invest together</button></div></div>
    <div class="act"><b>A buyer disputes my sale</b><p>A PayPal dispute arrives for your latest sale: chargeback, abuse re-scan, evidence from the receipts.</p><button class="go c" data-act="dispute">Receive a dispute</button></div>`,
  operator: `
    <div class="act"><b>Scan for fraud</b><p>Abuse and ring-linkage engines read the sales history. Rings light up red on the map and their money freezes.</p><button class="go o" data-act="scan">Scan the marketplace</button></div>
    <div class="act"><b>Run payday</b><p>Signal analyst, risk analyst, bull, bear and manager decide; code caps it to the safe release; PayPal Payouts pays.</p>
      <textarea id="signal">Risk alert: a fraud and chargeback wave is hitting brand-new viral accounts this week.</textarea>
      <button class="go o" data-act="payday">Run payday</button></div>
    <div class="act"><b>Prove we can pay everyone</b><p>A zero-knowledge proof that the safety fund covers every creator, without revealing a balance.</p><button class="go o" data-act="prove">Prove solvency</button></div>
    <div class="act"><b>Open the market for a round</b><p>Six AI customers, each in character, list, buy and return on the marketplace.</p><button class="go m" data-act="customers">Run one round</button></div>`,
};
let role = 'buyer';
function setRole(r) { role = r; document.querySelectorAll('#roles button').forEach(b => b.classList.toggle('on', b.dataset.r === r));
  $('#roleHint').textContent = {buyer: 'a buyer', creator: 'a creator (You)', operator: 'the platform operator'}[r]; $('#acts').innerHTML = ACTS[r]; }
$('#roles').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { setRole(b.dataset.r); setView({buyer: 'shop', creator: 'mine', operator: 'accts'}[b.dataset.r]); } });
$('#acts').addEventListener('click', e => { const vb = e.target.closest('button[data-view]'); if (vb) { setView(vb.dataset.view); return; } const b = e.target.closest('button[data-act]'); if (!b) return;
  const a = b.dataset.act, p = {};
  if (a === 'buy') { p.need = $('#need').value; p.budget = +$('#budget').value; p.attack = $('#attack').checked; }
  if (a === 'advance' && $('#advAmt').value) p.amount = +$('#advAmt').value;
  if (a === 'payday') p.signal = $('#signal').value;
  if (a === 'club') { p.note = $('#clubNote').value; p.amount = +$('#clubAmt').value || 200; }
  if (a === 'sell') { p.title = $('#sTitle').value; p.price = +$('#sPrice').value; p.category = $('#sCat').value; }
  b.disabled = true; setTimeout(() => b.disabled = false, 2500); act(a, p); });
async function act(a, p) {
  if (a !== 'customers') lastUserAct = Date.now();
  try { const r = await fetch('/api/live/act', {method: 'POST', headers: H, body: JSON.stringify({action: a, params: p || {}})}); const j = await r.json();
    if (j.error) toast(j.error); } catch (e) { toast('could not reach the server'); }
}
setRole('buyer');

let mktOn = false, mktTimer = null;
function setMkt(on) { mktOn = on; $('#mktSw').classList.toggle('on', on);
  $('#mktTxt').textContent = on ? 'Market open: AI customers trade every 30 s.' : 'Market closed. Turn on to let AI customers trade.';
  clearInterval(mktTimer); if (on) { mktTimer = setInterval(() => { if (!document.hidden && active === 0 && Date.now() - lastUserAct > 15000) act('customers'); }, 30000); if (active === 0) act('customers'); } }
$('#mktSw').addEventListener('click', () => setMkt(!mktOn));

// ================= marketplace map (d3-force) =================
const mapSvg = d3.select('#map'), mapView = $('#mapView');
let W = 600, Hh = 400, sim = null, mNodes = [], mEdges = [], nodeById = {}, ringSets = [];
const gEdges = mapSvg.append('g'), gRings = mapSvg.append('g'), gNodes = mapSvg.append('g'), gDots = mapSvg.append('g');
const bubbles = {};
function size() { const r = mapView.getBoundingClientRect(); W = Math.max(200, r.width); Hh = Math.max(200, r.height); mapSvg.attr('viewBox', `0 0 ${W} ${Hh}`); }
function hubPos(id) { return id === 'PAYPAL' ? [W * .5, Hh * .56] : [W * .5, Hh * .2]; }
function nodeColor(d) { if (d.hub === 'pp') return 'var(--ppbg)'; if (d.hub === 'op') return 'var(--violetbg)'; if (d.me) return 'var(--buyerbg)'; if (d.cust) return 'var(--marketbg)'; return 'var(--soft)'; }
function nodeStroke(d) { if (d.hub === 'pp') return '#d97706'; if (d.hub === 'op') return '#7c3aed'; if (d.me) return '#2563eb'; if (d.cust) return '#ea580c'; return '#94a3b8'; }
function rad(d) { if (d.hub) return 20; if (d.me) return 16; return 6 + Math.min(12, Math.sqrt(Math.max(0, d.owed || 0)) / 4); }
function setGraph(g) {
  size();
  const old = {}; mNodes.forEach(n => old[n.id] = n);
  const hubs = [['PAYPAL', 'PayPal', 'pp'], ['PLATFORM', 'Helm platform', 'op']].map(([id, name, hub]) => { const [x, y] = hubPos(id); return Object.assign(old[id] || {x, y}, {id, name, hub, fx: x, fy: y}); });
  const fresh = g.nodes.map(n => Object.assign(old[n.id] || {}, n));
  const keep = mNodes.filter(n => !n.hub && !g.nodes.find(x => x.id === n.id) && (n.cust || ringSets.some(r => r.members.includes(n.id))));
  mNodes = hubs.concat(fresh, keep);
  mNodes.forEach(n => { if (n.me && n.x == null) { n.x = W * .18; n.y = Hh * .56; } });
  nodeById = {}; mNodes.forEach(n => nodeById[n.id] = n);
  mEdges = g.edges.filter(e => nodeById[e.source] && nodeById[e.target]).map(e => ({...e}));
  drawMap(); $('#mapStat').textContent = `${g.nodes.length} accounts in view`;
}
function addNode(id, name, extra) { if (nodeById[id]) return nodeById[id]; const n = {id, name, owed: 0, ...extra, x: W * .5 + (Math.random() - .5) * 200, y: Hh * .5 + (Math.random() - .5) * 160};
  mNodes.push(n); nodeById[id] = n; drawMap(); return n; }
function drawMap() {
  if (!sim) {
    sim = d3.forceSimulation().force('charge', d3.forceManyBody().strength(-110))
      .force('collide', d3.forceCollide().radius(d => d.hub ? rad(d) + 38 : rad(d) + 9)).force('x', d3.forceX(() => W * .55).strength(d => d.cust ? .14 : .035)).force('y', d3.forceY(() => Hh * .55).strength(d => d.cust ? .14 : .06)).on('tick', tickMap);
  }
  sim.nodes(mNodes); sim.force('link', d3.forceLink(mEdges).id(d => d.id).distance(70).strength(.07));
  const rl = []; ringSets.forEach(r => { const ms = r.members.filter(m => nodeById[m]); for (let i = 0; i < ms.length; i++) for (let j = i + 1; j < ms.length; j++) rl.push({source: ms[i], target: ms[j]}); });
  sim.force('ring', d3.forceLink(rl).id(d => d.id).distance(30).strength(.9));
  const e = gEdges.selectAll('line').data(mEdges, d => (d.source.id || d.source) + '>' + (d.target.id || d.target));
  e.exit().remove();
  e.enter().append('line').merge(e).attr('class', d => 'medge' + (d.bad ? ' bad' : '')).attr('stroke-width', d => Math.min(4, .6 + Math.log2(1 + d.count)));
  const n = gNodes.selectAll('g.mnode').data(mNodes, d => d.id);
  n.exit().remove();
  const ne = n.enter().append('g').attr('class', 'mnode').on('click', (ev, d) => selectAccount(d.id))
    .on('mouseenter mousemove', (ev, d) => showTip(d, ev)).on('mouseleave', hideTip)
    .call(d3.drag().on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(.2).restart(); if (!d.hub) { d.fx = d.x; d.fy = d.y; } })
      .on('drag', (ev, d) => { if (!d.hub) { d.fx = ev.x; d.fy = ev.y; } }).on('end', (ev, d) => { if (!ev.active) sim.alphaTarget(0); if (!d.hub) { d.fx = null; d.fy = null; } }));
  ne.append('circle').attr('class', 'c'); ne.append('text');
  const all = ne.merge(n);
  all.attr('class', d => 'mnode' + (d.me ? ' me' : '') + (d.hub ? ' hub' : '') + (d.frozen ? ' frozen' : '') + (selected && selected.acct === d.id ? ' sel' : ''));
  all.select('circle').attr('r', rad).style('fill', nodeColor).style('stroke', nodeStroke);
  all.select('text').attr('dy', d => d.hub === 'op' ? -(rad(d) + 7) : rad(d) + 13).text(d => (d.hub || d.me || (selected && selected.acct === d.id)) ? (d.name.length > 16 ? d.name.slice(0, 15) + '…' : d.name) : '');
  all.classed('st-busy st-good st-bad st-money', false); all.each(function (d) { if (d.stUntil && d.stUntil > Date.now()) d3.select(this).classed(d.stCls, true); });
  sim.alpha(.5).restart();
}
function tickMap() {
  mNodes.forEach(d => { const r = rad(d) + 4; d.x = Math.max(r, Math.min(W - r, d.x)); d.y = Math.max(r + 22, Math.min(Hh - r - 24, d.y)); });
  gEdges.selectAll('line').attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  gNodes.selectAll('g.mnode').attr('transform', d => `translate(${d.x},${d.y})`);
  drawRings(); placeBubbles();
}
function drawRings() {
  const sel = gRings.selectAll('g.rg').data(ringSets);
  sel.exit().remove();
  const en = sel.enter().append('g').attr('class', 'rg'); en.append('path').attr('class', 'ring'); en.append('g').attr('class', 'rl'); en.append('text').attr('class', 'ringtxt');
  en.merge(sel).each(function (r) {
    const pts = r.members.map(m => nodeById[m]).filter(Boolean); const g = d3.select(this);
    if (pts.length < 2) return;
    const cx = d3.mean(pts, p => p.x), cy = d3.mean(pts, p => p.y);
    const pad = pts.flatMap(p => { const r = rad(p) + 14; return d3.range(8).map(k => [p.x + r * Math.cos(k * Math.PI / 4), p.y + r * Math.sin(k * Math.PI / 4)]); });
    const hull = d3.polygonHull(pad) || pad;
    g.select('path').attr('d', d3.line().curve(d3.curveCatmullRomClosed.alpha(.6))(hull));
    const top = d3.min(hull, q => q[1]), left = d3.min(hull, q => q[0]);
    const ls = g.select('.rl').selectAll('line').data(d3.pairs(pts.concat([pts[0]])));
    ls.enter().append('line').attr('class', 'ringl').merge(ls).attr('x1', d => d[0].x).attr('y1', d => d[0].y).attr('x2', d => d[1].x).attr('y2', d => d[1].y);
    g.select('text').text('');
  });
}
const ST = {buyer: 'st-busy', creator: 'st-good', operator: 'st-busy', market: 'st-busy', bad: 'st-bad', money: 'st-money'};
function bubble(id, text, cls, ms) {
  if (!id || !nodeById[id]) return; const n = nodeById[id];
  n.status = text; n.stCls = ST[cls] || 'st-busy'; n.stUntil = Date.now() + (ms || 6000);
  gNodes.selectAll('g.mnode').filter(d => d.id === id).classed('st-busy st-good st-bad st-money', false).classed(n.stCls, true);
  if (!replaying && !/…$/.test(text)) $('#mapCap').innerHTML = `<b>${esc(n.name)}</b> &middot; ${esc(text)}`;
  else if (!replaying) $('#mapCap').innerHTML = `<b>${esc(n.name)}</b> &middot; ${esc(text)}`;
  if (tipFor === id) showTip(n);
}
function placeBubbles() {}
setInterval(() => { const now = Date.now(); mNodes.forEach(n => { if (n.stUntil && n.stUntil < now) { n.stUntil = 0; n.status = n.status ? n.status : ''; gNodes.selectAll('g.mnode').filter(d => d.id === n.id).classed('st-busy st-good st-bad st-money', false); } }); }, 500);
let tipFor = null; const tip = $('#tip');
function showTip(d, ev) {
  tipFor = d.id; const ring = ringSets.find(r => r.members.includes(d.id));
  tip.innerHTML = `<b>${esc(d.name)}</b><div class="s">${d.hub ? (d.hub === 'pp' ? 'PayPal (sandbox)' : 'Helm platform') : d.me ? 'You' : d.cust ? 'AI customer' + (d.persona ? ' &middot; ' + esc(d.persona) : '') : 'Creator'}${d.frozen ? ' &middot; <span style="color:var(--bad)">frozen</span>' : ''}${ring ? ' &middot; <span style="color:var(--bad)">in a ring</span>' : ''}</div>` +
    (d.hub ? '' : `<div class="s">owed ${money(d.owed || 0)}${d.sales != null ? ' &middot; ' + d.sales + ' sales' : ''}</div>`) + (d.status ? `<div style="margin-top:4px">${esc(d.status)}</div>` : '');
  if (ev) { const r = mapView.getBoundingClientRect(); let x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14; if (x > r.width - 270) x -= 290; if (y > r.height - 90) y -= 100; tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
  tip.classList.add('on');
}
function hideTip() { tipFor = null; tip.classList.remove('on'); }
function pulse(from, to, cls) {
  const a = nodeById[from], b = nodeById[to]; if (!a || !b || replaying || a === b) return;
  const col = cls === 'bad' ? '#dc2626' : '#f59e0b';
  const c = gDots.append('circle').attr('class', 'dot').attr('r', 5).attr('fill', col).attr('cx', a.x).attr('cy', a.y).style('filter', `drop-shadow(0 0 6px ${col})`);
  c.transition().duration(900).ease(d3.easeCubicInOut).attrTween('cx', () => t => a.x + (b.x - a.x) * t).attrTween('cy', () => t => a.y + (b.y - a.y) * t).remove();
  const hit = gEdges.selectAll('line').filter(d => (d.source.id === from && d.target.id === to) || (d.source.id === to && d.target.id === from)).classed('hot', true);
  setTimeout(() => hit.classed('hot', false), 1200);
}
function glow(id, on) { gNodes.selectAll('g.mnode').filter(d => d.id === id).classed('act', on); }
window.addEventListener('resize', () => { size(); mNodes.forEach(n => { if (n.hub) { const [x, y] = hubPos(n.id); n.fx = x; n.fy = y; } }); sim && sim.alpha(.3).restart(); });
const ME = () => (mNodes.find(n => n.me) || {}).id;
function idFromLabel(s) { const m = /\[(u\d+|me)\]/.exec(s || ''); return m ? m[1] : null; }

// ================= agent graphs, one per LangGraph =================
const GRAPHS = {
  buyer: { title: 'Buyer', nodes: {
      supervisor: [270, 250, 'Supervisor', 'routes the work', 'code'], understand: [270, 48, 'Understand', 'what is needed', 'model'],
      search: [415, 108, 'Search', 'creators, then Channel3', 'code'], safety: [468, 250, 'Safety', 'quarantine injections', 'code'],
      select: [415, 392, 'Select', 'best fit in budget', 'model'], authorize: [270, 452, 'Authorize', 'signed mandate (ES256)', 'code'],
      settle: [125, 392, 'Settle', 'PayPal hold', 'code'], deliver: [72, 250, 'Deliver', 'seller hands it over', 'code'],
      inspect: [125, 108, 'Inspect', 'AI checks the delivery', 'model'], paypal: [72, 476, 'PayPal', 'Orders + holds', 'pp'], guard: [468, 330, 'Guardrails', 'blocks attacks', 'guard']},
    edges: [['supervisor','understand'],['supervisor','search'],['supervisor','safety'],['supervisor','select'],['supervisor','authorize'],['supervisor','settle'],['settle','paypal'],['safety','guard'],['settle','deliver'],['deliver','inspect']]},
  operator: { title: 'Payday', nodes: {
      signal_analyst: [270, 40, 'Signal analyst', 'reads the week', 'model'], risk_analyst: [270, 115, 'Risk analyst', 'pay or hold, per creator', 'model'],
      bull: [140, 192, 'Bull', 'argues to pay fast', 'model'], bear: [400, 192, 'Bear', 'argues for caution', 'model'],
      manager: [270, 270, 'Manager', 'risk multiplier + proposal', 'model'], compliance_gate: [270, 345, 'Compliance', 'sanctions, structuring', 'code'],
      dispose: [270, 420, 'Dispose', 'code caps to the safe release', 'code'], paypal: [460, 420, 'PayPal', 'Payouts API', 'pp'], guard: [80, 420, 'Guardrails', 'blocks attacks', 'guard']},
    edges: [['signal_analyst','risk_analyst'],['risk_analyst','bull'],['bull','bear'],['bear','bull',1],['bear','manager'],['manager','compliance_gate'],['compliance_gate','dispose'],['dispose','paypal']]},
  club: { title: 'Club', nodes: {
      mcp: [455, 40, 'MCP server', 'helm-market: news, prices', 'pp'], club_research: [270, 40, 'Research', 'calls the MCP tools', 'code'],
      club_reflect: [270, 112, 'Reflect', 'learns from past picks', 'model'],
      member_you: [68, 200, 'You', 'your agent', 'model'], member_priya: [203, 200, 'Priya', 'steady, dividends', 'model'],
      member_marcus: [338, 200, 'Marcus', 'growth, AI', 'model'], member_lena: [473, 200, 'Lena', 'recession-proof', 'model'],
      club_discuss: [270, 290, 'Share picks', 'each sees the others', 'code'], club_manager: [270, 362, 'Club manager', 'merges into one portfolio', 'model'],
      club_dispose: [270, 434, 'Limits', 'code: 35% cap, signed limits', 'code'], broker: [455, 434, 'Broker', 'Alpaca paper orders', 'pp']},
    edges: [['club_research','mcp'],['club_research','club_reflect'],['club_reflect','member_you'],['club_reflect','member_priya'],['club_reflect','member_marcus'],['club_reflect','member_lena'],
      ['member_you','club_discuss'],['member_priya','club_discuss'],['member_marcus','club_discuss'],['member_lena','club_discuss'],['club_discuss','club_manager'],['club_manager','club_dispose'],['club_dispose','broker']]},
  market: { title: 'Customers', nodes: {hub: [270, 250, 'Marketplace', 'listings, orders, returns', 'code']}, edges: []},
  fraud: { title: 'Fraud', nodes: {
      abuse: [150, 140, 'Abuse engine', 'serial returners, bad sellers', 'code'], linkage: [390, 140, 'Ring linkage', 'shared device, card, ip', 'code'],
      freeze: [270, 290, 'Freeze', 'suspend + freeze earnings', 'code'], guard: [270, 420, 'Guardrails', 'payouts blocked', 'guard']},
    edges: [['abuse','freeze'],['linkage','freeze'],['freeze','guard']]},
};
const NW = 140, NH = 46, gsvg = $('#graph'); let gKey = null;
const gState = {buyer: {}, operator: {}, club: {}, market: {}, fraud: {}}, gBadges = {buyer: {}, operator: {}, club: {}, market: {}, fraud: {}}, taken = {buyer: new Set(), operator: new Set(), club: new Set(), market: new Set(), fraud: new Set()}, lastG = {}, liveG = {};
function gtabs() { $('#gtabs').innerHTML = Object.entries(GRAPHS).map(([k, g]) => `<button data-g="${k}" class="${k === gKey ? 'on' : ''} ${liveG[k] ? 'live' : ''}">${liveG[k] ? '&#9679; ' : ''}${g.title}</button>`).join(''); }
$('#gtabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) showGraph(b.dataset.g, true); });
function showGraph(k, force) {
  if (gKey === k && !force) return; gKey = k; const G = GRAPHS[k];
  let h = '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="#94a3b8"/></marker></defs>';
  for (const [a, b, back] of G.edges) { const [x1, y1] = G.nodes[a], [x2, y2] = G.nodes[b];
    const p = back ? `M${x1},${y1 + 14} C${(x1 + x2) / 2},${y1 + 58} ${(x1 + x2) / 2},${y2 + 58} ${x2},${y2 + 14}` : `M${x1},${y1} L${x2},${y2}`;
    h += `<path class="gedge${back ? ' back' : ''}${taken[k].has(a + '>' + b) || taken[k].has(b + '>' + a) ? ' taken' : ''}" id="ge-${a}-${b}" d="${p}" marker-end="url(#ar)"/>`; }
  for (const [id, [x, y, name, sub, kind]] of Object.entries(G.nodes)) {
    h += `<g class="gn ${kind} ${gState[k][id] || ''}" data-n="${id}" id="gn-${id}" transform="translate(${x - NW / 2},${y - NH / 2})"><rect width="${NW}" height="${NH}" rx="11"/>
      <text x="${NW / 2}" y="19">${esc(name)}</text><text class="sub" x="${NW / 2}" y="34">${esc(sub)}</text><text class="tb" id="gtb-${id}" x="${NW - 6}" y="-5" text-anchor="end">${esc(gBadges[k][id] || '')}</text></g>`; }
  gsvg.innerHTML = h + '<g id="gpk"></g>'; gtabs();
}
function gNode(k, id, cls) { gState[k][id] = cls; if (gKey === k) { const el = gsvg.querySelector('#gn-' + CSS.escape(id)); if (el) { el.classList.remove('running', 'done', 'fallback', 'blocked'); if (cls) el.classList.add(cls); } } }
function gBadge(k, id, t) { gBadges[k][id] = t; if (gKey === k) { const el = gsvg.querySelector('#gtb-' + CSS.escape(id)); if (el) el.textContent = t; } }
function gFlash(k, id) { if (gKey !== k) return; const el = gsvg.querySelector('#gn-' + CSS.escape(id)); if (el) { el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1200); } }
function gPacket(k, from, to, color) {
  const G = GRAPHS[k]; if (!G.nodes[from] || !G.nodes[to] || from === to) return;
  taken[k].add(from + '>' + to); if (gKey !== k || replaying) return;
  const e = gsvg.querySelector(`#ge-${CSS.escape(from)}-${CSS.escape(to)}`) || gsvg.querySelector(`#ge-${CSS.escape(to)}-${CSS.escape(from)}`);
  if (e) { e.classList.add('taken', 'hot'); setTimeout(() => e.classList.remove('hot'), 800); }
  const [x1, y1] = G.nodes[from], [x2, y2] = G.nodes[to];
  const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.setAttribute('r', 5.5); c.setAttribute('fill', color || '#4f46e5'); c.style.filter = `drop-shadow(0 0 4px ${color || '#4f46e5'})`;
  gsvg.querySelector('#gpk').appendChild(c); const t0 = performance.now();
  (function st(now) { const q = Math.min(1, (now - t0) / 600), z = q < .5 ? 2 * q * q : 1 - Math.pow(-2 * q + 2, 2) / 2; c.setAttribute('cx', x1 + (x2 - x1) * z); c.setAttribute('cy', y1 + (y2 - y1) * z); if (q < 1) requestAnimationFrame(st); else c.remove(); })(t0);
}
function resetGraph(k) { gState[k] = {}; gBadges[k] = {}; taken[k] = new Set(); lastG[k] = null; if (k === 'market') { GRAPHS.market.nodes = {hub: [270, 250, 'Marketplace', 'listings, orders, returns', 'code']}; GRAPHS.market.edges = []; } }
function addCustomer(id, name, persona) {
  const G = GRAPHS.market; if (G.nodes['c_' + id]) return; const n = Object.keys(G.nodes).length - 1, ang = -Math.PI / 2 + n * (Math.PI * 2 / 6), R = 180;
  G.nodes['c_' + id] = [270 + R * Math.cos(ang), 250 + R * Math.sin(ang) * .95, name, String(persona || '').slice(0, 24), 'model']; G.edges.push(['hub', 'c_' + id]);
  if (gKey === 'market') showGraph('market', true);
}
gsvg.addEventListener('click', e => { const g = e.target.closest('.gn'); if (!g) return; const id = g.dataset.n;
  const sp = Object.values(spans).filter(s => s.graph === gKey && s.node === id).pop(); if (sp) selectSpan(sp.key); });
showGraph('buyer');

// ================= money flow =================
const FN = {
  buyers: [70, 45, 'Buyers'], hold: [210, 45, 'PayPal hold', 'pp'], earn: [350, 45, 'Creator earnings', 'good'], frozen: [490, 45, 'Frozen (fraud)', 'bad'],
  adv: [70, 145, 'Advances out'], fee: [210, 145, 'Platform fee'], clawed: [490, 145, 'Clawed back', 'bad'],
  fund: [70, 250, 'Safety fund'], payouts: [210, 250, 'PayPal Payouts', 'pp'], paid: [350, 250, 'Paid to creators', 'good']};
const FE = [['buyers', 'hold', 'pp'], ['hold', 'earn', 'good'], ['hold', 'fee', ''], ['hold', 'buyers', 'bad', 1], ['fund', 'payouts', 'pp'], ['payouts', 'paid', 'good'],
            ['earn', 'frozen', 'bad'], ['earn', 'clawed', 'bad'], ['fund', 'adv', '']];
const flowAmt = {}, edgeAmt = {}, flowOut = {};
function drawFlow() {
  let h = '';
  for (const [a, b, c, back] of FE) { const [x1, y1] = FN[a], [x2, y2] = FN[b], w = Math.min(16, 2 + Math.log10(1 + (edgeAmt[a + b] || 0)) * 3.2);
    const dir = y2 > y1 ? 1 : -1;
    const d = back ? `M${x1 - 30},${y1 + 22} C${x1 - 30},${y1 + 52} ${x2 + 30},${y2 + 52} ${x2 + 30},${y2 + 22}`
      : x1 === x2 ? `M${x1},${y1 + 22 * dir} L${x2},${y2 - 22 * dir}`
      : y1 === y2 ? `M${x1 + 64},${y1} L${x2 - 64},${y2}`
      : `M${x1 + 30},${y1 + 22} C${x1 + 30},${y2} ${x1 + 30},${y2} ${x2 - 64},${y2}`;
    h += `<path class="mfe ${c}" id="fe-${a}${b}" d="${d}" stroke-width="${w}"/>`; }
  for (const [id, [x, y, name, c]] of Object.entries(FN)) h += `<g class="mfn ${c || ''}" id="fn-${id}" transform="translate(${x - 64},${y - 22})"><rect width="128" height="44" rx="9"/><text x="64" y="17">${name}</text><text class="amt" x="64" y="34">${money(flowAmt[id] || flowOut[id] || 0)}</text></g>`;
  $('#flow').innerHTML = h + '<g id="fpk"></g>';
}
function flow(a, b, amt) {
  amt = +amt || 0; if (amt <= 0) return; edgeAmt[a + b] = (edgeAmt[a + b] || 0) + amt; flowAmt[b] = (flowAmt[b] || 0) + amt; flowOut[a] = (flowOut[a] || 0) + amt;
  if (replaying) return; drawFlow();
  const p = $('#fe-' + a + b); if (!p) return; const L = p.getTotalLength(), c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  c.setAttribute('r', 6); c.setAttribute('fill', '#f59e0b'); c.style.filter = 'drop-shadow(0 0 4px rgba(245,158,11,.7))'; $('#fpk').appendChild(c); const t0 = performance.now();
  (function st(now) { const q = Math.min(1, (now - t0) / 1100), pt = p.getPointAtLength(L * q); c.setAttribute('cx', pt.x); c.setAttribute('cy', pt.y); if (q < 1) requestAnimationFrame(st); else { c.remove(); const g = $('#fn-' + b); if (g) { g.classList.add('flash'); setTimeout(() => g.classList.remove('flash'), 900); } } })(t0);
}
drawFlow();

// ================= trace: tree + waterfall =================
function runEl(r) {
  const el = document.createElement('div'); el.className = 'run';
  el.innerHTML = `<div class="rh"><span class="role ${r.role}">${r.role}</span><span class="lbl">${esc(r.label)}</span><span class="ms">running</span></div><div class="kids"></div>`;
  el.querySelector('.rh').addEventListener('click', () => { const k = el.querySelector('.kids'); k.style.display = k.style.display === 'none' ? '' : 'none'; });
  const tr = $('#trace'); if (tr.querySelector('.empty')) tr.innerHTML = ''; tr.prepend(el);
  while (tr.children.length > 30) tr.lastChild.remove();
  return el;
}
function addSpan(r, s) {
  s.key = r.id + ':' + r.spans.length; s.run = r.id; r.spans.push(s); spans[s.key] = s;
  const el = document.createElement('div'); el.className = 'sp ' + (s.cls || ''); el.dataset.k = s.key;
  el.innerHTML = `<div class="n"><span class="ic">${s.icon || '•'}</span>${esc(s.title)}</div><div class="bar"><i></i></div><div class="t"></div>`;
  el.addEventListener('click', () => selectSpan(s.key)); r.el.querySelector('.kids').appendChild(el); s.el = el; layoutRun(r); return s;
}
function nowT(r) { return r.end ?? (r.t0 + (performance.now() / 1000 - r.t0r)); }
function layoutRun(r) {
  const now = nowT(r), span = Math.max(1, now - r.t0);
  r.el.querySelector('.ms').textContent = r.end != null ? (r.end - r.t0).toFixed(1) + ' s' : 'running ' + (now - r.t0).toFixed(1) + ' s';
  for (const s of r.spans) { const e = s.end ?? now, i = s.el.querySelector('i');
    i.style.left = (Math.max(0, s.start - r.t0) / span * 100) + '%'; i.style.width = Math.max(1.2, (e - s.start) / span * 100) + '%';
    s.el.querySelector('.t').textContent = s.end != null ? ((s.end - s.start) < .05 ? '' : (s.end - s.start).toFixed(1) + 's') : '…'; s.el.classList.toggle('running', s.end == null); }
}
setInterval(() => Object.values(runs).forEach(r => { if (r.end == null) layoutRun(r); }), 200);

// ================= inspector (coordinated with every view) =================
function selectSpan(key, follow) {
  const s = spans[key]; if (!s) return; selected = {span: key, follow: !!follow};
  document.querySelectorAll('.sp.sel,.gn.sel').forEach(e => e.classList.remove('sel')); s.el && s.el.classList.add('sel');
  if (s.graph && s.node) { if (gKey !== s.graph) showGraph(s.graph); const g = gsvg.querySelector('#gn-' + CSS.escape(s.node)); g && g.classList.add('sel'); }
  highlightAccount(follow ? null : (s.acct || null));
  renderInspector();
}
function renderInspector() {
  if (!selected) return;
  if (selected.acct) return renderAccount(selected.acct);
  const s = spans[selected.span]; if (!s) return;
  $('#inspWhat').textContent = s.kindLabel || '';
  let h = `<div class="ih"><b>${esc(s.title)}</b>${s.model ? `<span class="chip model">${esc(s.model)}</span>` : ''}${s.driverChip || ''}${s.end != null && s.end - s.start > .05 ? `<span class="chip">${(s.end - s.start).toFixed(1)} s</span>` : ''}${s.tokens ? `<span class="chip">${s.tokens} tokens</span>` : ''}</div>`;
  if (s.what) h += `<div class="what">${esc(s.what)}</div>`;
  if (s.text) h += `<div class="sec"><div class="k">${s.end == null ? 'The model is writing' : 'What the model wrote'}</div><div class="stream" id="istream">${esc(s.text)}${s.end == null ? '<span class="cur"></span>' : ''}</div></div>`;
  else if (s.end == null && s.kind === 'node' && s.cls === 'model') h += `<div class="sec"><div class="k">The model is thinking</div><div class="stream" id="istream"><span class="cur"></span></div></div>`;
  if (s.html) h += `<div class="sec"><div class="k">Decision</div>${s.html}</div>`;
  if (s.raw) h += `<div class="sec"><div class="k">Raw event</div><pre class="raw">${esc(JSON.stringify(s.raw, null, 1).slice(0, 2400))}</pre></div>`;
  $('#insp').innerHTML = h; const st = $('#istream'); if (st) st.scrollTop = st.scrollHeight;
}
function selectAccount(id) { selected = {acct: id}; document.querySelectorAll('.sp.sel,.gn.sel').forEach(e => e.classList.remove('sel')); drawMap(); highlightAccount(id); renderInspector(); }
function highlightAccount(id) {
  const nb = new Set(); if (id) mEdges.forEach(e => { if (e.source.id === id) nb.add(e.target.id); if (e.target.id === id) nb.add(e.source.id); });
  gNodes.selectAll('g.mnode').classed('sel', d => d.id === id).classed('dim', d => !!id && d.id !== id && !nb.has(d.id) && !d.hub);
  gEdges.selectAll('line').classed('dim', d => !!id && d.source.id !== id && d.target.id !== id);
}
const acctLog = {};
function logAcct(id, text) { if (!id) return; (acctLog[id] = acctLog[id] || []).unshift({t: clock(), text}); if (acctLog[id].length > 30) acctLog[id].length = 30; if (selected && selected.acct === id && !replaying) renderInspector(); }
function renderAccount(id) {
  const n = nodeById[id]; if (!n) return; $('#inspWhat').textContent = n.hub ? 'system' : 'account';
  const es = mEdges.filter(e => e.source.id === id || e.target.id === id);
  const bought = es.filter(e => e.source.id === id).reduce((s, e) => s + e.count, 0), sold = es.filter(e => e.target.id === id).reduce((s, e) => s + e.count, 0), bad = es.reduce((s, e) => s + e.bad, 0);
  const ring = ringSets.find(r => r.members.includes(id));
  let h = `<div class="ih"><b>${esc(n.name)}</b>${n.me ? '<span class="chip model">you</span>' : ''}${n.cust ? '<span class="chip hold">AI customer</span>' : ''}${n.frozen ? '<span class="chip no">frozen</span>' : ''}${ring ? '<span class="chip no">in a ring</span>' : ''}</div>`;
  if (!n.hub) h += `<div class="vrow"><span class="nm">Owed to them</span><span>${money(n.owed)}</span></div><div class="vrow"><span class="nm">Sales (all time)</span><span>${n.sales ?? sold}</span></div>
    <div class="vrow"><span class="nm">Orders on the map</span><span>${bought} bought, ${sold} sold, ${bad} returned or charged back</span></div>${n.country ? `<div class="vrow"><span class="nm">Country</span><span>${esc(n.country)}</span></div>` : ''}`;
  else h += `<div class="what">${n.hub === 'pp' ? 'Every hold, capture, void and payout goes through PayPal (sandbox). Gold dots on the map are money moving through it.' : 'The operator: the payday agents, the fraud engines, the safety fund and the proofs.'}</div>`;
  if (ring) h += `<div class="sec"><div class="k">Why it is a ring</div><div class="what">${esc(ring.reason || '')}</div><div class="what">members: ${ring.names.map(esc).join(', ')}</div></div>`;
  if (n.persona) h += `<div class="sec"><div class="k">Persona</div><div class="what">${esc(n.persona)}</div></div>`;
  h += `<div class="sec"><div class="k">What it did this session</div>${(acctLog[id] || []).map(l => `<div class="vrow"><span class="what" style="min-width:58px">${l.t}</span><span>${l.text}</span></div>`).join('') || '<div class="what">nothing yet</div>'}</div>`;
  $('#insp').innerHTML = h;
}

// ================= activity feed =================
let nFeed = 0;
const SRC = {pp: 'PayPal', ai: 'AI', code: 'code', sim: 'sim', alp: 'Alpaca', mcp: 'MCP'};
function feed(html, cls, key, src) { if (replaying) return; nFeed++; $('#actN').textContent = nFeed + ' events';
  const el = document.createElement('div'); el.className = 'fe ' + (cls || ''); el.innerHTML = `<div class="tm">${clock().slice(0, 5)}</div><div class="tx">${html}${src ? `<span class="src ${src}">${SRC[src]}</span>` : ''}</div>`;
  if (key) el.addEventListener('click', () => key.startsWith('acct:') ? selectAccount(key.slice(5)) : selectSpan(key));
  const f = $('#feed'); f.prepend(el); while (f.children.length > 160) f.lastChild.remove(); }

// ================= per-agent copy and decisions =================
const TITLE = {club_research: 'Research (MCP)', club_reflect: 'Reflect', member_you: 'Your agent', member_priya: 'Priya\'s agent', member_marcus: 'Marcus\'s agent', member_lena: 'Lena\'s agent',
  club_discuss: 'Share picks', club_manager: 'Club manager', club_dispose: 'Limits', club_execute: 'Buy',
  signal_analyst: 'Signal analyst', risk_analyst: 'Risk analyst', bull: 'Bull', bear: 'Bear', manager: 'Manager', compliance_gate: 'Compliance', dispose: 'Dispose',
  supervisor: 'Supervisor', understand: 'Understand', search: 'Search', safety: 'Safety', select: 'Select', authorize: 'Authorize', settle: 'Settle', deliver: 'Deliver', inspect: 'Delivery inspector'};
const DOES = {club_research: 'calls the helm-market MCP server for live prices, 3-month moves and the latest news', club_reflect: 'checks how the club\'s earlier picks did and keeps a lesson for each agent',
  member_you: 'picks for you, from your note', member_priya: 'picks for Priya: steady companies that pay dividends', member_marcus: 'picks for Marcus: growth, AI chips and cloud', member_lena: 'picks for Lena: what people buy in a recession',
  club_discuss: 'shares every agent\'s picks with the others', club_manager: 'merges the final picks into one club portfolio', club_dispose: 'only listed companies, none above 35%, each person within their signed limit',
  club_execute: 'places one order per company with the broker and splits the shares by money put in',
  signal_analyst: 'reads this week\'s signal into a risk posture', risk_analyst: 'judges every creator pay or hold from their real record', bull: 'argues to pay creators fast',
  bear: 'argues for caution', manager: 'weighs the debate, sets the risk multiplier, proposes payouts', compliance_gate: 'screens every payout for sanctions and structuring',
  dispose: 'caps to the safe release and pays on PayPal', supervisor: 'decides which worker goes next', understand: 'works out what the buyer needs',
  search: 'searches creators first, then real stores', safety: 'quarantines listings that try to give the agent orders', select: 'picks the best fit inside the signed budget',
  authorize: 'checks the owner\'s ES256-signed mandate', settle: 'holds the money on PayPal until delivery', deliver: 'the seller delivers through the platform, which records the files and their hash',
  inspect: 'compares what was promised with what arrived'};
const MODEL_NODES = new Set(['club_reflect', 'member_you', 'member_priya', 'member_marcus', 'member_lena', 'club_manager', 'signal_analyst', 'risk_analyst', 'bull', 'bear', 'manager', 'understand', 'select', 'inspect']);
const vchip = v => v === 'pay' ? '<span class="chip ok">PAY</span>' : '<span class="chip hold">HOLD</span>';
const pctw = w => Object.entries(w || {}).sort((a, b) => b[1] - a[1]).map(([t, v]) => `<span class="chip">${esc(t)} ${Math.round(v * 100)}%</span>`).join(' ');
function decision(ev) {
  const n = ev.node;
  if (n === 'club_research') return (ev.mcp || []).map(c => `<div class="vrow"><span class="chip pp">MCP</span><span class="nm">${esc(c.tool)}</span><span class="rs">${esc(c.result || '')} &middot; ${c.ms} ms${c.error ? ' &middot; ' + esc(c.error) : ''}</span></div>`).join('') +
    (ev.snapshots || []).map(x => `<div class="vrow"><span class="nm">${esc(x.ticker)}</span><span class="rs">${money(x.price)} &middot; ${x.return_3m_pct > 0 ? '+' : ''}${x.return_3m_pct}% in 3 months &middot; swings ${x.volatility_pct}%/yr</span></div>`).join('') +
    (ev.news || []).map(x => `<div class="what">${esc(x.time)} &middot; ${esc((x.symbols || []).join(', '))}: ${esc(x.headline)}</div>`).join('');
  if (n === 'club_reflect') { const l = Object.entries(ev.lessons || {}); return l.length ? l.map(([m, x]) => `<div class="vrow"><span class="nm">${esc(m)}</span><span class="rs">${esc(x)}</span></div>`).join('') : '<div class="what">First round: nothing bought yet, so nothing to learn from.</div>'; }
  if (/^member_/.test(n)) return `<div><span class="chip ${ev.round === 2 ? 'model' : ''}">${ev.round === 2 ? 'round 2: after seeing the others' : 'round 1: on its own'}</span>${ev.round === 2 ? ` <span class="chip ${ev.changed ? 'hold' : 'ok'}">${ev.changed ? 'changed its pick' : 'kept its pick'}</span>` : ''}${ev.sim ? ' <span class="src sim">sim member</span>' : ''}</div><div style="margin:6px 0">${pctw(ev.weights) || '<span class="chip no">sat out</span>'}${(ev.refuses || []).length ? ` <span class="chip no">won't buy ${esc(ev.refuses.join(', '))}</span>` : ''}</div><div class="what">${esc(ev.reason || '')}</div>`;
  if (n === 'club_discuss') return `<div class="what">round ${ev.round_done} picks shared; next: ${esc(ev.going_to || '')}</div>`;
  if (n === 'club_manager') return `<div style="margin-bottom:6px">${pctw(ev.weights) || '<span class="chip no">nothing</span>'}</div><div class="what">${esc(ev.reason || '')}</div>`;
  if (n === 'club_dispose') return `<div style="margin-bottom:6px">${pctw(ev.weights)}${ev.cash_share > 0.0005 ? ` <span class="chip hold">cash ${Math.round(ev.cash_share * 100)}%</span>` : ''}</div>` +
    ((ev.cuts || []).length ? ev.cuts.map(c => `<div class="vrow"><span class="chip no">CUT</span><span class="rs">${esc(c)}</span></div>`).join('') : '<div class="what">Nothing needed cutting: the AI stayed inside every limit.</div>') +
    (ev.members || []).map(m => `<div class="vrow"><span class="nm">${esc(m.member)}${m.sim ? ' <span class="src sim">sim</span>' : ''}</span><span class="rs">${money(m.funded)} of ${money(m.asked)} &middot; ${esc(m.reason)}</span></div>`).join('');
  if (n === 'club_execute') return `<div><b>${money(ev.invested)}</b> invested on ${esc(ev.backend)} &middot; ${ev.routed || 0} orders sent to Alpaca${ev.cash > 0.5 ? ` &middot; ${money(ev.cash)} kept as cash` : ''}</div>` +
    (ev.fills || []).map(f => `<div class="vrow"><span class="nm">${esc(f.ticker)}</span><span class="rs">${money(f.notional)} at ${money(f.price)} = ${f.units} shares${f.routed_to_alpaca ? ' &middot; Alpaca paper order' : ''}</span></div>`).join('') +
    (ev.shares || []).map(x => `<div class="vrow"><span class="nm">${esc(x.member)}${x.sim ? ' <span class="src sim">sim</span>' : ''}</span><span class="rs">${money(x.invested)} in ${Object.keys(x.holdings || {}).join(', ')}${(x.refused || []).length ? ' &middot; none in ' + esc(x.refused.join(', ')) : ''}</span></div>`).join('');
  if (n === 'signal_analyst') return `<div>${ev.caution ? '<span class="chip hold">caution</span>' : '<span class="chip ok">calm</span>'} ${ev.creators_in_view} creators in view ${ev.read ? '&middot; ' + esc(ev.read) : ''}</div>`;
  if (n === 'risk_analyst') return (ev.verdicts || []).map(v => `<div class="vrow">${vchip(v.verdict)}<span class="nm">${esc(v.creator)}</span><span class="rs">${esc(v.reason)}</span></div>`).join('');
  if (n === 'bull' || n === 'bear') return `<div class="quote ${n}">&ldquo;${esc(ev.argument)}&rdquo;</div><div style="margin-top:4px"><span class="chip ${n === 'bull' ? 'ok' : 'no'}">pushes risk ${Number(ev.pushes).toFixed(2)}&times;</span></div>`;
  if (n === 'manager') return `<div><span class="big">${Number(ev.risk_multiplier).toFixed(2)}&times;</span> <span class="what">risk multiplier</span></div><div class="what">proposes ${money(ev.proposed_total)}: ${(ev.proposal || []).map(p => esc(p.creator) + ' ' + money(p.amount)).join(', ')}</div>`;
  if (n === 'compliance_gate') return (ev.screened || []).map(s => `<span class="chip ${s.decision === 'allow' ? 'ok' : 'no'}">${esc(s.creator)}: ${esc(s.decision)}</span> `).join('') || '<span class="what">nothing to screen</span>';
  if (n === 'dispose') return `<div><span class="chip ${ev.status === 'completed' ? 'ok' : 'no'}">${esc(ev.status)}</span> paid <b>${money(ev.paid_total)}</b> &middot; safe release ${money(ev.safe_release_total)} &middot; proposed ${money(ev.proposed_total)}</div>` +
    ((ev.guardrail_overrides || []).length ? `<div class="what" style="color:var(--warn)">guardrail: ${esc(ev.guardrail_overrides.join('; '))}</div>` : '') +
    (ev.status !== 'completed' && ev.message ? `<div class="what" style="color:var(--bad)">${esc(ev.message)}${/INSUFFICIENT_FUNDS/.test(ev.message) ? ': the platform PayPal sandbox balance is empty, so nothing was paid' : ''}</div>` : '') +
    (ev.paid || []).map(p => `<div class="vrow"><span class="chip ${ev.status === 'completed' ? 'ok' : 'no'}">${ev.status === 'completed' ? 'PAID' : 'NOT SENT'}</span><span class="nm">${esc(p.creator)}</span><span class="rs">${money(p.amount)}</span></div>`).join('');
  if (n === 'understand') { const i = ev.intent || {}; return `<div>looking for <b>${esc(i.query)}</b> <span class="chip">${esc(i.category)}</span> <span class="chip">&le; ${money(i.max_price)}</span></div>`; }
  if (n === 'search') return `<div class="what">${ev.found} options from ${esc(ev.backend)}</div>` + (ev.top || []).map(p => `<div class="vrow"><span class="chip ${p.source === 'marketplace' ? 'ok' : ''}">${p.source === 'marketplace' ? 'creator' : 'store'}</span><span class="nm">${esc(p.title)}</span><span class="rs">${money(p.price)} &middot; ${esc(p.merchant)}</span></div>`).join('');
  if (n === 'safety') return (ev.quarantined || []).length ? ev.quarantined.map(q => `<div class="vrow"><span class="chip no">QUARANTINED</span><span class="rs">${esc(q)}</span></div>`).join('') + `<div class="what">${ev.clean} clean listings go on; the model never sees the poisoned one</div>` : `<div class="what">all ${ev.clean} listings clean</div>`;
  if (n === 'select') { const c = ev.choice || {}; return c.declined || !c.title ? `<div><span class="chip no">declined</span> <span class="what">${esc(c.reason)}</span></div>` : `<div><b>${esc(c.title)}</b> by ${esc(c.merchant)} &middot; <b>${money(c.price)}</b></div><div class="what">${esc(c.reason)}</div>`; }
  if (n === 'authorize') { const a = ev.authorization || {}; return `<div><span class="chip ${a.allowed ? 'ok' : 'no'}">${a.allowed ? 'mandate admits' : 'mandate refuses'}</span> <span class="what">${esc(a.reason)}</span></div>`; }
  if (n === 'deliver') { const d = ev.delivery || {}; return d.kind === 'download' ? `<div><b>${esc(d.archive)}</b> &middot; ${(d.files || []).length} files &middot; ${(d.bytes / 1e6).toFixed(2)} MB</div><div class="what">${(d.files || []).map(f => esc(f.name)).slice(0, 6).join(', ')}</div><div class="what">sha256 ${esc(d.sha256 || '')}</div>` : `<div>${esc(d.carrier || '')} ${esc(d.tracking || '')} &middot; ${esc(d.status || '')} <span class="src sim">sim</span></div>`; }
  if (n === 'inspect') { const v = VERD[ev.verdict] || VERD.unverified; return `<div><span class="chip ${v[0]}">${v[1]}</span> <span class="what">${esc(ev.reason || '')}</span></div>` + (ev.checks || []).map(c => `<div class="vrow"><span class="rs">&check; ${esc(c)}</span></div>`).join('') + (ev.error ? `<div class="what" style="color:var(--bad)">${esc(ev.error)}</div>` : ''); }
  if (n === 'settle') return `<div><span class="chip ${ev.status === 'held' ? 'ok' : 'no'}">${esc(ev.status)}</span> ${ev.payee ? 'payee <b>' + esc(ev.payee) + '</b>' : ''}</div>${ev.authorization_id ? `<div class="what">PayPal authorization ${esc(ev.authorization_id)}</div>` : ''}`;
  return '';
}
function oneLine(ev) {
  const n = ev.node;
  const top = w => Object.entries(w || {}).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([t, v]) => `${t} ${Math.round(v * 100)}%`).join(', ');
  if (n === 'club_research') return `${(ev.snapshots || []).length} companies and ${(ev.news || []).length}+ headlines over MCP`;
  if (/^member_/.test(n)) return `round ${ev.round}${ev.round === 2 ? (ev.changed ? ', changed' : ', kept') : ''}: ${top(ev.weights) || 'sat out'}`;
  if (n === 'club_manager') return `club portfolio: ${top(ev.weights)}`;
  if (n === 'club_dispose') return (ev.cuts || []).length ? `${ev.cuts.length} cut: ${ev.cuts[0]}` : 'inside every limit';
  if (n === 'club_execute') return `bought ${money(ev.invested)} across ${(ev.fills || []).length} companies`;
  if (n === 'risk_analyst') { const v = ev.verdicts || []; return `${v.filter(x => x.verdict === 'pay').length} to pay, ${v.filter(x => x.verdict !== 'pay').length} to hold`; }
  if (n === 'bull' || n === 'bear') return `pushes risk ${Number(ev.pushes).toFixed(2)}x`;
  if (n === 'manager') return `${Number(ev.risk_multiplier).toFixed(2)}x risk, proposes ${money(ev.proposed_total)}`;
  if (n === 'dispose') return ev.status === 'completed' ? `paid ${money(ev.paid_total)} of ${money(ev.proposed_total)} on PayPal (cap ${money(ev.safe_release_total)})` : `not sent: ${ev.message || ev.status}`;
  if (n === 'understand') return `looking for ${(ev.intent || {}).query || ''}`;
  if (n === 'search') return `${ev.found} options from ${ev.backend}`;
  if (n === 'safety') return (ev.quarantined || []).length ? `quarantined ${ev.quarantined.length} poisoned listing` : 'all listings clean';
  if (n === 'select') { const c = ev.choice || {}; return c.title ? `picked ${c.title} at ${money(c.price)}` : 'declined'; }
  if (n === 'authorize') return (ev.authorization || {}).allowed ? 'mandate admits it' : 'mandate refuses';
  if (n === 'settle') return ev.status === 'held' ? 'PayPal holds the money' : ev.status;
  if (n === 'deliver') { const d = ev.delivery || {}; return d.kind === 'download' ? `${ev.title}: ${(d.files || []).length} files, ${(d.bytes / 1e6).toFixed(2)} MB` : `${ev.title}: shipped, ${d.carrier} ${d.tracking}`; }
  if (n === 'inspect') return `${ev.title}: ${(VERD[ev.verdict] || VERD.unverified)[1]}. ${ev.reason || ''}`;
  return '';
}
function ppName(path, status, auth) {
  if (/\/v2\/checkout\/orders$/.test(path) && auth) return 'Orders v2: card approved, money held';
  if (/\/v2\/checkout\/orders$/.test(path) && status === 'COMPLETED') return 'Orders v2: paid and captured';
  if (/\/v1\/payments\/payouts/.test(path)) return 'Payouts: batch to creators';
  if (/\/authorize$/.test(path)) return 'Orders: authorize (hold)'; if (/\/capture$/.test(path)) return 'Capture: release to the seller';
  if (/\/void$/.test(path)) return 'Void: money back to the buyer'; if (/\/refund$/.test(path)) return 'Refund';
  if (/\/v1\/catalogs\/products/.test(path)) return 'Catalog: new product';
  if (/\/v2\/checkout\/orders$/.test(path)) return 'Orders v2: create'; if (/dispute/.test(path)) return 'Disputes'; return path;
}

// ================= the event handler =================
function follow(s) { if (replaying) return; if (!selected || selected.follow || (selected.span && spans[selected.span] && spans[selected.span].end != null && !selected.acct)) selectSpan(s.key, true); }
function onEvent(ev) {
  const r = runs[ev.run];
  switch (ev.kind) {
    case 'hello': renderBooks(ev.account); setGraph(ev.graph); replaying = true; try { (ev.history || []).forEach(onEvent); } finally { replaying = false; } drawFlow(); showGraph(gKey, true);
      active = ev.busy || 0; break;
    case 'run_start': {
      const R = runs[ev.run] = {id: ev.run, action: ev.action, role: ev.role, label: ev.label, t0: ev.t, t0r: performance.now() / 1000, spans: [], cur: {}};
      R.el = runEl(R); if (!replaying) active++;
const k = {buy: 'buyer', payday: 'operator', club: 'club', customers: 'market', scan: 'fraud'}[ev.action];
      if (k) { resetGraph(k); liveG[k] = !replaying; if (!replaying) { showGraph(k, true); if (view !== 'map') setView('map'); } }
      if (ev.action === 'buy') { glow(ME(), true); bubble(ME(), 'my buyer agent is shopping…', 'buyer', 30000); $('#gCap').innerHTML = `<b>Buyer agents</b> are working on &ldquo;${esc((ev.params || {}).need || '')}&rdquo;`; }
      if (ev.action === 'payday') { bubble('PLATFORM', 'payday: agents deciding…', 'operator', 40000); glow('PLATFORM', true); $('#gCap').innerHTML = '<b>Payday</b>: the operator agents are deciding who gets paid'; }
      if (ev.action === 'customers') $('#gCap').innerHTML = '<b>AI customers</b> take their turn on the marketplace';
      if (ev.action === 'scan') { bubble('PLATFORM', 'scanning for fraud…', 'operator', 15000); gNode('fraud', 'abuse', 'running'); gNode('fraud', 'linkage', 'running'); $('#gCap').innerHTML = '<b>Fraud engines</b> read the whole sales history'; }
      if (ev.action === 'my_page') bubble(ME(), 'my AI manager is reviewing my sales…', 'creator', 30000);
      if (ev.action === 'advance') bubble(ME(), 'asking for an advance…', 'creator', 15000);
      if (ev.action === 'club') { bubble(ME(), 'my club is deciding together…', 'creator', 30000); $('#gCap').innerHTML = '<b>Investment club</b>: four agents read the news over MCP and pick together'; }
      if (ev.action === 'dispute') bubble(ME(), 'a buyer opened a dispute', 'bad', 9000);
      if (ev.action === 'prove') bubble('PLATFORM', 'proving solvency in zero knowledge…', 'operator', 12000);
      if (ev.action === 'confirm' || ev.action === 'reject') bubble(ME(), ev.action === 'confirm' ? 'confirmed delivery' : 'reported a failed delivery', 'buyer', 6000);
      gtabs(); feed(`<span class="role ${ev.role}">${ev.role}</span> <b>${esc(ev.label)}</b>`, '', null);
      break; }
    case 'node_start': {
      if (!r) break; const k = ev.graph === 'buyer' ? 'buyer' : (ev.graph === 'club' ? 'club' : 'operator');
      if (k === 'club' && /^member_/.test(ev.node)) gPacket(k, lastG[k] === 'club_discuss' ? 'club_discuss' : 'club_reflect', ev.node); else if (lastG[k]) gPacket(k, lastG[k], ev.node);
      if (!(k === 'club' && /^member_/.test(ev.node))) lastG[k] = ev.node; gNode(k, ev.node, 'running');
      if (ev.node === 'supervisor') break;
      const isM = MODEL_NODES.has(ev.node);
      const s = addSpan(r, {kind: 'node', node: ev.node, graph: k, title: TITLE[ev.node] || ev.node, start: ev.t, end: null, cls: isM ? 'model' : 'code', icon: isM ? '✦' : '⚙',
        what: DOES[ev.node], kindLabel: isM ? 'AI agent' : 'deterministic code', driverChip: `<span class="chip ${isM ? 'model' : 'code'}">${isM ? 'AI model' : 'deterministic code'}</span>`, text: ''});
      r.cur[ev.node] = s;
      if (!replaying) { $('#gCap').innerHTML = `<b>${esc(TITLE[ev.node] || ev.node)}</b> ${esc(DOES[ev.node] || '')}&hellip;`; follow(s); }
      break; }
    case 'model_start': { const s = r && r.cur[ev.node]; if (s) { s.model = ev.model + ' · ' + ev.tool + '()'; if (s.graph) gBadge(s.graph, s.node, 'thinking…'); if (selected && selected.span === s.key && !replaying) renderInspector(); } break; }
    case 'token': { const s = r && r.cur[ev.node]; if (!s) break; s.text += ev.text; if (s.text.length > 4000) s.text = '…' + s.text.slice(-3000); if (s.graph) gBadge(s.graph, s.node, 'writing…');
      if (selected && selected.span === s.key && !replaying) { const st = $('#istream'); if (st) { const c = st.querySelector('.cur'); c && c.remove(); st.append(document.createTextNode(ev.text)); st.insertAdjacentHTML('beforeend', '<span class="cur"></span>'); st.scrollTop = st.scrollHeight; } else renderInspector(); }
      break; }
    case 'model_end': { const s = r && r.cur[ev.node]; if (s && ev.tokens) s.tokens = (s.tokens || 0) + ev.tokens; break; }
    case 'node_end': {
      if (!r) break; const k = ev.graph === 'buyer' ? 'buyer' : (ev.graph === 'club' ? 'club' : 'operator');
      gNode(k, ev.node, ev.driver === 'fallback' ? 'fallback' : (ev.node === 'safety' && (ev.quarantined || []).length ? 'blocked' : 'done'));
      gBadge(k, ev.node, ev.ms != null ? (ev.ms / 1000).toFixed(1) + 's' : '');
      if (ev.node === 'supervisor') { if (ev.route && ev.route !== 'done' && !replaying) $('#gCap').innerHTML = `<b>Supervisor</b> routes to <b>${esc(ev.route)}</b>`; break; }
      const s = r.cur[ev.node]; if (s) { s.end = ev.t; s.html = decision(ev); s.raw = ev; if (ev.driver === 'fallback') s.driverChip += ' <span class="chip hold">fallback</span>'; layoutRun(r); if (selected && selected.span === s.key && !replaying) renderInspector(); }
      const line = oneLine(ev); if (line) feed(`<b>${esc(TITLE[ev.node])}</b> ${esc(line)}`, ev.node === 'safety' && (ev.quarantined || []).length ? 'bad' : (ev.node === 'dispose' && ev.status === 'completed' ? 'good' : ''), s && s.key, MODEL_NODES.has(ev.node) && ev.driver !== 'fallback' ? 'ai' : 'code');
      if (ev.node === 'dispose' && ev.status === 'completed') (ev.paid || []).forEach(p => ledgerAdd({what: 'Payout to a creator', from: 'Helm platform', to: p.creator, amount: p.amount, rail: 'PayPal Payouts', status: 'sent'}));
      if (ev.node === 'select' && (ev.choice || {}).title) bubble(ME(), `picked ${ev.choice.title} · ${money(ev.choice.price)}`, 'buyer', 9000);
      if (ev.node === 'risk_analyst') (ev.verdicts || []).forEach(v => { const id = idFromLabel(v.creator); if (id) { bubble(id, v.verdict === 'pay' ? 'risk analyst: pay' : 'risk analyst: hold', v.verdict === 'pay' ? 'creator' : 'bad', 9000); logAcct(id, `risk analyst said <b>${esc(v.verdict)}</b>: ${esc(v.reason)}`); } });
      if (ev.node === 'dispose' && ev.status === 'completed') (ev.paid || []).forEach((p, i) => { const id = idFromLabel(p.creator); if (!id) return; logAcct(id, `paid <b>${money(p.amount)}</b> by PayPal Payouts`); flow('payouts', 'paid', p.amount);
        if (!replaying) setTimeout(() => { pulse('PLATFORM', 'PAYPAL'); setTimeout(() => pulse('PAYPAL', id), 900); bubble(id, `paid ${money(p.amount)} via PayPal Payouts`, 'money', 9000); }, i * 500); });
      break; }
    case 'paypal': {
      if (!r) break; const ok = ev.http && ev.http < 400, name = ppName(ev.path || '', ev.status, ev.authorization);
      const s = addSpan(r, {kind: 'paypal', title: 'PayPal ' + name, start: ev.t, end: ev.t, cls: ok ? 'pp' : 'bad', icon: '$', kindLabel: 'PayPal API call',
        driverChip: `<span class="chip ${ok ? 'pp' : 'no'}">HTTP ${esc(ev.http)}</span>`, what: `${ev.method || 'POST'} ${ev.path}${ev.amount != null ? ' · ' + money(ev.amount) : ''}${ev.payee ? ' · to ' + ev.payee : ''}`,
        html: `${ev.id ? `<div class="vrow"><span class="nm">id</span><span>${esc(ev.id)}</span></div>` : ''}${ev.status ? `<div class="vrow"><span class="nm">status</span><span>${esc(ev.status)}</span></div>` : ''}${ev.authorization ? `<div class="vrow"><span class="nm">authorization</span><span>${esc(ev.authorization)}</span></div>` : ''}${ev.issue ? `<div class="vrow"><span class="nm">PayPal said</span><span style="color:var(--bad)">${esc(ev.issue)}</span></div>` : ''}`, raw: ev});
      feed(`PayPal <b>${esc(name)}</b> ${ok ? '' : 'failed '}HTTP ${esc(ev.http)}${ev.amount != null ? ' · ' + money(ev.amount) : ''}${ev.issue ? ' · ' + esc(ev.issue) : ''}`, ok ? 'pp' : 'bad', s.key, 'pp');
      ledgerAdd({what: 'PayPal ' + name, from: {customers: 'an AI customer', buy: 'You (buyer)', confirm: 'PayPal hold', reject: 'PayPal hold', payday: 'Helm platform', sell: 'You'}[r.action] || '', to: ev.payee || (r.action === 'sell' ? 'PayPal Catalog' : ''), amount: ev.amount != null ? +ev.amount : null, rail: 'PayPal sandbox', id: ev.id || '', status: ok ? (ev.status || 'HTTP ' + ev.http) : (ev.issue || 'HTTP ' + ev.http), bad: !ok});
      gFlash(r.action === 'payday' ? 'operator' : 'buyer', 'paypal');
      if (ok && /\/v2\/checkout\/orders$/.test(ev.path) && ev.status === 'COMPLETED' && !ev.authorization) { flow('buyers', 'hold', ev.amount); setTimeout(() => { flow('hold', 'earn', ev.amount * .9); flow('hold', 'fee', ev.amount * .1); }, 1100); }
      else if (ok && /\/v2\/checkout\/orders$/.test(ev.path)) { flow('buyers', 'hold', ev.amount); pulse(ME(), 'PAYPAL'); }
      if (ok && /\/v1\/payments\/payouts/.test(ev.path)) flow('fund', 'payouts', ev.amount);
      break; }
    case 'mcp': {
      if (!r) break; const s = addSpan(r, {kind: 'mcp', title: 'MCP ' + ev.tool, start: ev.t, end: ev.t, cls: ev.error ? 'bad' : 'pp', icon: '⇄', kindLabel: 'MCP tool call (stdio)',
        driverChip: `<span class="chip pp">${esc(ev.server)}</span>`, what: `${ev.items} items in ${ev.ms} ms`, html: `<div class="vrow"><span class="nm">args</span><span class="rs">${esc(JSON.stringify(ev.args || {}))}</span></div>${ev.error ? `<div class="what" style="color:var(--bad)">${esc(ev.error)}</div>` : ''}`, raw: ev});
      gFlash('club', 'mcp'); feed(`MCP <b>${esc(ev.tool)}</b> on ${esc(ev.server)}: ${ev.items} items`, ev.error ? 'bad' : '', s.key, 'mcp'); break; }
    case 'broker': {
      if (!r) break; const s = addSpan(r, {kind: 'broker', title: `Buy ${ev.ticker} ${money(ev.notional)}`, start: ev.t, end: ev.t, cls: 'pp', icon: '$', kindLabel: 'broker order',
        driverChip: `<span class="chip pp">${ev.routed ? 'Alpaca paper' : esc(ev.backend)}</span>`, what: `${ev.units} shares at ${money(ev.price)}`, raw: ev});
      gFlash('club', 'broker'); feed(`Broker: <b>${esc(ev.ticker)}</b> ${money(ev.notional)} at ${money(ev.price)}${ev.routed ? ' (Alpaca paper order)' : ''}`, '', s.key, 'alp');
      ledgerAdd({what: 'Club buys ' + ev.ticker, from: 'Investment club', to: ev.ticker, amount: ev.notional, rail: ev.routed ? 'Alpaca paper' : 'live price (paper)', status: ev.units + ' shares'}); break; }
    case 'guard': {
      const s = r && addSpan(r, {kind: 'guard', title: 'Blocked: ' + (ev.what || 'guardrail'), start: ev.t, end: ev.t, cls: 'bad', icon: '⛔', kindLabel: 'guardrail',
        what: `“${ev.sample || ''}”`, html: (ev.words || []).length ? `<div class="what">tripped on: ${ev.words.map(esc).join(', ')}</div><div class="what">The listing is quarantined before any model reads it.</div>` : '', raw: ev});
      ['buyer', 'operator'].forEach(k => gFlash(k, 'guard'));
      feed(`<b>Blocked</b> ${esc(ev.what)}: &ldquo;${esc((ev.sample || '').slice(0, 70))}&rdquo;`, 'bad', s && s.key, 'code'); break; }
    case 'direct': {
      const W = {opened: ['Opened', 'buyer', 'code'], bought: ['Bought', 'buyer', 'pp'], repriced: ['Repriced', 'creator', 'code'], delisted: ['Took down', 'creator', 'code'], frozen: ['Froze', 'bad', 'code'], cleared: ['Cleared', 'creator', 'code']}[ev.what] || [ev.what, '', 'code'];
      const txt = ev.what === 'opened' ? `${ev.title} from ${ev.merchant}: access logged from ${ev.ip} as proof of delivery` : ev.what === 'bought' ? `${ev.title} from ${ev.merchant} · ${money(ev.price)} held on PayPal` : ev.what === 'repriced' ? `${ev.title}: ${money(ev.old)} → ${money(ev.price)}` : ev.what === 'frozen' || ev.what === 'cleared' ? `${ev.title} (${money(ev.price)} owed)` : ev.title;
      const s = r && addSpan(r, {kind: 'direct', title: `${W[0]} ${ev.title}`, start: ev.t, end: ev.t, cls: ev.what === 'frozen' ? 'bad' : ev.what === 'bought' ? 'pp' : 'code', icon: '●', kindLabel: 'your own action', html: `<div>${esc(txt)}</div>`, raw: ev});
      if (ev.what === 'bought') { bubble(ME(), `bought ${ev.title}`, 'money', 9000); if (ev.seller) logAcct(ev.seller, `you bought <b>${esc(ev.title)}</b> (${money(ev.price)} held)`); }
      if (ev.what === 'frozen' || ev.what === 'cleared') { const n = nodeById[ev.account]; if (n) { n.frozen = ev.what === 'frozen'; drawMap(); } bubble(ev.account, ev.what === 'frozen' ? 'frozen by the operator' : 'cleared by the operator', ev.what === 'frozen' ? 'bad' : 'creator', 9000); logAcct(ev.account, `${ev.what} by the operator`); }
      if (ev.what === 'frozen') ledgerAdd({what: 'Earnings frozen (review)', from: ev.title, to: 'held by platform', amount: ev.price, rail: 'operator', status: 'frozen', bad: true});
      feed(`<b>${esc(W[0])}</b> ${esc(txt)}`, W[1] === 'bad' ? 'bad' : W[2] === 'pp' ? 'pp' : 'good', s && s.key, W[2] === 'pp' ? 'pp' : 'code'); break; }
    case 'listing': {
      const s = r && addSpan(r, {kind: 'listing', title: `Listed ${ev.title}`, start: ev.t, end: ev.t, cls: 'pp', icon: '+', kindLabel: 'your new listing',
        html: `<div><b>${esc(ev.title)}</b> &middot; ${money(ev.price)} <span class="chip">${esc(ev.category)}</span></div><div class="what">${ev.paypal_product ? 'PayPal Catalog product ' + esc(ev.paypal_product) : 'not registered with PayPal'}. Buyer agents looking for ${esc(ev.category)} and the AI customers can buy it now.</div>`, raw: ev});
      if (s) follow(s); bubble(ME(), `listed ${ev.title} · ${money(ev.price)}`, 'creator', 9000); logAcct(ME(), `listed <b>${esc(ev.title)}</b> at ${money(ev.price)}`);
      ledgerAdd({what: 'Listed for sale', from: '', to: 'You', amount: ev.price, rail: ev.paypal_product ? 'PayPal Catalog' : 'marketplace (sim)', id: ev.paypal_product || ev.id, status: ev.title});
      feed(`<b>You listed</b> ${esc(ev.title)} at ${money(ev.price)}`, 'good', s && s.key, ev.paypal_product ? 'pp' : 'sim'); break; }
    case 'actor_start': {
      if (!r) break; const n = addNode(ev.id, ev.name, {}); n.cust = true; n.persona = ev.persona; if (!replaying) drawMap();
      addCustomer(ev.id, ev.name, ev.persona); gNode('market', 'c_' + ev.id, 'running'); gPacket('market', 'hub', 'c_' + ev.id, '#ea580c'); glow(ev.id, true);
      bubble(ev.id, 'deciding…', 'market', 20000);
      const s = addSpan(r, {kind: 'actor', node: 'c_' + ev.id, graph: 'market', acct: ev.id, title: ev.name, start: ev.t, end: null, cls: 'actor', icon: '☻', kindLabel: 'AI customer', what: ev.persona, text: ''});
      r.cur['cust:' + ev.id] = s; follow(s); break; }
    case 'actor': {
      const dchip = ev.driver === 'error' ? ' <span class="chip hold">model did not answer</span>' : ev.driver === 'sim' ? ' <span class="chip hold">simulated, no model key</span>' : '';
      const s = r && r.cur['cust:' + ev.id]; if (s) { s.end = ev.t; s.html = `<div><span class="chip ${ev.action === 'return' ? 'no' : ev.action === 'buy' ? 'ok' : ''}">${esc(ev.action)}</span>${dchip} ${esc(ev.outcome)}</div><div class="what">${esc(ev.reason)}</div>`; s.raw = ev; layoutRun(r); if (selected && selected.span === s.key && !replaying) renderInspector(); }
      gNode('market', 'c_' + ev.id, ev.driver && ev.driver !== 'llm' ? 'fallback' : ev.action === 'return' ? 'blocked' : 'done'); glow(ev.id, false); if (s) gBadge('market', 'c_' + ev.id, (s.end - s.start).toFixed(1) + 's');
      const out = String(ev.outcome || '').replace(ev.name + ' ', '');
      bubble(ev.id, out, ev.action === 'return' ? 'bad' : 'market', 9000); logAcct(ev.id, `${esc(ev.outcome)}${ev.reason ? ' &middot; <span class="what">' + esc(ev.reason) + '</span>' : ''}`);
      feed(`<b>${esc(ev.name)}</b> ${esc(out)}${ev.driver === 'error' ? ' (the model did not answer)' : ''}`, ev.action === 'return' ? 'bad' : '', 'acct:' + ev.id, ev.driver === 'llm' || !ev.driver ? 'ai' : ev.driver === 'sim' ? 'sim' : 'code'); break; }
    case 'orders': (ev.orders || []).forEach(o => { const nm = id => id === ME() ? 'You' : ((nodeById[id] || {}).name || id);
        ledgerAdd({what: o.status === 'returned' ? 'Return' : o.status === 'charged_back' ? 'Chargeback' : o.new ? 'Sale' : o.status, from: nm(o.buyer), to: nm(o.seller), amount: o.amount, rail: 'marketplace (sim)', id: o.id, status: o.status, bad: o.status === 'returned' || o.status === 'charged_back'}); });
      (ev.orders || []).forEach((o, i) => {
        const go = () => { if (!nodeById[o.buyer] || !nodeById[o.seller]) return;
          if (o.status === 'returned' || o.status === 'charged_back') { pulse(o.seller, o.buyer, 'bad'); logAcct(o.seller, `${esc(o.status.replace('_', ' '))} ${money(o.amount)}`); }
          else if (o.new) { pulse(o.buyer, 'PAYPAL'); setTimeout(() => pulse('PAYPAL', o.seller), 850); logAcct(o.seller, `sold ${money(o.amount)} to ${esc((nodeById[o.buyer] || {}).name)}`); logAcct(o.buyer, `bought ${money(o.amount)} from ${esc((nodeById[o.seller] || {}).name)}`); } };
        replaying ? go() : setTimeout(go, i * 250); }); break;
    case 'scan': {
      ringSets = (ev.rings || []).map(g => ({members: g.members, names: g.names || [], reason: g.reason, label: `ring: ${(g.members || []).length} accounts, one person`}));
      ringSets.forEach(g => g.members.forEach((m, i) => { if (nodeById[m]) nodeById[m].frozen = true; if (!nodeById[m]) addNode(m, g.names[i] || m, {}); bubble(m, 'linked: same device and card', 'bad', 10000); logAcct(m, 'flagged as part of a ring and frozen'); }));
      (ev.verdicts || []).forEach(v => logAcct(v.account, `<b>${esc(v.action)}</b>: ${esc(v.reason)}`));
      drawMap(); drawRings(); ['abuse', 'linkage'].forEach(n => gNode('fraud', n, 'done')); gPacket('fraud', 'linkage', 'freeze', '#dc2626'); gPacket('fraud', 'abuse', 'freeze', '#dc2626'); gNode('fraud', 'freeze', 'blocked'); gNode('fraud', 'guard', 'blocked');
      if (ev.frozen) flow('earn', 'frozen', ev.frozen);
      const s = r && addSpan(r, {kind: 'scan', node: 'linkage', graph: 'fraud', title: `${ringSets.length} rings, ${(ev.suspended || []).length} suspended`, start: ev.t, end: ev.t, cls: 'bad', icon: '⛓', kindLabel: 'fraud engines',
        html: ringSets.map(g => `<div class="vrow"><span class="chip no">ring</span><span class="rs">${g.names.map(esc).join(', ')}: ${esc(g.reason)}</span></div>`).join('') + (ev.verdicts || []).map(v => `<div class="vrow"><span class="chip hold">${esc(v.action)}</span><span class="nm">${esc(v.name)}</span><span class="rs">${esc(v.reason)}</span></div>`).join(''), raw: ev});
      if (s) follow(s);
      feed(`<b>Fraud scan</b>: ${ringSets.length} rings found, ${money(ev.frozen)} frozen`, 'bad', s && s.key, 'code');
      if (!replaying) $('#mapCap').innerHTML = `<b>Fraud scan</b> &middot; ${ringSets.length} rings circled in red (accounts sharing one device, card and IP), ${money(ev.frozen)} frozen`;
      if (ev.frozen) ledgerAdd({what: 'Earnings frozen (fraud)', from: 'ring members', to: 'held by platform', amount: ev.frozen, rail: 'fraud engines', status: (ev.suspended || []).length + ' suspended', bad: true}); break; }
    case 'result': {
      const o = ev.out || {};
      if (ev.action === 'confirm' || ev.action === 'reject') { const sale = o.sale || {};
        if (ev.action === 'confirm' && sale.seller_net != null) { flow('hold', 'earn', sale.seller_net); flow('hold', 'fee', sale.platform_fee); }
        if (ev.action === 'reject') flow('hold', 'buyers', (sale.gross || o.amount || 0));
        feed(`<b>${ev.action === 'confirm' ? 'Delivery confirmed' : 'Delivery failed'}</b>: ${esc(o.status || '')}${sale.seller_net != null ? ` · ${money(sale.seller_net)} to the creator, ${money(sale.platform_fee)} fee` : ''}`, ev.action === 'confirm' ? 'good' : 'bad'); }
      if (ev.action === 'dispute') { const cb = o.chargeback || {}; flow('earn', 'clawed', cb.clawed); bubble(ME(), `clawed back ${money(cb.clawed)}`, 'bad', 9000);
        if (r) follow(addSpan(r, {kind: 'dispute', title: 'PayPal dispute: chargeback', start: ev.t, end: ev.t, cls: 'bad', icon: '↩', kindLabel: 'PayPal dispute (simulated webhook)', html: `<div><b>${money(cb.clawed)}</b> clawed back from the seller</div><div class="what">evidence: ${esc(o.evidence || o.reason || '')}</div>`, raw: o}));
        feed(`<b>Dispute</b>: ${money(cb.clawed)} clawed back with evidence from the receipt chain`, 'bad', null, 'sim');
        ledgerAdd({what: 'Chargeback', from: 'You', to: 'the buyer', amount: cb.clawed, rail: 'dispute (sim webhook)', status: 'clawed back', bad: true}); }
      if (ev.action === 'advance') { const tk = o.taken || {}; if (tk.status && tk.status !== 'rejected') flow('fund', 'adv', tk.amount || o.offer);
        if (r) follow(addSpan(r, {kind: 'advance', title: o.eligible ? `Offer ${money(o.offer)}` : 'No safe offer', start: ev.t, end: ev.t, cls: 'code', icon: '⚙', kindLabel: 'advance pricing (code)', html: `<div class="vrow"><span class="nm">Proven earnings</span><span>${money(o.proven_earnings)}</span></div><div class="vrow"><span class="nm">Default risk</span><span>${((o.pd || 0) * 100).toFixed(1)}%</span></div>${o.pd_band ? `<div class="vrow"><span class="nm">Could really be</span><span>${(o.pd_band.low * 100).toFixed(0)}% to ${(o.pd_band.high * 100).toFixed(0)}%</span></div>` : ''}${o.max_amount != null && o.max_amount - o.offer > 0.5 ? `<div class="vrow"><span class="nm">Cut for uncertainty</span><span>${money(o.max_amount)} &rarr; ${money(o.offer)}</span></div>` : ''}<div class="vrow"><span class="nm">Fee</span><span>${((o.fee_rate || 0) * 100).toFixed(1)}%</span></div><div class="vrow"><span class="nm">Taken</span><span>${esc(tk.status || 'no')} ${tk.amount ? money(tk.amount) : ''}</span></div><div class="what">${esc(o.reason)}</div>`, raw: o}));
        bubble(ME(), o.eligible ? `advance ${esc(tk.status || 'offered')}: ${money(tk.amount || o.offer)}` : 'no safe advance', 'creator', 9000);
        feed(`<b>Advance</b>: offer ${money(o.offer)} (default risk ${((o.pd || 0) * 100).toFixed(0)}%), ${esc(tk.status || 'not taken')}`, 'good', null, 'code');
        if (tk.status && tk.status !== 'rejected') ledgerAdd({what: 'Advance', from: 'Safety fund', to: 'You', amount: tk.amount || o.offer, rail: 'loan book (sim)', status: tk.status}); }
      if (ev.action === 'my_page') { const b = o.briefing; const txt = typeof b === 'string' ? b : (b && (b.text || b.summary || b.briefing)) || JSON.stringify(b || {});
        if (r) follow(addSpan(r, {kind: 'brief', title: 'Your AI manager\'s briefing', start: r.t0, end: ev.t, cls: 'model', icon: '✦', kindLabel: 'AI agent', html: `<div class="quote">${esc(txt)}</div>` + (Array.isArray(o.recommendations) ? o.recommendations.map(x => [null, x]) : Object.entries(o.recommendations || {})).slice(0, 6).map(([k, x]) => `<div class="vrow"><span class="nm">${esc(k ? k.replace(/_/g, ' ') : 'next')}</span><span class="rs">${esc(Array.isArray(x) ? x.join(', ') : (typeof x === 'object' ? JSON.stringify(x) : x))}</span></div>`).join(''), raw: o}));
        bubble(ME(), 'briefing ready', 'creator', 6000); feed(`<b>Your AI manager</b>: ${esc(String(txt).slice(0, 140))}`, 'good', null, 'ai'); }
      if (ev.action === 'prove') { if (r) follow(addSpan(r, {kind: 'proof', title: o.verified ? 'Solvency proved' : 'Not provable', start: ev.t, end: ev.t, cls: o.verified ? 'code' : 'bad', icon: '∎', kindLabel: 'zero-knowledge proof',
          html: `<div><span class="chip ${o.verified ? 'ok' : 'no'}">${o.verified ? 'verified' : 'failed'}</span> ${esc(o.statement || '')}</div><div class="what">${o.bit_proofs ? o.bit_proofs + ' range proofs; ' : ''}${esc(o.reveals || 'no balance is revealed')}</div>`, raw: o}));
        bubble('PLATFORM', o.verified ? 'proved: the fund covers every creator' : 'cannot prove solvency', o.verified ? 'creator' : 'bad', 9000); feed(`<b>Zero-knowledge proof</b>: ${o.verified ? 'the safety fund covers every creator' : 'not provable'}`, o.verified ? 'good' : 'bad', null, 'code'); }
      if (ev.action === 'buy') { const st = o.settlement || {}; if (st.status === 'held') bubble(ME(), `PayPal holds ${money((o.choice || {}).price)} until delivery`, 'money', 9000); }
      if (ev.action === 'club') { const x = o.execution || {}; bubble(ME(), `club bought ${money(x.invested || 0)}; my share ${money(o.from_your_earnings || 0)}`, 'money', 9000);
        feed(`<b>Investment club</b>: ${money(x.invested || 0)} invested together; ${money(o.from_your_earnings || 0)} came from your earnings, the rest from the community <span class="src sim">sim</span>`, 'good', null, 'code'); }
      if (ev.action === 'customers') { const pd = (o.paid_on_paypal || []).filter(x => x.status === 'completed');
        feed(`<b>AI customers</b>: ${o.sales || 0} sales, ${o.returns || 0} returns this round${pd.length ? `; ${pd.length} paid on PayPal (${money(pd.reduce((a, x) => a + x.amount, 0))})` : ''}`, '', null, 'ai'); }
      break; }
    case 'books': renderBooks(ev.account); break;
    case 'network': setGraph(ev.graph); break;
    case 'error': feed(`<b>error</b> ${esc(ev.error)}`, 'bad'); if (!replaying) toast(ev.error); break;
    case 'run_end': {
      if (r) { r.end = ev.t; layoutRun(r); r.el.querySelector('.ms').textContent = (ev.ms / 1000).toFixed(1) + ' s'; }
      if (!replaying) active = Math.max(0, active - 1); glow(ME(), false); glow('PLATFORM', false);
      [ME(), 'PLATFORM'].forEach(id => { const b = bubbles[id]; if (b && /…$/.test(b.textContent)) b.dataset.until = Date.now(); });
const k = {buy: 'buyer', payday: 'operator', club: 'club', customers: 'market', scan: 'fraud'}[ev.action]; if (k) liveG[k] = false; gtabs();
      if (!replaying && r && k) $('#gCap').innerHTML = `<b>Done</b> in ${(ev.ms / 1000).toFixed(1)} s. The path the agents took stays lit; click any node to inspect it.`;
      $('#traceStat').textContent = Object.keys(runs).length + ' runs' + (lseq ? ' · ' + lseq + ' money events' : '');
      if (!replaying) refreshView();
      if (selected) selected.follow = false; break; }
  }
}

// ================= money ledger (AG Grid, streaming) =================
let lgrid = null, lseq = 0; const lpending = [];
function ledgerAdd(row) { const r = {n: ++lseq, t: new Date().toTimeString().slice(0, 8), ...row}; r.what = String(r.what || '').replace(/^PayPal /, ''); if (!lgrid) { lpending.push(r); return; }
  const res = lgrid.applyTransaction({add: [r], addIndex: 0}); if (!replaying && res && res.add && res.add.length) lgrid.flashCells({rowNodes: res.add});
  $('#traceStat').textContent = lseq + ' money events'; }
function cssv(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function gridTheme() { const dk = document.documentElement.dataset.theme === 'dark';
  return agGrid.themeQuartz.withParams({backgroundColor: cssv('--panel'), foregroundColor: cssv('--ink'), headerBackgroundColor: cssv('--hdr'), headerTextColor: cssv('--muted'), headerFontWeight: 500,
    borderColor: cssv('--line'), rowHoverColor: dk ? 'rgba(139,149,255,.08)' : 'rgba(79,70,229,.05)', oddRowBackgroundColor: cssv('--odd'), accentColor: cssv('--accent'), chromeBackgroundColor: cssv('--hdr'),
    browserColorScheme: dk ? 'dark' : 'light', fontFamily: 'inherit', fontSize: '12.5px', headerFontSize: '12px', spacing: 6, wrapperBorder: false, wrapperBorderRadius: 0}); }
function themeLabel() { const dk = document.documentElement.dataset.theme === 'dark'; $('#themeIco').innerHTML = dk ? '&#9728;' : '&#9790;'; $('#themeTxt').textContent = dk ? 'Light' : 'Dark'; }
$('#themeBtn').addEventListener('click', () => { const r = document.documentElement; const dk = r.dataset.theme !== 'dark';
  if (dk) r.dataset.theme = 'dark'; else delete r.dataset.theme; try { localStorage.setItem('helm-theme', dk ? 'dark' : 'light'); } catch (e) {}
  themeLabel(); [lgrid, mineGrid, salesGrid, acctGrid].forEach(g => { if (g) g.setGridOption('theme', gridTheme()); }); });
themeLabel();
function initLedger() { if (!window.agGrid) return;
  const theme = gridTheme();
  const railCell = p => { const v = p.value || ''; const c = /PayPal/.test(v) ? 'pp' : /sim/.test(v) ? 'sim' : 'code'; return `<span class="src ${c}" style="margin:0">${esc(v)}</span>`; };
  lgrid = agGrid.createGrid($('#ledger'), {theme, rowData: [], getRowId: p => String(p.data.n), animateRows: true, suppressCellFocus: true,
    defaultColDef: {sortable: true, filter: true, resizable: true},
    rowClassRules: {'bad': p => !!(p.data && p.data.bad)},
    columnDefs: [{field: 't', headerName: 'Time', width: 76}, {field: 'what', headerName: 'What', minWidth: 150, flex: 1.4, tooltipField: 'what'},
      {field: 'amount', headerName: 'Amount', width: 92, type: 'rightAligned', filter: 'agNumberColumnFilter', valueFormatter: p => p.value == null ? '' : money(p.value), cellStyle: p => ({fontWeight: 600, color: p.data && p.data.bad ? 'var(--bad)' : 'var(--ink)'})},
      {field: 'rail', headerName: 'Rail', width: 138, cellRenderer: railCell}, {field: 'from', headerName: 'From', width: 110, tooltipField: 'from'}, {field: 'to', headerName: 'To', width: 130, tooltipField: 'to'},
      {field: 'status', headerName: 'Status', width: 110}, {field: 'id', headerName: 'PayPal or order id', width: 170}]});
  if (lpending.length) lgrid.applyTransaction({add: lpending.splice(0).reverse(), addIndex: 0}); }
$('#ptabs').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; document.querySelectorAll('#ptabs button').forEach(x => x.classList.toggle('on', x === b));
  const L = b.dataset.p === 'ledger'; $('#ledger').classList.toggle('on', L); $('#trace').classList.toggle('off', L); });
$('#realBtn').addEventListener('click', e => { e.stopPropagation(); $('#realP').classList.toggle('on'); });
document.addEventListener('click', e => { if (!e.target.closest('.real')) $('#realP').classList.remove('on'); });
initLedger();

// ================= the views beside the map: shop, my shop, accounts =================
let view = 'map';
function setView(v) { view = v; $('#center').classList.toggle('wide', v !== 'map'); document.querySelectorAll('#vtabs button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  ['map', 'shop', 'mine', 'accts'].forEach(k => $('#v' + {map: 'Map', shop: 'Shop', mine: 'Mine', accts: 'Accts'}[k]).classList.toggle('on', k === v));
  if (v === 'map') setTimeout(() => { size(); mNodes.forEach(n => { if (n.hub) { const [x, y] = hubPos(n.id); n.fx = x; n.fy = y; } }); sim && sim.alpha(.4).restart(); }, 30);
  refreshView(); }
$('#vtabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) setView(b.dataset.v); });
function refreshView() { if (view === 'shop') loadShop(); if (view === 'mine') loadMine(); if (view === 'accts') loadAccts(); }
async function getj(u) { const r = await fetch(u, {headers: H}); const j = await r.json(); if (j.error || !r.ok) throw new Error(j.error || 'the server could not answer (' + r.status + ')'); return j; }

// --- shop (the buyer's catalog) ---
$('#qCat').innerHTML += ['presets', 'beats', 'prints', 'ebooks', 'merch', 'templates'].map(c => `<option>${c}</option>`).join('');
const shopItems = {};
async function loadShop() {
  const q = $('#q').value.trim(), qs = new URLSearchParams({q, category: $('#qCat').value}); if ($('#qStores').checked && q) qs.set('stores', 'true');
  if ($('#qMax').value) qs.set('max_price', $('#qMax').value);
  let j; try { j = await getj('/api/live/catalog?' + qs); } catch (e) { $('#shopGrid').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  $('#shopNote').innerHTML = `You have <b>${money(j.spendable)}</b> of earnings to spend. <b>Buy now</b> holds the money on PayPal until you confirm delivery; <b>Ask my agent</b> sends your buyer agent with your signed budget.`;
  const card = c => { shopItems['l:' + c.id] = c; return `<div class="pc ${c.suspended ? 'off' : ''}">
      <div class="pt">${esc(c.title)}</div>
      <div class="pm"><span class="chip">${esc(c.category)}</span> ${c.new ? '<span class="tag new">new</span>' : ''} ${c.mine ? '<span class="tag mine">yours</span>' : ''} ${c.suspended ? '<span class="tag sus">seller frozen</span>' : ''}</div>
      <div class="pm">by <b>${esc(c.seller_name)}</b> &middot; ${c.sold} sold &middot; ${Math.round(c.return_rate * 100)}% returns${c.trust != null && !c.mine ? ` &middot; <b title="Seller trust: the low end of the 95% range on this seller's orders that were not returned or disputed. Fewer sales, less certainty, lower score.">trust ${c.trust}</b>` : ''}${c.paypal_payee ? ' &middot; <span class="tag pp">paid via PayPal</span>' : ''}</div>
      <div class="pr">${money(c.price)}</div>
      <div class="pa">${c.mine || c.suspended ? '' : `<button class="go sm" data-buy="${esc(c.id)}">Buy now</button><button class="ghost sm" data-agent="l:${esc(c.id)}">Ask my agent</button>`}</div></div>`; };
  let h = `<h4>From creators on Helm (${j.creators.length})</h4><div class="pgrid">${j.creators.map(card).join('') || '<div class="empty">Nothing matches. Try another word or category.</div>'}</div>`;
  if (j.stores) { h += `<h4>From real stores via Channel3 (${(j.stores.products || []).length})${j.stores.backend !== 'channel3' ? ' &middot; demo catalog' : ''}</h4><div class="pgrid">` + (j.stores.products || []).map(p => { shopItems['s:' + p.id] = p; return `<div class="pc">
      ${p.image ? `<img src="${esc(p.image)}" alt="" loading="lazy">` : ''}<div class="pt">${esc(p.title)}</div><div class="pm">${esc(p.brand || '')} &middot; ${esc(p.merchant || '')}</div><div class="pr">${money(p.price)}</div>
      <div class="pa"><button class="go sm" data-store="${esc(p.id)}">Buy now</button><button class="ghost sm" data-agent="s:${esc(p.id)}">Ask my agent</button></div></div>`; }).join('') + '</div>'; }
  else if (!$('#qStores').checked) h += `<div class="what">Tick <b>real stores</b> and search to add products from Channel3.</div>`;
  $('#shopGrid').innerHTML = h;
}
$('#qGo').addEventListener('click', loadShop); $('#q').addEventListener('keydown', e => { if (e.key === 'Enter') loadShop(); });
$('#qCat').addEventListener('change', loadShop);
$('#shopGrid').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.buy) { b.disabled = true; act('buy_listing', {listing: b.dataset.buy}); }
  if (b.dataset.store) { b.disabled = true; act('buy_store', {product: b.dataset.store}); }
  if (b.dataset.agent) { const it = shopItems[b.dataset.agent]; if (!it) return; setRole('buyer');
    $('#need').value = `I need ${it.title}`; $('#budget').value = Math.ceil((+it.price || 0) * 1.15); act('buy', {need: $('#need').value, budget: +$('#budget').value, for_price: +it.price || 0, attack: $('#attack').checked}); } });

// --- my shop (the creator's listings and sales) ---
let mineGrid = null, salesGrid = null;
async function loadMine() {
  let j; try { j = await getj('/api/live/myshop'); } catch (e) { return; }
  const s = j.summary;
  $('#mineSum').innerHTML = [['Listings', s.listings], ['Orders', s.orders], ['Return rate', Math.round(s.return_rate * 100) + '%'], ['Owed to you', money(s.owed_to_you)], ['Settled, payable now', money(s.settled_now)], ['PayPal payee', s.payee ? 'linked' : 'platform']].map(([k, v]) => `<div><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  if (!window.agGrid) return;
  if (!mineGrid) mineGrid = agGrid.createGrid($('#mineGrid'), {theme: gridTheme(), rowData: [], getRowId: p => p.data.id, suppressCellFocus: true, singleClickEdit: true,
    defaultColDef: {sortable: true, resizable: true},
    columnDefs: [{field: 'title', headerName: 'Listing', flex: 2, minWidth: 160}, {field: 'category', headerName: 'Category', width: 100},
      {field: 'price', headerName: 'Price (click to edit)', width: 140, editable: true, cellEditor: 'agNumberCellEditor', valueFormatter: p => money(p.value), cellStyle: {fontWeight: 600, color: 'var(--accent)'}},
      {field: 'sold', headerName: 'Sold', width: 76}, {field: 'revenue', headerName: 'Revenue', width: 104, valueFormatter: p => money(p.value)}, {field: 'returns', headerName: 'Returns', width: 86},
      {headerName: '', width: 92, sortable: false, cellRenderer: p => `<button class="cellbtn bad" data-delist="${esc(p.data.id)}">Take down</button>`}],
    onCellValueChanged: e => { if (e.colDef.field === 'price' && +e.newValue > 0 && +e.newValue !== +e.oldValue) act('reprice', {listing: e.data.id, price: +e.newValue}); }});
  mineGrid.setGridOption('rowData', j.listings);
  if (!salesGrid) salesGrid = agGrid.createGrid($('#salesGrid'), {theme: gridTheme(), rowData: [], suppressCellFocus: true, defaultColDef: {sortable: true, resizable: true},
    rowClassRules: {'bad': p => p.data && p.data.status !== 'fulfilled'},
    columnDefs: [{field: 'listing', headerName: 'Item', flex: 2, minWidth: 150}, {field: 'buyer', headerName: 'Buyer', flex: 1, minWidth: 100}, {field: 'amount', headerName: 'Amount', width: 96, valueFormatter: p => money(p.value)},
      {field: 'status', headerName: 'Status', width: 110}, {field: 'order', headerName: 'Order', width: 110}]});
  salesGrid.setGridOption('rowData', j.sales);
}
$('#mineGrid').addEventListener('click', e => { const b = e.target.closest('[data-delist]'); if (b) { b.disabled = true; act('delist', {listing: b.dataset.delist}); } });
$('#mineNew').addEventListener('click', e => { e.preventDefault(); setRole('creator'); const t = $('#sTitle'); t && t.focus(); });

// --- accounts (the operator's review queue) ---
let acctGrid = null, afilter = 'all';
const acctRows = {};
async function loadAccts() {
  let j; try { j = await getj('/api/live/accounts'); } catch (e) { return; }
  j.accounts.forEach(a => acctRows[a.id] = a);
  if (!window.agGrid) return;
  if (!acctGrid) acctGrid = agGrid.createGrid($('#acctGrid'), {theme: gridTheme(), rowData: [], getRowId: p => p.data.id, suppressCellFocus: true,
    defaultColDef: {sortable: true, resizable: true, filter: true},
    isExternalFilterPresent: () => afilter !== 'all', doesExternalFilterPass: n => afilter === 'frozen' ? n.data.status === 'frozen' : n.data.risk >= .3 && n.data.status !== 'frozen',
    rowClassRules: {'bad': p => p.data && p.data.status === 'frozen'},
    onRowClicked: e => { if (e.event && e.event.target.closest('button')) return; acctInspect(e.data); },
    columnDefs: [{field: 'name', headerName: 'Account', width: 130}, {field: 'risk', headerName: 'Risk', width: 110, sort: 'desc',
        cellRenderer: p => { const v = p.value, c = v >= .6 ? '#dc2626' : v >= .3 ? '#d97706' : '#10b981'; return `<span class="riskb" style="width:${Math.max(4, v * 46)}px;background:${c}"></span>${Math.round(v * 100)}`; }},
      {field: 'status', headerName: 'Status', width: 92, cellRenderer: p => `<span class="chip ${p.value === 'frozen' ? 'no' : 'ok'}">${p.value}</span>`},
      {field: 'signals', headerName: 'Evidence', flex: 2, minWidth: 220, tooltipField: 'signals'}, {field: 'owed', headerName: 'Owed', width: 100, valueFormatter: p => money(p.value)},
      {field: 'sales', headerName: 'Sales', width: 76}, {field: 'buys', headerName: 'Buys', width: 72}, {field: 'country', headerName: 'Country', width: 86},
      {headerName: '', width: 96, sortable: false, filter: false, cellRenderer: p => p.data.me ? '' : p.data.status === 'frozen' ? `<button class="cellbtn good" data-unfreeze="${p.data.id}">Clear</button>` : `<button class="cellbtn bad" data-freeze="${p.data.id}">Freeze</button>`}]});
  acctGrid.setGridOption('rowData', j.accounts); acctGrid.setGridOption('quickFilterText', $('#aq').value);
  const rv = j.accounts.filter(a => a.risk >= .3 && a.status !== 'frozen').length, fz = j.accounts.filter(a => a.status === 'frozen').length;
  $('#acctNote').innerHTML = `<b>${j.accounts.length}</b> accounts &middot; <b>${rv}</b> need review &middot; <b>${fz}</b> frozen. Ranked by risk from each account's own record. Click a row for the evidence; freeze one and its earnings stop moving.`;
}
$('#aq').addEventListener('input', () => acctGrid && acctGrid.setGridOption('quickFilterText', $('#aq').value));
$('#aseg').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; afilter = b.dataset.f; document.querySelectorAll('#aseg button').forEach(x => x.classList.toggle('on', x === b)); acctGrid && acctGrid.onFilterChanged(); });
$('#acctGrid').addEventListener('click', e => { const f = e.target.closest('[data-freeze]'), u = e.target.closest('[data-unfreeze]');
  if (f) { f.disabled = true; act('freeze', {account: f.dataset.freeze}); } if (u) { u.disabled = true; act('unfreeze', {account: u.dataset.unfreeze}); } });
function acctInspect(a) {
  if (nodeById[a.id]) highlightAccount(a.id);
  selected = {acctRow: a.id}; $('#inspWhat').textContent = 'review';
  $('#insp').innerHTML = `<div class="ih"><b>${esc(a.name)}</b><span class="chip ${a.status === 'frozen' ? 'no' : 'ok'}">${a.status}</span><span class="chip ${a.risk >= .6 ? 'no' : a.risk >= .3 ? 'hold' : 'ok'}">risk ${Math.round(a.risk * 100)}</span></div>
    <div class="sec"><div class="k">Evidence</div><div>${esc(a.signals)}</div></div>
    <div class="sec"><div class="k">Record</div><div class="vrow"><span class="nm">Sales</span><span>${a.sales}, ${Math.round(a.seller_return_rate * 100)}% came back</span></div>
    <div class="vrow"><span class="nm">Purchases</span><span>${a.buys}, ${Math.round(a.buyer_return_rate * 100)}% returned</span></div><div class="vrow"><span class="nm">Owed to them</span><span>${money(a.owed)}</span></div>
    <div class="vrow"><span class="nm">Country</span><span>${esc(a.country)}</span></div><div class="vrow"><span class="nm">PayPal payee</span><span>${a.paypal_payee ? 'sandbox seller account' : 'paid through the platform'}</span></div>${a.reason ? `<div class="vrow"><span class="nm">Frozen because</span><span>${esc(a.reason)}</span></div>` : ''}</div>
    <div class="sec">${a.me ? '' : a.status === 'frozen' ? `<button class="go c" data-unfreeze-i="${a.id}">Clear after review</button>` : `<button class="go" style="background:var(--bad)" data-freeze-i="${a.id}">Freeze for review</button>`}</div>`;
}
$('#insp').addEventListener('click', e => { const f = e.target.closest('[data-freeze-i]'), u = e.target.closest('[data-unfreeze-i]');
  if (f) { f.disabled = true; act('freeze', {account: f.dataset.freezeI}); } if (u) { u.disabled = true; act('unfreeze', {account: u.dataset.unfreezeI}); } });

// ================= live connection =================
function connect() {
  const es = new EventSource('/api/live/stream?sid=' + encodeURIComponent(SID));
  es.onopen = () => { $('#conn').classList.add('on'); $('#connTxt').textContent = 'LIVE'; };
  es.onmessage = m => { try { onEvent(JSON.parse(m.data)); } catch (e) { console.error(e); } };
  es.onerror = () => { $('#conn').classList.remove('on'); $('#connTxt').textContent = 'RECONNECTING'; };
}
size(); connect();

document.querySelectorAll('.max').forEach(b => b.addEventListener('click', () => { const c = $('#center'), p = document.getElementById(b.dataset.z);
  const on = !p.classList.contains('z'); document.querySelectorAll('.center>.pnl').forEach(x => x.classList.remove('z')); c.classList.toggle('zoom', on); if (on) p.classList.add('z');
  setTimeout(() => { size(); mNodes.forEach(n => { if (n.hub) { const [x, y] = hubPos(n.id); n.fx = x; n.fy = y; } }); sim && sim.alpha(.4).restart(); }, 60); }));
const qs = new URLSearchParams(location.search); if (qs.get('market') === '1') setTimeout(() => setMkt(true), 1500);
})();
</script></body></html>
"""
