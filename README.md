# Helm

**An autonomous treasury that steers a business to its forecast, settled on PayPal.**

Helm is a money brain for a business that runs on agents. It takes money in from customers, continuously compares what the plan forecast against what is actually happening, and then acts on its own to close the gap: it decides what to buy and from whom, and it decides who to pay and how much, and it executes every one of those money moves through PayPal. The plan is the target. Helm is the autopilot that holds the business on that target.

This repository is the full specification and build plan for Helm. It is written so that a developer can pick it up cold and build it end to end. Read the Overview and Architecture first, then the Build Plan.

---

## 1. The one paragraph version

Most "AI finance" tools look at your numbers and draw you a chart. Helm does the opposite: it is a closed loop that senses the gap between forecast and actual and then moves money by itself to shrink that gap. Think of the way a ship autopilot holds a heading: it reads the current position, compares it to the planned course, and nudges the rudder every few seconds. Helm reads the business position (cash, inventory, demand, open obligations), compares it to the planned course (the forecast or budget), and nudges the two levers a business actually has: buying (pay suppliers to restock or pre-buy) and paying out (release partner commissions and rewards). Every nudge is a real PayPal transaction. The brain decides; the arms execute; PayPal moves the money.

---

## 2. The problem

Every operating business runs on a plan: a forecast of demand, revenue, spend, and inventory. Reality never matches the plan. Demand spikes, a supplier is late, a cohort of customers pays slowly, a promotion overperforms. The gap between forecast and actual is called variance, and managing it is a continuous job that today is done by people reading dashboards and then placing orders and payments by hand, usually too late.

Two things make this worse right now:

 - Businesses increasingly want to run operations with agents, not staff clicking through portals. But an agent that can place orders and payments needs a controller that knows what to do, not just a chat box.
 - The tooling that exists either forecasts (it tells you the gap) or disburses (it sends money to a list you hand it). Nothing closes the loop: senses the gap, decides the corrective money moves, and executes them.

Helm is that missing closed loop.

---

## 3. What Helm does, concretely

Helm runs a continuous control cycle. Each cycle:

 1. **Sense.** Pull the current state: cash position, inventory on hand and on order, incoming customer demand and payments, outstanding payout obligations, and the running actuals from the ledger.
 2. **Compare.** Line the actuals up against the forecast across a forward window (for example the next several weeks). Measure the variance per line (cash, each inventory item, service level, partner liabilities).
 3. **Decide.** Choose the set of money moves over the forward window that drives the projected variance back toward zero while respecting hard limits (cash floor, budget caps, legal constraints). Commit only the first move now, then re-plan next cycle with fresh data. This is receding horizon control (see Section 5).
 4. **Act.** Execute the chosen moves through PayPal:
     - Buying: place an optimal purchase to restock or pre-buy inputs (the Awardsmith arm).
     - Paying: release partner commissions, rebates, or rewards (the Payout Engine arm).
 5. **Record and learn.** Write the results back to the ledger as new actuals, update the forecast error model, and start the next cycle.

The output a human keeps is a live, auditable control journal: for every cycle, the measured variance, the decision Helm made, why it made it, and the real PayPal transaction IDs that prove the money moved.

---

## 4. Why Helm is not a dashboard (the thing that makes it worth building)

The entire value rests on one distinction. A dashboard shows you the gap. Helm acts to close it. If Helm ever degrades into "here is a chart of your variance," it has failed and it loses to the forty other finance copilots that already draw that chart.

So the product is defined by autonomy with proof: Helm must be seen to detect a variance, decide a corrective money move, and execute that move on PayPal, all by itself, with the variance then measurably shrinking. The demo is built around exactly this moment (Section 8).

---

## 5. The hard technical core

Helm is a controller, and the controller is a real optimization problem, not a prompt chain.

### 5.1 The control loop (receding horizon / model predictive control)

