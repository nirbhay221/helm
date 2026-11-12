"""The money-out operator as a multi-agent graph, not a single ReAct loop.

The old operator was one model talking to itself in a tool-calling loop. This is
the inversion done properly: several role agents that actually collaborate, wired
as a LangGraph state graph, and then deterministic code disposes the money. The
shape follows the published multi-agent-trading-firm pattern (analysts -> a
bull/bear research debate -> a manager that decides), adapted to Helm's job of
paying creators safely:

    signal_analyst   reads the cycle's signal into a risk posture
    risk_analyst     judges each creator pay-vs-hold from their messy context
    bull / bear      debate how aggressive the release should be (N rounds)
    manager          synthesises the debate + analyst views into a proposal
    compliance_gate  screens every proposed payment (sanctions/structuring/...)
    dispose          the solver sizes the safe release and PayPal pays, clamped

The agents only PROPOSE. The dispose node calls the same deterministic tools the
single-agent operator used, so every hard limit (safe-release cap, owed cap, AUP
purpose, human-approval threshold) still binds exactly as before. When no model
key is present each node has a transparent deterministic fallback, so the graph
runs end to end offline; with a key the agents genuinely reason.
"""
from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from market.compliance import ComplianceEngine

from .llm import LLMClient
from .operator_tools import OperatorTools

try:                                            # the agents reason from a sourced knowledge base
    from market.knowledge import retrieve as _kb_retrieve
except Exception:                               # pragma: no cover
    _kb_retrieve = None


def _ground(state: OpState, query: str) -> str:
    """Retrieve the financial principles relevant to this decision, inject them into the agent's
    prompt (so the reasoning is financially literate, not generic), and record which were applied
    so the cycle can cite its sources. Addresses the FinQA domain-knowledge error class."""
    if _kb_retrieve is None:
        return ""
    try:
        items = _kb_retrieve(query, k=3)
    except Exception:
        return ""
    applied = state.setdefault("grounding", [])
    for p in items:
        tag = {"topic": p.topic, "source": p.source}
        if tag not in applied:
            applied.append(tag)
    block = "\n".join(f"- {p.topic}: {p.statement} ({p.source})" for p in items)
    return ("\nGround your judgment in these financial principles, and do not contradict them:\n"
            + block + "\n") if block else ""

def _clip(text: Any, limit: int) -> str:
    """Shorten model prose for display without cutting a word in half: prefer the last full
    sentence that fits, else the last whole word, and mark any cut with an ellipsis."""
    s = " ".join(str(text or "").replace("\u2014", ", ").replace(" ,", ",").split())
    if len(s) <= limit:
        return s
    head = s[:limit]
    stop = max(head.rfind(". "), head.rfind("; "), head.rfind("! "), head.rfind("? "))
    if stop >= limit * 0.5:
        return head[:stop + 1]
    space = head.rfind(" ")
    return (head[:space] if space > 0 else head).rstrip(",;:") + "..."


_RISKY_WORDS = ("fraud", "new", "viral", "dispute", "chargeback", "suspicious", "spike", "flag")


class OpState(TypedDict, total=False):
    observation: dict
    signal_read: dict
    risk_views: list            # [{creator, verdict: "pay"|"hold", reason}]
    debate: list                # [{role, round, argument, pushes}]
    debate_round: int
    max_debate_rounds: int
    risk_multiplier: float
    proposal: list              # [{creator, amount}]
    defaulted: list             # cleared creators the manager left out, paid their settled balance
    compliance: list           # [{creator, decision, reasons}]
    grounding: list             # [{topic, source}] financial principles the agents applied
    decision: dict              # final dispose result
    driver: str                 # "model" | "fallback" (worst node wins)
    nodes: dict                 # node -> {"driver", "model"?, "error"?}: who actually ran each step


