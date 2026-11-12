# Helm

[![CI](https://github.com/nirbhay221/helm/actions/workflows/ci.yml/badge.svg)](https://github.com/nirbhay221/helm/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![PayPal sandbox](https://img.shields.io/badge/PayPal-sandbox-003087.svg)

**The money layer for a creator marketplace, run by AI agents and settled on PayPal.**

AI agents shop for buyers, check deliveries, pay creators, invest their earnings and catch fraud
rings. Every dollar they touch moves through PayPal, and deterministic code and cryptography keep
each one inside rules the agents cannot break.

- **Control room (start here):** https://184-194-177-73.sslip.io/live
- **Full console (every tool):** https://184-194-177-73.sslip.io
- **Devpost entry and video (under 3 minutes):** https://devpost.com/software/helm-making-things-should-pay-on-time-and-fairly
- **API:** `docs/openapi.json`, a Postman collection in `docs/`, and a generated Python SDK in `sdk/python/`

No login, no keys and no setup are needed. Everything runs on the PayPal sandbox, so no real money moves.

---

## The problem

Every creator marketplace (presets, beats, prints, templates, ebooks, merch) runs the same back
office:

- buyers pay, and their money has to be held until delivery;
- creators wait to be paid, and someone decides every week who is safe to pay;
- fraud rings farm the platform with linked accounts;
- chargebacks claw money back after it has gone out.

Today that is a risk team and a spreadsheet. AI agents can make these calls, but no platform will let
a model move money unless it can see the limits it works within. Helm draws that line. The agents
propose; code, cryptography and PayPal dispose.

**Who it is for:** marketplaces and platforms that pay many small sellers, and the creators and
buyers on them.

---

## Try it in three minutes

Open https://184-194-177-73.sslip.io/live. Pick a role on the left; the big panel switches to what
that role works with.

1. **Buyer.**
   - In **Shop**, browse every creator's items, with their sales, return rates and a seller trust
     score (the low end of the 95% range on orders that were not returned or disputed, so a seller
     with few sales starts low and earns it).
   - Tick *real stores* and search to add Channel3 products.
   - Press **Buy now** on one: PayPal holds the money, and it waits in *Needs your approval*.
   - Press **Ask my agent** on another (or **Send my buyer agent**): watch the buyer agents search,
     quarantine a listing that hides a hijack, pick the item that fits, weighing price against
     seller trust, inside your signed budget, and place a PayPal hold.
   - Each hold shows what the seller delivered (files, sizes, SHA-256) and the AI delivery
     inspector's verdict. **Open it** to log your access, then **Accept** (a PayPal capture) or
     **Reject** (a void). Do nothing and a matching delivery auto-releases when the inspection
     window ends.
2. **Creator.**
   - In **My shop**, see your listings, what each sold and your recent sales. Click a price to
     change it.
   - **List it** to put up something new; it becomes a PayPal Catalog product.
   - **Brief me** gets your AI manager's read of your sales and your best money option.
   - **Get paid early** offers an advance priced from your own sales; the less certain your next six
     months, the less it lends.
   - **Invest with my club**: you and three community members (simulated) invest in ten real
     companies. Each member's AI agent reads live prices and Alpaca news through the market MCP
     server, picks alone, then sees the others' picks and may revise. A manager agent blends the
     picks by money, and code enforces the rules (listed companies only, none above 35%, each
     signed mandate, and none of a person's money in a company they ruled out) before Alpaca paper
     orders go out.
3. **Operator.**
   - In **Accounts**, the review queue ranks all 121 accounts by risk from their own record. Click
     one for the evidence.
   - **Scan the marketplace**: two rings are circled on the live map and their money freezes.
   - **Run one round**: six AI customers trade, and their purchases from creators with PayPal
     seller accounts are paid on PayPal.
   - **Run payday**: the payout agents debate and PayPal Payouts pays.
   - **Prove solvency** in zero knowledge.
4. Open **Money ledger** next to Trace: every dollar of the session, with its PayPal id.

Payday sends a real PayPal Payouts batch from the platform's sandbox balance. If that balance runs
out, PayPal's own refusal (INSUFFICIENT_FUNDS) is shown, and nothing is booked.

---

## The control room

One screen where you act and see everything respond. Nothing on it is a recording: every action
runs the real agent graphs, and their steps stream to the page over server-sent events.

**What you can see**

- **Live map.** Every account, PayPal and the platform. A ring around a dot shows what that account
  just did, gold dots are money moving, and red dashed outlines are fraud rings. Hover any dot for who
  it is and what it did.
- **Shop.** The buyer's catalog: creator listings (search, category, price) and real products from
  Channel3. You can buy an item yourself or hand it to your agent.
- **My shop.** The creator's listings with sales, revenue and returns. Prices can be edited in the
  grid, listings can be taken down, and recent sales are listed below.
- **Accounts.** The operator's review queue: every account with a risk score, the evidence behind
  it (shared device, card or IP, and return rates), what it is owed, and freeze or clear buttons.
- **Agents.** The LangGraph that is running (buyer, payday, AI customers, fraud), lit up step by step
  with the path it took.
- **Money flow.** Holds, earnings, fees, payouts, freezes, advances and clawbacks.
- **Trace and money ledger.** A Langfuse-style tree and waterfall of every step and model call, and
  an AG Grid ledger with one row per dollar movement.
- **Inspector.** Click any agent, trace row, ledger row or account to see what it saw, the tokens it
  streamed and what it decided.
- **What is real?** Every activity line and ledger row is tagged PayPal, AI, code or sim, and the
  header lists exactly what is simulated.

**What you can do**

- *Buyer:*
  - browse and search the catalog;
  - buy directly;
  - send your buyer agent, with an optional planted hijack;
  - open each delivery, see the AI inspector's verdict, and accept or reject it.
- *Creator:*
  - sell something (registered as a PayPal Catalog product);
  - reprice or take down a listing;
  - get your AI manager's briefing;
  - take an advance priced from your sales;
  - receive a dispute.
- *Operator:*
  - review and freeze or clear accounts;
  - scan for fraud rings;
  - run payday;
  - prove solvency;
  - open the market so AI customers trade every 30 seconds.

---

## Who confirms the delivery happened

A PayPal hold only proves the buyer paid. Before the money moves, Helm answers "was it really
delivered?" the way escrow services and PayPal seller protection do: evidence from a system of record,
then an inspection window.

1. **The seller delivers through the platform.** A digital item is recorded as a file manifest with its
   size and SHA-256 hash; a physical item as a shipment with a tracking number. Sellers behave like
   their own record: one whose buyers often return things sometimes ships the wrong file, an empty
   archive or only a preview.
2. **An AI delivery inspector checks it.** A buyer-side agent (gpt-5-mini) compares what the listing
   promised with what arrived and says matches, mismatch or incomplete, with the checks it made. It
   streams live in the buyer graph like every other agent.
3. **Opening the file is logged.** The time and masked IP of the buyer's access are recorded, the kind of
   proof of delivery PayPal asks for on intangible goods.
4. **The buyer accepts or rejects; silence releases only a match.** If the buyer does nothing, the hold
   is captured when the inspection window ends (3 minutes in the demo, days in production), but only
   when the inspector found a match. A flagged delivery waits for the buyer, and a model that does not
   answer leaves the delivery unverified, never silently passed.

Measured: on ten labelled deliveries (six correct, four broken: empty, preview only, wrong product),
the inspector was right 10 of 10, on two separate runs.

## Everything else, in the full console

https://184-194-177-73.sslip.io has three lanes of tools that read and write the same account.

**Earn (creator)**

- **Your creator page.** Earnings, a Holt forecast, what to make next, money moves that need your
  approval, and your tax statement.
- **Policy compiler.** Plain-English treasury policy compiled by the model into objective weights
  and hard constraints.
- **Signal reader.** An operational signal read into a bounded forecast adjustment.
- **Advance pricing.** Risk-priced from the sales ledger. A band on default risk comes from the creator's own
  history (how far the estimate could move over six more months), so a thin or volatile file lends less.
- **RL advance-sizer.** A contextual bandit trained offline on simulated defaults.
- **Tax regime.** US 1099-K and EU DAC7 thresholds.
- **Invest at live prices.** Alpaca paper orders.
- **Investment club.** You and three community members (simulated) invest together in ten real companies. Each member has an AI agent that reads live prices and Alpaca news through the market MCP server, picks alone, then sees the others' picks and may revise (a LangGraph fan-out in two rounds, after TradingAgents and AlphaAgents). A manager agent blends the picks by money. Code then enforces the rules: listed companies only, none above 35%, each person within their signed mandate, and no member's money in a company they ruled out. Orders go to Alpaca paper trading, and each agent remembers its past picks.

**Spend (buyer)**

- **Spend earnings.** A real product found via Channel3, screened for prompt injection, and bound to
  a single-use intent token.
- **Buyer (multi-agent).** The full buyer graph, step by step.
- **Agent negotiates.** Counters a creator's listing down to your per-item cap, then settles on
  PayPal Orders.
- **Agent mandate (crypto).** An owner-signed ES256 mandate; a forged or tampered one is refused.
- **Agent identity.** A signed agent passport.
- **Pool together.** Co-own a position or clear a volume discount, split by the Shapley value.
- **Pay on proof.** PayPal authorizes and holds; code releases on proof or voids. Tick "cheat" to see
  the hold voided.
- **x402 micropayment.** Pay per request.

**Platform (operator)**

- **Your marketplace.** The 120-creator marketplace, scanned by the abuse and ring engines.
- **Operator (multi-agent).** The payout graph, step by step.
- **Platform P&L.** Expected revenue and loss, RAROC, and a CECL-style provision.
- **Agent grounding.** Hybrid semantic and keyword retrieval over a sourced financial knowledge base,
  also served over MCP.
- **Proven safe (Z3).** An SMT proof that no sequence of deals can overspend the signed budget.
- **Zero-knowledge reserves.** A Pedersen-commitment range proof that the fund covers liabilities;
  set liabilities above the lots and it becomes unprovable.
- **Fraud graph.** Kuzu multi-hop Cypher finds rings whose members share no single identifier.
- **Audit and reconcile.** Hash-chained receipts reconciled against PayPal's record, and
  sanctions, structuring, velocity and duplicate screening on every payout.

---

## How the agents work

- **Buyer (money in).**
  - A LangGraph supervisor routes worker agents: `understand -> search -> safety -> select ->
    authorize -> settle -> deliver -> inspect`, and it can loop back to search (bounded).
  - Listings are screened for prompt injection before any model reads them.
  - The choice must fit the owner's signed mandate, whose category limit is checked against the
    listing's own category.
  - Settlement is a PayPal authorization. The seller's delivery is recorded and checked by the AI
    delivery inspector, and the hold is captured only on the buyer's acceptance or a matching
    delivery whose inspection window ended.
- **Operator (money out).**
  - The flow is `signal_analyst -> risk_analyst -> bull -> bear -> (debate again or decide) ->
    manager -> compliance_gate -> dispose`.
  - The risk analyst judges each creator from their real record (tenure, sales, returns,
    chargebacks, ring links).
  - The manager sets a risk multiplier.
  - The dispose step caps every proposal to what is owed and what is safe, and Payouts holds large
    batches for a human.
- **Investment club.**
  - The flow is `club_research (MCP) -> club_reflect -> four member agents in parallel ->
    club_discuss -> the members again (round 2) -> club_manager -> club_dispose -> broker`.
  - Research spawns the market MCP server as its own process and calls `market_snapshot` and
    `market_news` over stdio; reflect compares each agent's past picks with today's prices.
  - Round 1 is independent; in round 2 each agent sees the others and changes only when another
    reason is better for its own member, because LLM crowds that see each other first herd.
  - The manager blends the picks by how much each person put in; dispose (code) drops off-list
    tickers, caps each company at 35%, checks every signed mandate and removes each person's
    refused companies from their own share.
- **AI customers.**
  - Six marketplace members, each a model with a persona, memory and periodic reflection (after
    Generative Agents).
  - Each one chooses to list, buy, return or hold.
  - Their activity is emergent, not scripted, and it is what the fraud engines have to catch.
- **Grounding.** Each agent gets the financial principles relevant to its decision retrieved into
  its prompt (Basel BCBS 283, FASB ASC 326, IRS 1099-K, EU DAC7, OWASP LLM01, Shapley 1953), and the
  cycle records which ones it applied.

**What is model-driven and what is not**

- *Model-driven:* compiling a policy, pay or hold, the debate, reading signals, the buyer's
  understanding and choice, the delivery inspection, the club members' picks and the club
  manager's blend, and the customers' decisions.
- *Deterministic or cryptographic:* the allocation solver, the cash controller, caps, conformal
  intervals, tax thresholds, compliance screening, signatures, hash-chained receipts, and the Z3
  and zero-knowledge proofs.

---

## PayPal

- **Orders v2:** create, authorize (hold), capture, void and refund, with the selling creator as the
  payee. Used for the buyer's holds, direct purchases and AI customers' payments.
- **Payouts:** idempotent batches, a human approval gate and cross-border withholding. Payday uses
  them, and a refusal is reported with PayPal's issue code.
- **Catalog Products:** a creator's new listing is registered as a PayPal product.
- **Customer Disputes:** the CUSTOMER.DISPUTE.CREATED webhook charges back the seller, and evidence
  goes to provide-evidence while the dispute is WAITING_FOR_SELLER_RESPONSE.
- **Webhooks:** signature verification and event de-duplication.
- **Multiparty (opt in):** with `HELM_PAYPAL_MULTIPARTY=1`, orders carry the platform fee and
  delayed disbursement.
- **MCP:** a Payouts tool and three domain MCP servers (payouts, market, trust) in `mcp_server/`.

Every call is booked only when PayPal accepts it.

## AI

Any OpenAI-compatible model works. The live demo runs OpenAI gpt-5-nano with gpt-5-mini as the
fallback, streamed token by token. gpt-5-mini also runs the delivery inspector and the investment
club's member and manager agents. The model client retries with the provider's suggested wait and
falls through the chain, and the UI names which model answered.

## Sponsor tools

- **AG Grid:** the streaming money ledger, the editable My shop grid, the accounts review queue,
  and the console's grids.
- **Channel3:** real-store search, both for the buyer agent and for the Shop view.
- **Postman:** a full collection in `docs/`.
- **APIMatic:** a generated Python SDK in `sdk/python/`.

---

## Measured, not claimed

- **Property testing found a real money bug.**
  - Scaled payout shares were rounded to the nearest cent, so a batch could exceed its cap.
  - A brute-force check of 200,000 cases found this in about 14% of scaled batches, by up to 2 cents.
  - Shares now round down, and a regression test covers it.
- **The learned advance policy finds the break-even from data.**
  - Expected profit turns negative above a default probability of about 13%.
  - Net profit per creator over 120,000 simulated rounds: learned 30.70, rule of thumb 7.51, always
    lend 25% -3.77, always lend the maximum -15.07.
- **Both agent journeys are tested end to end on the live model.** A silent fallback anywhere fails
  the test and names the step.
- **The AI is evaluated live.** A golden eval asserts properties of the model's output, including
  that it does not obey an injected instruction.
- **A refused PayPal call is reported as refused.** This caught holds that only looked successful:
  an unapproved order cannot be authorized (ORDER_NOT_APPROVED).
- **Proof costs.** The zero-knowledge solvency proof with 32 bit proofs takes about 1.4 s. The Z3
  budget proof returns PROVEN_BOUNDED, plus a 6-deal counterexample when the running-total guard is
  removed.
- **Tests.** 314 tests: unit, Hypothesis property-based, proof, and live end-to-end. CI runs on
  every push.

---

## What is real and what is simulated

**Real:**

- every PayPal sandbox call;
- every model call;
- Channel3 product search;
- live market prices, Alpaca news and Alpaca paper orders;
- the solvers, the Z3 and zero-knowledge proofs, and the graph and vector databases;
- the fraud and abuse engines, and every signature.

**Simulated, and labelled as such:**

- **The other 120 creators and their four months of order history.** These are generated, with two
  fraud rings planted and never labelled.
- **The AI customers' wallets.** A purchase from a creator with a sandbox seller account is still
  paid on PayPal.
- **The sellers' deliveries.** The files a seller delivers are generated manifests, because the sellers
  are simulated. The hash, the AI inspection, the access log and the PayPal capture are real.
- **The other three investment club members.** Their goals and money are simulated; their AI
  agents, the market data and the paper orders are real.
- **The dispute button.** It simulates the webhook; the real receiver is `/api/paypal/webhook`.
- **The advance book and the safety fund.** Lending is regulated in production.
- **Payees.** A creator is the PayPal payee only when `HELM_SELLER_PAYEE_EMAILS` maps them to a
  sandbox seller account.

The zero-knowledge proof binds liabilities to the published figure. Like any proof of reserves, it
cannot by itself prove that the committed lots exist at a bank; that needs an attested balance feed.

---

## Run it yourself

```bash
pip install -r requirements.txt
python -m pytest -q            # unit, property-based and proof tests, no credentials needed
uvicorn ui.app:app             # http://127.0.0.1:8000 (control room at /live)
python -m mcp_server           # payouts MCP server (also: market, trust)
```

With no credentials, the app runs end to end in a clearly labelled demo mode. To use the real
rails:

1. `cp .env.example .env`
2. Set `DEMO_MODE=0` and add your PayPal sandbox, model, Channel3 and Alpaca keys.
3. Run `python scripts/smoke_all.py`.

Keys are read from the environment only and are never committed.

## Layout

- `ui/` the app.
  - `live_page.py`, `live_hub.py` and `live_views.py` make up the control room: actions, the
    server-sent events hub, the d3 views, the catalog, the shop, the review queue and the AG Grid
    ledger.
  - `page.py` is the full console, and `app.py` holds the API.
- `agent/` the model layer: the operator graph, policy compiler, signal desk, the resilient model
  client, and the live tap that streams agent steps.
- `market/` the marketplace: the buyer graph, AI customers, abuse and ring engines (Kuzu), signed
  mandates and agent identity, negotiation, pooling, product search and the injection guard, x402,
  escrow, the Z3 verifier, compliance screening, and the knowledge base.
- `marketplace/` deterministic finance: the allocation LP, cash controller, conformal intervals,
  P&L, advances and the learned policy, forecasting, investing, reconciliation, receipts and the
  zero-knowledge reserves proof.
- `paypal/` Orders, Payouts, authorizations, Catalog, webhooks, the ledger and the Payouts MCP tool.
- `mcp_server/` three domain MCP servers: payouts, market, trust.
- `docs/` the OpenAPI spec, the Postman collection, the Devpost text, the presentation guide and the
  video script.
- `tests/` unit, property-based, proof and live end-to-end tests.

Deployed on an isolated AWS instance. MIT licensed.