Helm plans over a forward horizon, applies only the first action, then re-plans from the new state next period. This is model predictive control (MPC), also called receding horizon control. It is the standard, well studied way to steer a system under forecast error, and it is used exactly this way for supply chain and inventory control, where demand is treated as an external disturbance and the controller re-solves each step as the forecast updates.

Formally, each cycle Helm solves:

 - **State** x_t: cash, inventory levels, on-order quantities, outstanding partner obligations, demand signal.
 - **Forecast / reference trajectory** r over the horizon H: the planned values for each state line.
 - **Decision variables** over the horizon: purchase quantities per input per period, and payout amounts per obligation per period, plus timing of customer payment capture.
 - **Objective:** minimize the weighted sum of squared deviations between projected state and reference over the horizon (that is, minimize variance), plus a penalty on action cost and churn.
 - **Constraints:** cash never drops below a floor (Helm holds no float; see Section 6 custody rule), inventory meets a service level, spend stays under budget caps, and every money move is legal under PayPal rules (Section 6).
 - **Apply** only period t's actions, observe reality, re-solve next cycle.

This is a quadratic or mixed integer program depending on how buying is modeled, re-solved on a rolling basis. The forecast error model (how wrong the plan tends to be, and in which direction) feeds the controller so it can act with appropriate caution.

### 5.2 The two action solvers (the arms)

The controller decides how much to buy and how much to pay. Turning those targets into the best concrete transaction is itself non trivial:

 - **Buying (Awardsmith):** given "acquire quantity Q of input X within budget B," choose the optimal purchase across available supplier quotes. This is the procurement winner determination problem: a mixed integer program with minimum order quantities, tiered volume discounts (piecewise linear), all or nothing bundle offers, supplier capacity, and multi sourcing or diversification limits. It is NP hard in general and solved with branch and bound.
 - **Paying (Payout Engine):** given "distribute pot P to the parties who earned it," compute a split that reflects true contribution and that nobody can inflate by cheating. The reason this is hard is that a naive split by tracked activity is gameable: a party can spin up duplicate identities, inflate activity, or split activity to dodge a cap, and drain the pot from the honest parties. The engine computes the attacker's most profitable manipulation and hardens the split (caps, hold backs, clawbacks, verification gates) until manipulation earns nothing. This is a leader and follower (Stackelberg) optimization that iterates to a point where no profitable deviation exists. Published results show that a plain contribution split is not manipulation proof on its own, which is exactly why the hardening layer is load bearing rather than decorative.

### 5.3 Honesty about when the core is real

The control loop and both solvers are genuine computation only when the problem is genuine:

 - The buying arm earns its keep when there are real supplier choices with minimum orders, discounts, or bundles. If there is one supplier and a flat price, buying is trivial and the solver is theater.
 - The paying arm earns its keep when activity can actually be inflated or faked (affiliate, creator, and crowd payouts, where this is rampant). If every contribution is cleanly and un fakeably tracked, a proportional split is correct and the hardening is unnecessary.
 - The controller earns its keep when variance is real and the two levers actually move it. If the business is perfectly predictable, there is nothing to control.

Build and demo Helm on a setting where all three conditions hold.

---

## 6. PayPal surfaces and the hard rules

Helm settles everything on PayPal. The design is shaped by what PayPal allows.

### 6.1 Surfaces used

 - **Orders v2** for money in (customer payments) and for buying (paying a supplier who accepts PayPal is an ordinary purchase). Supports authorize, capture, void, refund, and partial capture, which the controller uses to time cash.
 - **Payouts (REST)** for paying partners their commissions, rebates, and rewards. Pays by email, can reach recipients who do not yet have an account, auto returns unclaimed funds after a holding period, and accepts large batches.
 - **Agent Toolkit and MCP server** as the agent facing execution layer. The hosted sandbox endpoint is `mcp.sandbox.paypal.com`. The toolkit exposes tools for orders, invoices, refunds, subscriptions, shipment tracking, transaction data, products, and disputes.
 - **Webhooks** to confirm each transaction landed, with idempotent handling so a retried or duplicated event never double acts.

### 6.2 The Payouts gap we fill