def _mark(state: OpState, driver: str, node: str | None = None, model: str | None = None,
          error: str | None = None) -> None:
    """Record the weakest driver used so far (one fallback node taints the cycle), and per node
    which model actually answered or why it fell back."""
    if driver == "fallback" or state.get("driver") == "fallback":
        state["driver"] = "fallback"
    else:
        state["driver"] = "model"
    if node:
        rec = {"driver": driver}
        if driver == "model" and model:
            rec["model"] = model
        if driver != "model" and error:
            rec["error"] = error
        state.setdefault("nodes", {})[node] = rec


class OperatorGraph:
    """Compile the multi-agent operator once; run one cycle per `step`."""

    def __init__(self, tools: OperatorTools, llm: LLMClient | None = None,
                 max_debate_rounds: int = 1, compliance: ComplianceEngine | None = None) -> None:
        self.tools = tools
        self.llm = llm or LLMClient()
        self.max_debate_rounds = max(1, int(max_debate_rounds))
        self.compliance = compliance or ComplianceEngine()
        self.app = self._build()

    # --- graph wiring -------------------------------------------------------
    def _build(self):
        from agent.tap import traced
        g = StateGraph(OpState)
        for n in ("signal_analyst", "risk_analyst", "bull", "bear", "manager", "compliance_gate", "dispose"):
            g.add_node(n, traced("operator", n, getattr(self, n), _live_summary))

        g.set_entry_point("signal_analyst")
        g.add_edge("signal_analyst", "risk_analyst")
        g.add_edge("risk_analyst", "bull")
        g.add_edge("bull", "bear")
        # bear either sends the debate back to bull for another round, or to the manager
        g.add_conditional_edges("bear", self._debate_router,
                                {"continue": "bull", "decide": "manager"})
        g.add_edge("manager", "compliance_gate")
        g.add_edge("compliance_gate", "dispose")
        g.add_edge("dispose", END)
        return g.compile()

    DISAGREE = 0.2      # bull and bear this far apart on the multiplier get another round

    def _debate_router(self, state: OpState) -> str:
        """Another round only while the bull and the bear still disagree, up to the cap."""
        rnd = state.get("debate_round", 1)
        if rnd >= self.max_debate_rounds:
            return "decide"
        last = {d["role"]: d["pushes"] for d in state.get("debate", []) if d.get("round") == rnd}
        gap = abs(last.get("bear", 1.0) - last.get("bull", 1.0))
        return "continue" if gap > self.DISAGREE else "decide"

    # --- an LLM helper that returns structured JSON or signals fallback -----
    def _ask(self, system: str, user: str, schema: dict, temperature: float = 0.2):
        """Call the model for one function-shaped answer. Returns (data, "model")
        or (None, "fallback") if there is no key or the call fails."""
        self._last_error = None
        if not self.llm.available:
            self._last_error = "no model key"
            return None, "fallback"
        try:
            msg = self.llm.chat(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                tools=[{"type": "function", "function": schema}],
                tool_choice={"type": "function", "function": {"name": schema["name"]}},
                temperature=temperature,
            )
            calls = (msg or {}).get("tool_calls") or []
            if not calls:
                self._last_error = "model answered without calling the tool"
                return None, "fallback"
            args = calls[0].get("function", {}).get("arguments", "{}")
            return (args if isinstance(args, dict) else json.loads(args)), "model"
        except Exception as exc:
            self._last_error = "%s: %s" % (type(exc).__name__, str(exc)[:160])
            return None, "fallback"

    def _rec(self, state: OpState, drv: str, node: str) -> None:
        _mark(state, drv, node, model=getattr(self.llm, "last_model", None) or self.llm.model,
              error=getattr(self, "_last_error", None))

    # --- nodes --------------------------------------------------------------
    def signal_analyst(self, state: OpState) -> OpState:
        """Read the cycle's signal into a risk posture (reuses the signal desk)."""
        obs = self.tools.observe()
        read = self.tools.interpret_signal()
        state["observation"] = obs
        state["signal_read"] = read
        # honest driver: the signal desk says whether the model or its keyword fallback read it
        drv = "fallback" if (read.get("source") == "fallback" or not self.llm.available) else "model"
        _mark(state, drv, "signal_analyst", model=getattr(self.llm, "model", None),
              error=None if drv == "model" else "signal desk used its keyword fallback")
        return state

    def risk_analyst(self, state: OpState) -> OpState:
        """Judge each creator pay-vs-hold from their context and ledger standing."""
        creators = state["observation"]["creators"]
        caution = bool(state.get("signal_read", {}).get("suggests_caution"))
        schema = {
            "name": "classify_creators",
            "description": "Classify each creator as pay or hold with a one-line reason.",
            "parameters": {"type": "object", "properties": {"verdicts": {"type": "array", "items": {
                "type": "object", "properties": {
                    "creator": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["pay", "hold"]},
                    "reason": {"type": "string"}},
                "required": ["creator", "verdict", "reason"]}}}, "required": ["verdicts"]},
        }
        system = ("You are the risk analyst on a payout desk. Decide, per creator, whether to PAY "
                  "them this cycle or HOLD. Pay low-risk creators (long-tenured, steady, clean, past "
                  "their chargeback window). Hold risky ones (brand new, just went viral, flagged for "
                  "fraud/disputes, or owing recoupment). Be specific; use the context given. The "
                  "week's signal is the newest information: where it names a creator or contradicts a "
                  "creator's profile, the signal wins, and your reason must say so."
                  + _ground(state, "creator default risk expected loss chargeback early release hold"))
        user = ("This week's signal: " + (state["observation"].get("signal") or "(none)") +
                "\nSignal posture: " + ("CAUTION" if caution else "normal") + "\nCreators:\n" +
                json.dumps(creators, indent=0))
        data, drv = self._ask(system, user, schema)
        if data and isinstance(data.get("verdicts"), list):
            got = {v.get("creator"): v for v in data["verdicts"] if isinstance(v, dict)}
            views = []
            for c in creators:
                v = got.get(c["creator"])
                if v and v.get("verdict") in ("pay", "hold"):
                    views.append({"creator": c["creator"], "verdict": v["verdict"],
                                  "reason": _clip(v.get("reason", ""), 160)})
                else:
                    views.append(self._risk_fallback_one(c, caution))
            state["risk_views"] = views
            missed = [v["creator"] for v in views if v.get("_fallback")]
            if missed:        # the model skipped someone: that creator was judged by rules, say so
                self._last_error = "model gave no verdict for " + ", ".join(missed)
                drv = "fallback"
            self._rec(state, drv, "risk_analyst")
        else:
            state["risk_views"] = [self._risk_fallback_one(c, caution) for c in creators]
            self._rec(state, "fallback", "risk_analyst")
        return state

    def _risk_fallback_one(self, c: dict, caution: bool) -> dict:
        ctx = (c.get("context") or "").lower()
        risky = any(w in ctx for w in _RISKY_WORDS) or (c.get("recoup_due", 0) or 0) > 1e-6
        if caution and (c.get("settled_owed", 0) or 0) <= 0:
            risky = True
        return {"creator": c["creator"], "verdict": "hold" if risky else "pay",
                "reason": ("risky context/recoupment" if risky else "clean and settled"),
                "_fallback": True}

    def bull(self, state: OpState) -> OpState:
        state.setdefault("debate", [])
        rnd = state.get("debate_round", 0) + 1
        state["debate_round"] = rnd
        self._debate_turn(state, "bull", rnd,
                          system=("You argue the AGGRESSIVE case on a payout desk: paying creators "
                                  "fast builds trust and most are honest. Argue for a LOWER risk "
                                  "multiplier (nearer 1.0) and for releasing to borderline creators, "
                                  "but concede any genuinely dangerous one. At most three sentences."
                                  + _ground(state, "liquidity creator trust fast payout working capital")),
                          default="Pay the clean, settled creators in full now; holding good "
                                  "creators needlessly costs trust. Keep the multiplier near 1.0.",
                          pushes_default=1.0)
        return state

    def bear(self, state: OpState) -> OpState:
        self._debate_turn(state, "bear", state.get("debate_round", 1),
                          system=("You argue the CONSERVATIVE case on a payout desk: an early "
                                  "release to a creator who later charges back is an unrecoverable "
                                  "loss. Argue for a HIGHER risk multiplier when the signal warns of "
                                  "risk, and for holding anything unsettled or flagged. At most three "
                                  "sentences."
                                  + _ground(state, "expected loss chargeback reserve provision CECL large exposure")),
                          default="Hold every creator past only their settled balance and raise the "
                                  "multiplier if the signal warns of fraud; an early release is "
                                  "unrecoverable.",
                          pushes_default=1.3)
        return state

    def _debate_turn(self, state: OpState, role: str, rnd: int, system: str,
                     default: str, pushes_default: float) -> None:
        schema = {"name": "argue", "description": "Make your case and the risk multiplier you push for.",
                  "parameters": {"type": "object", "properties": {
                      "argument": {"type": "string"},
                      "pushes_multiplier": {"type": "number", "description": "the risk multiplier you advocate, >= 1.0"}},
                      "required": ["argument", "pushes_multiplier"]}}
        prior = "\n".join(f"{d['role']}: {d['argument']}" for d in state.get("debate", []))
        user = (f"Signal: {state['observation'].get('signal')}\n"
                f"Risk views: {json.dumps(state.get('risk_views', []))}\n"
                f"Debate so far:\n{prior or '(none)'}\n\nMake your argument.")
        data, drv = self._ask(system, user, schema, temperature=0.5)
        if data:
            arg = _clip(data.get("argument", default), 420)
            pushes = max(1.0, float(data.get("pushes_multiplier", pushes_default)))
        else:
            arg, pushes, drv = default, pushes_default, "fallback"
        state["debate"].append({"role": role, "round": rnd, "argument": arg, "pushes": pushes})
        self._rec(state, drv, "%s_%d" % (role, rnd))

    def manager(self, state: OpState) -> OpState:
        """Synthesise the analyst views + debate into a risk multiplier and an allocation.

        The manager proposes amounts; it never sizes the safe release (the solver does)
        and never pays (PayPal does). Default each paid creator to their settled balance;
        a creator the risk analyst held gets nothing."""
        creators = {c["creator"]: c for c in state["observation"]["creators"]}
        holds = {v["creator"] for v in state.get("risk_views", []) if v["verdict"] == "hold"}
        pushes = [d["pushes"] for d in state.get("debate", [])] or [1.0]
        schema = {"name": "decide_payout", "parameters": {"type": "object", "properties": {
            "risk_multiplier": {"type": "number"},
            "allocations": {"type": "array", "items": {"type": "object", "properties": {
                "creator": {"type": "string"}, "amount": {"type": "number"}},
                "required": ["creator", "amount"]}}},
            "required": ["risk_multiplier", "allocations"]}}
        system = ("You are the payout manager. Weigh the bull and bear arguments and the risk views, "
                  "then choose a risk_multiplier (>= 1.0; higher = hold more reserve) and the amount to "
                  "pay each creator you are NOT holding. Never pay a held creator. Prefer each creator's "
                  "settled_owed; only exceed it for a clearly low-risk creator. The solver will cap the "
                  "total, so propose honestly."
                  + _ground(state, "RAROC risk-adjusted return reserve provision large exposure allocation"))
        user = (f"Risk views: {json.dumps(state.get('risk_views', []))}\n"
                f"Debate: {json.dumps(state.get('debate', []))}\n"
                f"Creators: {json.dumps(list(creators.values()))}")
        data, drv = self._ask(system, user, schema, temperature=0.1)
        if data and isinstance(data.get("allocations"), list):
            mult = max(1.0, float(data.get("risk_multiplier", max(pushes))))
            alloc = []
            for a in data["allocations"]:
                if not isinstance(a, dict):
                    continue
                name = a.get("creator")
                if name in creators and name not in holds:
                    try:
                        amt = float(a.get("amount", 0))
                    except (TypeError, ValueError):
                        continue
                    if amt > 1e-6:
                        alloc.append({"creator": name, "amount": round(amt, 2)})
            # Holding a creator's settled earnings is a decision with a stated reason, and only
            # the risk analyst's hold verdict carries one. A cleared creator the manager left out
            # (a quiet week once returned an empty allocation and paid no one) is paid their
            # settled balance by default; the solver still caps the batch.
            given = {a["creator"] for a in alloc}
            defaulted = []
            for c in state["observation"]["creators"]:
                name, due = c["creator"], round(c.get("settled_owed", 0.0) or 0.0, 2)
                if name not in holds and name not in given and due > 1e-6:
                    alloc.append({"creator": name, "amount": due})
                    defaulted.append(name)
            if defaulted:
                state["defaulted"] = defaulted
            state["risk_multiplier"] = mult
            state["proposal"] = alloc
            self._rec(state, drv, "manager")
        else:
            # fallback: pay each non-held creator their settled balance, multiplier = bear's push
            state["risk_multiplier"] = max(pushes)
            state["proposal"] = [{"creator": c["creator"], "amount": round(c.get("settled_owed", 0.0), 2)}
                                 for c in state["observation"]["creators"]
                                 if c["creator"] not in holds and (c.get("settled_owed", 0) or 0) > 1e-6]
            self._rec(state, "fallback", "manager")
        return state

    def compliance_gate(self, state: OpState) -> OpState:
        """Screen every proposed payment; drop anything blocked or held."""
        screened, kept = [], []
        for a in state.get("proposal", []):
            res = self.compliance.screen(a["creator"], a["amount"])
            screened.append({"creator": a["creator"], "decision": res["decision"], "reasons": res["reasons"]})
            if res["decision"] == "allow":
                kept.append(a)
        state["compliance"] = screened
        state["proposal"] = kept
        return state

    def dispose(self, state: OpState) -> OpState:
        """Deterministic: size the safe release, then pay. Every hard limit binds here."""
        sized = self.tools.size_safe_release(state.get("risk_multiplier", 1.0))
        result = self.tools.pay_creators(state.get("proposal", []), approved=False)
        result["safe_release_total"] = sized["safe_release_total"]       # the cap the multiplier set
        result["proposed_total"] = round(sum(a["amount"] for a in state.get("proposal", [])), 2)
        state["decision"] = result
        return state

    # --- public API ---------------------------------------------------------
    def step(self, signal_text: str = "") -> OpState:
        self.tools.current_signal = signal_text or ""
        init: OpState = {"debate_round": 0, "max_debate_rounds": self.max_debate_rounds}
        return self.app.invoke(init)


