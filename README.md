# Helm

[![CI](https://github.com/nirbhay221/helm/actions/workflows/ci.yml/badge.svg)](https://github.com/nirbhay221/helm/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![PayPal sandbox](https://img.shields.io/badge/PayPal-sandbox-003087.svg)

**An autonomous money layer for a creator marketplace, settled on PayPal.**

**Live demo (no setup, no login, no keys):** https://184-194-177-73.sslip.io
Open it and use the **Start here** row: four buttons, each runs a headline capability live
against the real PayPal sandbox and a live model.

Helm is one person-account with three sides. Creators **earn** and get paid out; anyone
can **spend** as a buyer through agents boxed in by signed mandates; and the **platform**
runs the treasury and *proves it is safe*. Teams of AI agents propose the judgment;
deterministic code and cryptography dispose the money and the limits.

---

## One account, one set of books

Your browser gets its own live two-sided marketplace: 120 creators who sell and buy, their
listings and four months of order history, with two coordinated fraud rings planted in that
history and never labelled. **You are one of its sellers**, with three listings and your own
sales. Every tool reads and writes this one marketplace and one set of books, so the features
act on each other instead of being separate demos (the **Your account** strip at the top):

- **What the platform owes creators, and your earnings, are computed, not typed in.** Each
  sale's net (after the 10% platform fee) is a dated lot in a per-creator ledger. It counts
  as settled, safe to pay, only once its 30-day chargeback window has closed. Returns and
  chargebacks claw it back, and money already paid out becomes a debt recouped from future
  sales.
- **Buy from another creator** (the buyer agent and the shop search your marketplace's listings
  before outside stores) and the money moves from your earnings to theirs; the platform keeps
  its fee. Their PayPal seller account is named as the order's payee when one is configured.
- **Your agent negotiates** with a creator's listing under the mandate your owner key signed,
  countering down to your per-item cap, and the deal settles on PayPal Orders.
- **Scan the marketplace** and the abuse and ring engines suspend the planted rings; a
  suspended creator's earnings freeze, so the operator cannot pay them and buyers cannot buy
  from them.
- **Run the operator** and its cohort is you, the creators owed the most, and anyone flagged,
  each judged from their real record (tenure, sales, returns, chargebacks, ring links). Its
  payouts pay down the creators' ledger.
- **A buyer disputes a sale** (PayPal's CUSTOMER.DISPUTE.CREATED webhook, or a labelled
  simulation of it) and it is charged back to the selling creator, the abuse engines re-run,
  and the seller's evidence is built from the receipt chain.
- **Your creator page** shows your earnings, a Holt forecast, what to make next, money moves
  that need your approval, and your tax statement, all from your own sales.
- **Take an advance** and it leaves the safety fund: the solvency margin drops, the
  zero-knowledge proof is produced over the smaller fund, and the P&L prices your real loan.
  Later payouts to that creator withhold 25% to repay it.
- **Buy something** and your earnings are held on PayPal (a real sandbox authorization), not
  spent. You confirm delivery to capture it or report a failure to void it and get the money
  back. You cannot spend more than you have earned, and the running total spent under your
  signed mandate carries across buys.
- The **audit desk** reconciles your own receipts against PayPal's recorded captures, and the
  tamper demo edits a copy, never your real chain.

Lend too much and the platform can no longer prove it is solvent.

---

## What makes it different

- **Agents that collaborate, not one model in a loop.** The payout operator is a LangGraph
  of role agents: a signal analyst, a risk analyst, a bull and a bear who debate how
  aggressive to be, a manager, then a compliance gate. The buyer is a LangGraph supervisor
  routing worker agents (understand, search, quarantine, select, authorize, settle). Every
  agent only proposes; the solver, the guardrails and PayPal dispose.
- **It proves its own solvency in zero knowledge.** The platform proves its hidden reserves
  cover the *published* liabilities (outstanding advances and pool commitments) without
  revealing any balance: Pedersen commitments on bn128 plus a bit-decomposition range proof
  with Chaum-Pedersen OR proofs. The liability commitment is opened and checked against the
  published figure, so a fund cannot prove against a smaller number, and an insolvent fund
  cannot produce a proof at all.
- **It formally proves its agents cannot overspend.** A Z3 SMT proof shows that for *any*
  sequence of deals, cumulative spend stays inside the owner's signed budget. It is an
  unbounded inductive-invariant proof, not a bounded check, plus machine-found
  counterexamples showing each guard is necessary, emitted as an ES256-signed verdict.
- **Its money invariants are property-tested, not just example-tested.** Hypothesis throws
  thousands of adversarial inputs (NaN, negative and infinite amounts, unknown payees,
  replayed tokens, tampered receipts, split payments) at every guardrail. This found a real
  bug, described below.
- **Three databases, each for what it is good at.** SQLite for the money ledger, the Kuzu
  embedded graph database for fraud rings (multi-hop Cypher finds rings whose members share
  no single identifier), and an embedded vector store for the agents' financial knowledge.
- **A learned lending policy.** A contextual bandit, trained offline on simulated defaults,
  sizes creator advances by estimated risk inside the hard caps.

---

## Measured, not claimed

Every figure below is produced by code in this repo.

- **Property testing found a real money bug.** When the agents proposed more than the safe
  release, the operator scaled each share and rounded it to the nearest cent, so the total
  could exceed the cap. A brute-force check of 200,000 cases found it in about 14% of scaled
  batches, by up to 2 cents. Shares now round down, and a regression test reproduces the
  failure on the old code (paid 3108.13 against a 3108.12 cap) and passes on the fix.
- **The learned advance policy finds the break-even from data.** Expected profit turns
  negative above a default probability of spread / loss-given-default = 0.12 / 0.9, about
  13%. The bandit learned to lend in full up to the 10-15% risk bucket and nothing above it.
  Net profit per creator over 120,000 simulated rounds: learned **30.70**, rule of thumb
  7.51, always lend 25% **-3.77**, always lend the maximum **-15.07**.
- **The agents stay on the model under load.** Hosted models rate-limit. The model client
  retries with the provider's suggested wait and then moves across a chain of models, each
  metered separately. Four back-to-back operator cycles all ran on the model in 11 to 14
  seconds each; before the change, a burst dropped every cycle to the deterministic fallback.
  The UI names each model that answered, and says so plainly when a fallback ran.
- **The AI is evaluated live.** A golden eval runs the real model and asserts properties of
  its output: it reads policy intent, excludes the right country, gets a signal's direction,
  ignores irrelevant text, does not obey an injected instruction, and stays bounded on a
  conflicting policy (7 of 7 passing on the live model).
- **Both agent journeys are tested end to end on the live model.** `tests/test_e2e_live.py`
  drives the operator and the buyer through the API and checks three levels: every agent
  step ran on the model (a silent fallback anywhere fails the test and names the step and
  why), the graph took the expected route, and the end state is right. The flagged creator
  is held, a held creator is never paid, the buyer gets a laptop rather than a laptop stand,
  a purchase outside the owner's categories is refused, and the account's books move by
  exactly the amounts decided. With the marketplace in place it also checks that suspended
  ring members are held and never paid, that the buyer prefers a fitting creator listing and
  the sale credits that creator, and that a dispute claws back from the seller.
- **A PayPal call that is refused is reported as refused.** Every order, authorization,
  capture, void and refund is booked only when PayPal accepted it, with PayPal's own issue
  code otherwise. This caught holds that had looked successful: an unapproved order cannot be
  authorized (ORDER_NOT_APPROVED). Sandbox holds now carry PayPal's test card as the buyer's
  approval and return real authorizations.
- **The buyer's mandate is the owner's, not the agent's.** The owner signs the intent mandate
  before any agent runs (the AP2 order). It is verified against the owner's registered key,
  and its category limit is checked against the listing's own category, so an agent cannot
  relabel a product to get it past the limit.
- **Proof costs.** The zero-knowledge solvency proof with 32 bit proofs takes about 1.4 s; the
  Z3 budget proof returns PROVEN_BOUNDED with a 6-deal counterexample when the running-total
  guard is removed.

---

## The three sides (what you can do in the live console)

**Earn (you are a seller).** Write a treasury policy in plain English and watch the model
compile it into objective weights and hard constraints; read an operational signal into a
bounded forecast adjustment; price an advance against proven earnings (risk-priced, with a
conformal uncertainty band so an uncertain estimate lends less) or let the learned policy
size it; see a US 1099-K / EU DAC7 tax regime; invest earnings at live market prices on
Alpaca paper.

**Spend (you are a buyer).** Run the multi-agent buyer end to end; verify an owner-signed
ES256 mandate (a forged or tampered one is refused by the signature); carry an **agent
identity** passport; **pool** with others to co-own a position or clear a volume discount
split by the Shapley value; **spend earnings** on a real product (found via Channel3,
screened for prompt injection, bound to a single-use intent token); settle with
**pay-on-proof escrow** (PayPal authorizes and holds, code releases on proof or voids); or
pay per request with **x402** agentic micropayments.

**Platform (it runs and proves the money).** Run the multi-agent operator; the **Platform
P&L** (expected revenue, loss, RAROC, provision, fund coverage); **agent grounding** (hybrid
semantic and keyword retrieval over a sourced knowledge base, also served over MCP); the
**Z3** mandate proof; the **zero-knowledge** reserves proof; the graph-database **fraud
ring** finder; and an **audit and reconcile** desk (tamper-evident hash-chained receipts,
reconciliation against PayPal's record, and sanctions / structuring / velocity / duplicate
screening on every payout).

---

## How the agents work

**Operator (money out).** One cycle is a LangGraph: `signal_analyst -> risk_analyst -> bull
-> bear -> (debate again or decide) -> manager -> compliance_gate -> dispose`. Each agent
gets the financial principles relevant to its decision retrieved into its prompt (expected
loss, CECL provisioning, large-exposure limits, RAROC, segregation of duties), and the cycle
records which principles it applied. The manager proposes amounts and a risk multiplier; the
cash controller sizes the safe release from a forecast with an uncertainty buffer; the
dispose step clamps every proposal to what is owed and what is safe, and Payouts holds large
batches for a human.

**Buyer (money in).** A supervisor routes worker agents and can loop back to search again
(bounded). Listings are screened for prompt injection before the model sees them; the
choice must fit the owner's signed mandate; settlement is a PayPal authorization that is
captured only on proof.

**Grounding.** The knowledge base cites named standards (Basel BCBS 283, FASB ASC 326, IRS
1099-K, EU DAC7, OWASP LLM01, Shapley 1953). Retrieval is hybrid: ONNX sentence embeddings
(bge-small-en-v1.5, CPU only) blended with keyword overlap, because pure embeddings picked
the wrong principle on financial paraphrases in our tests. A deterministic hashing embedder
is the fallback.

---

## The design: the agent proposes, deterministic code and crypto dispose

- **Model-driven** (varies run to run): compiling an English policy, deciding who to pay
  and who to hold, the debate, reading signals, the buyer's understanding and choice, the
  per-creator recommendations.
- **Deterministic / cryptographic** (exact, every time): the allocation solver, the cash
  controller, expected-loss and advance caps, the conformal intervals, the tax thresholds,
  compliance screening, the ES256 mandate and identity signatures, the hash-chained
  receipts, and the Z3 and zero-knowledge proofs.

This attacks the two documented causes of financial-agent error (missing domain knowledge,
numerical mistakes): knowledge through retrieval, numbers through deterministic tools.

---

## PayPal + AI

PayPal: Orders v2 (money in and agent purchases, with the selling creator as the payee),
Payouts (money out, idempotent batches, a human approval gate, cross-border withholding), the
full authorize / capture / void lifecycle for escrow, Customer Disputes (the dispute webhook
charges back the seller; evidence goes to provide-evidence while the dispute is
WAITING_FOR_SELLER_RESPONSE), and webhook signature verification with event dedupe. With
`HELM_PAYPAL_MULTIPARTY=1` (an approved PayPal partner), orders also carry the platform fee and
DELAYED disbursement, released per seller by a referenced payout. A Payouts tool
is exposed over MCP. Everything runs on the PayPal sandbox; no real money moves.

AI: any OpenAI-compatible model (vendor-neutral; the live demo uses gpt-oss-120b with a
fallback chain) drives the operator and buyer graphs, policy compiler, signal desk and
per-creator manager, grounded in the knowledge base and constrained to propose, never to
move money.

Sponsor tools used: **AG Grid** (the data grids), **Postman** (a full API collection),
**Channel3** (buyer-side product search), and **APIMatic** (a generated Python SDK from the
documented OpenAPI spec).

---

## What is real and what is simulated

Real: the PayPal sandbox calls, live market prices and Alpaca paper orders, Channel3 product
search, the model calls, the solvers, the Z3 and zero-knowledge proofs, the graph and vector
databases, the fraud and abuse engines, and every signature.

Simulated, and labelled as such: the creator population and the marketplace's history are
generated, not real users; a creator is paid as the PayPal payee only when
`HELM_SELLER_PAYEE_EMAILS` maps them to a sandbox seller account, otherwise money settles to the
platform account and the UI says so; a plain sandbox app refuses Multiparty's platform fee and
delayed disbursement (PLATFORM_FEES_NOT_SUPPORTED, DELAYED_DISBURSEMENT_NOT_SUPPORTED), so those
are off unless enabled; the dispute button simulates the webhook (the real receiver is
`/api/paypal/webhook`); the advance book and safety fund are a simulated loan book
(lending is regulated in production); the learned advance policy is trained on simulated
defaults. The ZK proof binds the liabilities to the published figure, but like any
proof-of-reserves it cannot by itself prove that the committed reserve lots exist at a bank;
that needs an attested balance feed.

---

## Testing it (judges start here)

**A. The hosted demo, zero setup.** Open https://184-194-177-73.sslip.io and use the Start
here buttons. Then try: Platform -> Zero-knowledge reserves (set liabilities above the lots
to see it become unprovable); Platform -> Proven safe (Z3) (tick "forge" to see a tampered
mandate rejected); Spend -> Pay on proof (tick "cheat" to see the hold voided); Spend ->
Spend earnings (tick "plant a prompt-injection listing" and "tamper"). Available through
the judging period.

**B. Run it yourself.**

```bash
pip install -r requirements.txt
python -m pytest -q            # unit, property-based and proof tests, no credentials needed
uvicorn ui.app:app            # the dashboard at http://127.0.0.1:8000
python -m mcp_server          # payouts MCP server (also: market, trust)
```

With no credentials the app runs end to end in a clearly labelled demo mode, and the live
AI eval skips itself. To exercise the real rails, `cp .env.example .env`, set `DEMO_MODE=0`
plus your PayPal sandbox, model, Alpaca and Channel3 keys, then `python scripts/smoke_all.py`
and `python -m pytest tests/test_ai_golden.py`. Keys are read from the environment only and
never committed.

**Or exercise the API directly.** Import `docs/helm.postman_collection.json` into Postman
(every endpoint with example bodies, pointed at the live demo). A typed Python client SDK
generated from the OpenAPI spec with APIMatic is in `sdk/python/`; the spec is
`docs/openapi.json`.

---

## Layout

- `agent/` the model layer: the operator graph, policy compiler, signal desk, and the
  resilient model client (retry, model chain, honest model reporting).
- `marketplace/` deterministic finance: the allocation LP, cash controller, conformal
  intervals, predictive P&L, risk-priced advances and the learned advance policy, economics,
  forecasting, investing, reconciliation, tamper-evident receipts, and the zero-knowledge
  reserves proof.
- `market/` the marketplace: the buyer graph, agentic customers, two-sided abuse, the Kuzu
  fraud-ring graph, signed mandates and agent identity, a2a commerce, pooling, product search
  and the injection/intent guard, x402, escrow, the Z3 verifier, compliance screening, the
  vector store and the financial knowledge base.
- `arms/payout_engine/` the un-gameable split and atomic, idempotent execution.
- `paypal/` Orders, Payouts, authorizations, webhooks, the ledger, and the Payouts MCP tool.
- `mcp_server/` three domain MCP servers: payouts, market, trust.
- `ui/` the dashboard (start-here tour, three-lane live console, AG Grid, Chart.js).
- `tests/` unit, property-based (Hypothesis), proof, and live AI golden tests; CI runs on
  every push.

34 live endpoints, deployed on an isolated AWS instance. No real money moves anywhere.