PayPal's Agent Toolkit MCP server has tools for taking money in and managing orders, invoices, subscriptions, and disputes, but it has no tool for paying out. Payouts run through the separate Payouts API. Helm ships a Payouts MCP tool that wraps the Payouts REST API as an agent callable tool, with an idempotency key and a human confirmation gate, so the controller can execute disbursements through the same agent interface as everything else. This is a concrete, reusable contribution that closes a real hole in the official toolkit.

### 6.3 The constraints that shape the design (read these before building)

 - **No custody.** Helm never holds or pools money. Holding other parties' money turns the operator into a money transmitter, which is illegal without licensing and gets accounts frozen. The pot and the operating cash live in the operator's own PayPal business account. Helm only computes amounts and instructs PayPal to move money directly from the operator to each recipient. This is why the cash floor constraint in the controller matters: Helm spends only money the operator already holds.
 - **No payroll.** PayPal's payout rules do not permit paying employee wages. Helm's money out is therefore limited to supplier purchases (ordinary payments for goods) and partner commissions, rebates, rewards, and incentives (the permitted payout categories). Paying salaries is explicitly out of scope.
 - **Permitted payout purposes only.** The payout rail is restricted to commissions, rebates, rewards, and incentives. The Clearwright check (Section 7) proves every planned money edge maps to a permitted purpose on a permitted rail before anything executes.
 - **Sandbox for the build.** Everything is built and demonstrated in the PayPal sandbox: a sandbox business account funds the moves, sandbox recipients receive them, and the demo shows real sandbox transaction IDs. No real money moves.

---

## 7. System architecture

Helm is a council of specialized agents around a deterministic controller. The language agents explore, read messy inputs, and explain. The solvers decide. The split is deliberate: creativity in the exploration layer, determinism in the decision layer, so the money decisions are reproducible and auditable.

### 7.1 The brain

 - **Helm Core (the controller).** Runs the sense, compare, decide, act cycle of Section 5.1. Holds the state model, the forecast, and the receding horizon optimizer. Emits targets to the arms ("buy this much," "pay out this much") and writes the control journal.
 - **Forecast and variance model.** Maintains the reference trajectory and the forecast error model. Turns raw ledger actuals and demand signals into the variance measurement the controller optimizes against.
 - **Council and orchestration.** Coordinates the agents, routes each cycle through sense, decide, act, and reconciles disagreement between the business objective (hit the forecast) and the constraints (stay within cash, budget, and legal limits) before any action is committed.

### 7.2 The arms

 - **Awardsmith (buying arm).** Procurement winner determination solver. Input: a buy target from the controller plus available supplier quotes. Output: the optimal purchase plan, executed as PayPal Orders payments to suppliers.
 - **Payout Engine (paying arm).** Turns a payout target into correct, un gameable, legal, tax handled disbursements. It is composed of five sub parts that run in sequence on the same pot:
     - **Mete (contribution split).** Computes each party's share of a jointly created pot by true marginal contribution, so credit is not double counted or awarded only to the last touch. Needed when contributions overlap.
     - **Bulwark (manipulation hardening).** Simulates the most profitable cheat against the split and hardens the schedule (caps, hold backs, clawbacks, verification gates) until cheating earns nothing. This is the un gameable guarantee and the paying arm's money shot.
     - **Clearwright (legality pre flight).** Proves the whole payout plan is permitted: every money edge maps to an allowed purpose on an allowed rail, nothing pools in the operator, the operator is not acting as a transmitter. Returns the exact offending edge and a fix if a plan is illegal.
     - **Tollgate (tax).** For cross border recipients, computes the correct withholding and prepares the filing data. This reuses established tax logic rather than reinventing it.
     - **Keystone (atomic execution).** Executes the batch so that partial failure never corrupts the books: if some payments fail, it reconciles or rolls back so nothing is stranded or double paid and the totals still balance. Runs on top of the Payouts MCP tool.

### 7.3 The money in path

 - **Orders intake.** Customer payments captured through Orders v2 feed the actuals and the cash position. The controller can authorize and delay capture, or partially capture, to time cash against the forecast.