def _live_summary(node: str, st: dict) -> dict:
    """What the live view shows when an operator agent finishes: its own decision, in brief."""
    if node == "signal_analyst":
        r = st.get("signal_read") or {}
        obs = st.get("observation") or {}
        return {"caution": bool(r.get("suggests_caution")),
                "read": str(r.get("rationale") or r.get("summary") or r.get("reading") or "")[:240],
                "creators_in_view": len(obs.get("creators") or [])}
    if node == "risk_analyst":
        return {"verdicts": [{"creator": v.get("creator"), "verdict": v.get("verdict"),
                              "reason": str(v.get("reason", ""))[:200]} for v in st.get("risk_views", [])]}
    if node in ("bull", "bear"):
        mine = [d for d in st.get("debate", []) if d.get("role") == node]
        d = mine[-1] if mine else {}
        return {"round": d.get("round"), "pushes": d.get("pushes"), "argument": str(d.get("argument", ""))[:600]}
    if node == "manager":
        prop = st.get("proposal", [])
        return {"risk_multiplier": st.get("risk_multiplier"), "proposal": prop[:12],
                "proposed_total": round(sum(a.get("amount", 0) for a in prop), 2),
                "defaulted": st.get("defaulted", [])}
    if node == "compliance_gate":
        return {"screened": st.get("compliance", [])}
    if node == "dispose":
        d = st.get("decision") or {}
        return {k: d.get(k) for k in ("status", "message", "paid_total", "paid", "safe_release_total", "proposed_total",
                                      "cash_after", "reserve_ok_after", "guardrail_overrides")}
    return {}