### 7.4 Data flow summary

Customers pay through Orders, which updates actuals. Helm Core compares actuals to forecast, measures variance, and solves for corrective actions. Buy targets go to Awardsmith, which purchases through Orders. Payout targets go to the Payout Engine, which splits, hardens, checks, taxes, and executes through the Payouts MCP tool. Webhooks confirm each move, which updates actuals, and the loop repeats. Every step is written to the control journal.

---

## 8. The demo (what has to be on screen)

The build is organized around one undeniable three minute sequence. Build the brain and exactly one arm for the demo; the other arm is shown as a described capability, not built deep.

**Core sequence (either arm):** start a simulated business running on plan. Inject a shock (a demand spike, or a supplier delay, or a slow paying cohort). The variance chart opens a visible gap. Helm detects it, decides a corrective move, and executes it on the PayPal sandbox with a real transaction ID appearing on screen. The variance chart then visibly closes. The point the audience must feel: the system did this by itself, and the money actually moved.

**If the paying arm is the demo:** add the manipulation moment. Show a naive split handing a cheater with duplicate identities a large slice. Turn on Bulwark. The cheater's take collapses toward zero while the honest parties' shares rise, and the hardened batch pays out live in sandbox. This before and after is the strongest single beat available.

**If the buying arm is the demo:** show the controller sizing a restock from the variance, Awardsmith selecting the optimal supplier mix under minimum orders and volume discounts (and visibly beating the naive lowest unit price choice on total landed cost), and the purchase settling on sandbox.

Recommendation: lead with the paying arm for the sharper money shot, or the buying arm if the forecast to purchase story is clearer for your chosen business setting. Pick one.

---

## 9. How this maps to the judging criteria

 - **Technological Implementation.** A real controller (receding horizon optimization) plus a real action solver (winner determination or Stackelberg hardening) plus a genuine PayPal integration that fills a real gap in the official toolkit (the Payouts MCP tool).
 - **Design.** One coherent product with a clear loop and a single clear screen (the control journal and the variance chart), not a bag of features.
 - **Potential Impact.** Autonomous treasury and procurement is a large and strategically active area; the loop applies to any operating business that buys inputs and pays partners.
 - **Innovation.** Nothing in the field closes the loop from forecast variance to executed money moves. Existing tools forecast or disburse, not both.
 - **Presentation.** The money shot (variance opens, Helm acts alone, money moves, variance closes) is visible and concrete in the demo window.

A dashboard built in AG Studio (the control journal and the live variance and decision view) is a natural fit for the AG Grid sponsor prize and should be the primary UI.

---

## 10. Build plan

Build in this order. Do not build all arms. Build the brain and one arm deep, make the demo land, then widen.

### Phase 0: foundation
 - Repo scaffold, environment, PayPal sandbox app with Orders and Payouts enabled. Enable Payouts on the sandbox business account on day one, because enablement can take time.
 - A synthetic business simulator that produces a forecast, a stream of actuals, and injectable shocks (demand spike, supplier delay, slow paying cohort). This is the data source for everything; make it realistic in its aggregate distribution, not flat and not single sample.

### Phase 1: the brain
 - Implement Helm Core: state model, forecast and variance measurement, and the receding horizon optimizer with the cash floor, budget, and service level constraints. Start with a quadratic objective and linear dynamics; add integrality for buying only when the buying arm is built.
 - Implement the control journal (per cycle: variance, decision, rationale, transaction references).

### Phase 2: one arm
 - If paying: implement Mete (contribution split), then Bulwark (the attacker simulation and the hardening loop), then Clearwright (the legality pre flight), then Keystone on top of the Payouts MCP tool. Add Tollgate last; it is reuse, not core.
 - If buying: implement Awardsmith (the winner determination solver) and wire its purchases through Orders.

### Phase 3: the Payouts MCP tool
 - Wrap the Payouts REST API as an MCP tool with an idempotency key and a human confirmation gate. This is both the executor and a standalone contribution.

### Phase 4: the loop and the demo
 - Close the loop: shock, sense, decide, act on sandbox, variance closes. Build the single demo screen. Rehearse the three minute sequence until the autonomy and the money movement are both unmistakable.

### Phase 5: widen (only if time)
 - Add the second arm as a shown capability. Add Tollgate if paying. Add scenario variety.

---

## 11. Recommended stack

 - Agent orchestration: a graph based multi agent framework (a stateful graph of nodes with a shared state object) for the council and the sense, decide, act cycle.
 - Solvers: a constraint and mixed integer solver (for example OR-Tools CP-SAT or an MILP solver) for Awardsmith and the Bulwark inner and outer problems; a quadratic or convex solver for the MPC step; an SMT solver (for example Z3) for the Clearwright legality proof and the conservation checks in Keystone.
 - Backend: Python for the solver and agent layer. A thin API for the UI.
 - PayPal: the PayPal server SDK plus direct REST for Payouts, wrapped as the MCP tool. Sandbox throughout.
 - UI: a dashboard (AG Studio recommended for sponsor fit) showing the control journal and the live variance and decision view.
 - Webhooks: an idempotent handler keyed on event id and a request id on every write.

---

## 12. Suggested repository structure

```
helm/
  README.md                  this document
  LICENSE
  simulator/                 synthetic business: forecast, actuals, injectable shocks
  helm_core/                 the controller: state, forecast/variance, receding horizon optimizer, control journal
  arms/
    awardsmith/              procurement winner determination solver + Orders execution
    payout_engine/
      mete/                  contribution split
      bulwark/               attacker simulation + hardening loop
      clearwright/           legality pre flight (SMT)
      tollgate/              cross border withholding (reuse)
      keystone/              atomic batch execution + reconciliation
  paypal/
    mcp_payouts_tool/        the Payouts MCP tool (idempotent, human gated)
    orders/                  Orders v2 intake and supplier payment
    webhooks/                idempotent webhook handler
  council/                   agent orchestration (sense, decide, act)
  ui/                        control journal + variance dashboard
  tests/                     solver correctness, loop behavior, sandbox integration
  docs/                      deeper notes as they accrue
```

---

## 13. Honest risks and open questions

Carry these openly. They are the real decision points.

 - **The core must act, not report.** The single largest risk is that the controller gets shown as a chart and reads as another finance copilot. The demo must show autonomous action moving money. Protect this above all.
 - **The solvers must be load bearing.** If the buying setting has no real supplier choice, or the paying setting has un fakeable tracking, or the business has no real variance, the computation is theater. Choose a setting where all three bite (Section 5.3).
 - **Big vendors are circling.** Autonomous treasury and procurement agents are an active push from large enterprise vendors in 2026. Helm's defensible edge is the closed loop from variance to executed PayPal money moves plus the un gameable payout, not generic "AI for finance." Keep the framing on the loop and the autonomy.
 - **Field adjacency.** There is a cluster of cashflow and CFO copilot entries in the hackathon that only visualize numbers. Helm must not be mistaken for one; the autonomy and the money movement are the separators.
 - **Legal line.** No payroll, no custody. If any flow pools money in the operator or pays wages, it breaks the rules. Clearwright must enforce this and the demo must not cross it.
 - **Scope.** The full autonomous finance department is too much. Build the brain and one arm. Resist widening until the demo lands.
 - **Verify in sandbox early.** Confirm on day one that the sandbox supports partial capture, Payouts batches, and the MCP endpoints you depend on, and that Payouts is enabled on the account.

---

## 14. Competitive landscape (why this is differentiated)

The hackathon field is heavily concentrated in money in and buyer protection: agent spending guardrails and mandates, invoice chasers, refund and dispute desks, escrow and release gates, shopping and checkout agents, and reconciliation copilots. The money out side is comparatively empty, and a closed loop controller that both decides and executes money moves is absent. Among finance focused entries, the common pattern is a dashboard that reports numbers. Helm is differentiated on two axes at once: it is money out and operational (not another buyer side guardrail), and it is a closed loop that acts (not a dashboard that reports).

---

## 15. Extended levers and optional modules

Helm's loop has two core levers in the first build (buy and pay). The business money problem has more levers and more decision aids, and three of the earlier candidates plug in as genuine extensions. They are documented here as roadmap and optional modules, not part of the first build. The rule holds: a thing having a real role is not a reason to build it now. Build the brain and one core arm first.

 - **Mint (a third lever: pricing, the inflow side).** Helm can respond to variance not only by changing what it buys and pays, but by changing what it charges. Mint designs the pricing and subscription structure (tiers, packaging, dynamic adjustment), executed through Orders and Subscriptions, so price becomes a control input the controller can move when demand drifts from forecast. Honest caveats: pricing optimization is a mature, well funded external category (Pricefx shipped pricing agents in 2025, Zilliant shipped a pricing MCP server, Vendavo and PROS compete), so Helm should incorporate or wrap pricing logic as a lever rather than try to out build a dedicated pricing platform, and the optimizer needs willingness-to-pay data that is usually synthetic in a demo. The novelty is pricing as one lever inside a closed loop, not a standalone pricing engine.

 - **Candor (a decision aid: resolve calls the controller cannot compute).** The controller decides cleanly when inputs are measurable. Some decisions have no objective ground truth (is this supplier's quality acceptable, which qualitative option is better, was a contribution legitimate). Candor is a peer-prediction mechanism (Bayesian Truth Serum and its robust and multi-task variants) that elicits an honest answer to an unmeasurable question by rewarding reports that are surprisingly common and that accurately predict others, then feeds that answer back to the controller as an input. Honest caveats: peer prediction needs a large enough panel to be incentive compatible and is empirically underproven at scale, and a near neighbor already exists in the wild (a crypto, on-chain peer-prediction settlement for subjective agent work), so Candor's distinct value here is as an internal resolver inside the controller on fiat PayPal rails, not a standalone settlement product. This is the least proven of the three.

 - **Seignior (an optional arm: govern a customer loyalty currency).** If the business runs a points or rewards program, that program is a currency Helm can manage: earn rates, expiry, and a points-to-cash redemption rate, redeemed through PayPal Payouts. Seignior sets a redemption policy that caps the outstanding points liability and keeps spend on budget. Honest caveats: this applies only to businesses that run a points program, it is a large self-contained subsystem, and loyalty liability is an audited accounting area (points are a performance obligation under ASC 606, and breakage estimates need historical cohort data and audit-ready documentation, not model output alone), so any policy must be defensible to finance, not just optimal.

---

## 16. Considered and set aside

Recorded so the full decision trail is in one place and these are not re-proposed:

 - **Groundswell (fiat quadratic funding for public goods).** No clean fit inside a for-profit business steering to a forecast. Quadratic funding allocates a sponsor pool to community projects by breadth of support, which does not plug into the buy, pay, and price loop. Set aside unless the business specifically runs community or grant allocation.
 - **Cadence (compile a contract into a PayPal billing lifecycle).** Set aside because recurring billing is a solved commercial category (Stripe Billing, Chargebee, Zuora, and contract-to-billing tools such as Stigg and Tabs), so the headline claim does not survive the incumbent test.
 - **Industry seams searched and closed.** Health, agriculture, government and public sector, mobility and travel, and retail and consumer were each searched and closed: in each, the clean money rails are either held by funded incumbents or blocked by custody and regulation (payroll, insurance claims, and government disbursement are off limits), leaving no maker where a PayPal rail is the natural money leg.

---

## 17. Roadmap

 - In scope for the first build: the brain, one arm, the Payouts MCP tool, the closed loop, and the single demo screen.
 - Near term: the second arm, Tollgate, richer forecast error modeling, and scenario variety.
 - Later: multiple simultaneous inputs and partners, learned forecast models, and a library of control policies for different business types.

---

## 18. License

See LICENSE. Released under the MIT License.
