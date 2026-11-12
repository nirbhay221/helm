# Helm: Devpost submission text

Paste each section into the matching Devpost field.

## Tagline

An autonomous money layer for a creator marketplace: AI agents decide who gets paid, PayPal moves the money, and code and cryptography keep every dollar inside the rules.

## Inspiration

Every creator marketplace runs the same hidden back office. Buyers pay, creators wait for payouts, fraud rings farm the platform, chargebacks claw money back, and someone has to decide every week who is safe to pay. Today that is spreadsheets and a risk team. AI agents can do the judgment, but nobody will let a model move money without proof that it cannot overspend, cannot be hijacked by a listing, and cannot pay a fraud ring. Helm is that back office, with agents that propose and code that disposes.

## What it does

Open the control room at https://184-194-177-73.sslip.io/live and act in three roles. Every action runs the real agent graphs and streams every step, model token, PayPal call and guardrail to the screen.

- **As a buyer**, browse and search the Shop: every creator's listings with their sales, return rates and a seller trust score (the low end of the 95% range on orders that were not returned or disputed, so few sales means a lower score), plus real products from Channel3. Buy one yourself (PayPal holds the money) or press Ask my agent. Given a need and a budget, a LangGraph supervisor routes worker agents: understand the need, search creator listings and then real stores (Channel3), quarantine a listing that hides a prompt-injection hijack, pick the item that fits, weighing price against seller trust, inside the owner's ES256-signed mandate, and place a PayPal Orders hold. The seller then delivers through the platform (files and their SHA-256, or a tracking number), an AI delivery inspector checks it against the listing, and your access to the file is logged. You accept (capture) or reject (void); if you say nothing, a matching delivery releases when the inspection window ends, and a flagged one waits for you.
- **As a creator**, My shop shows your listings, what each sold and your recent sales, with prices editable in the grid. List something for sale and it becomes a PayPal Catalog product and a live listing. AI customers, each a model with a persona, memory and reflection, trade on the marketplace; when one buys from a creator with a sandbox seller account, PayPal is paid for real with that creator as the payee. Your AI manager briefs you from your own sales, and you can take an advance priced from your proven earnings. You can also put earnings into an investment club with three community members (simulated): each member's AI agent reads live prices and Alpaca news through the market MCP server, picks on its own, then sees the others' picks and may revise; a manager agent blends them by money, code enforces a 35% cap per company, each signed mandate and each person's refusals, and the orders go to Alpaca paper trading.
- **As the operator**, the business is visible: Helm earns a 10% take on each sale and the fee on each advance. Work a review queue that ranks every account by risk from its own record (shared device, card or IP, and return rates) and freeze or clear each one, scan for fraud (an abuse engine plus a Kuzu graph database that finds rings sharing devices, cards and IPs, which freezes their earnings), run payday (a signal analyst, a risk analyst, a bull and a bear who debate, a manager, a compliance gate, then PayPal Payouts, capped by code to the safe release), and prove in zero knowledge that the safety fund covers every creator without revealing a balance.

The big panel switches between the live marketplace map, the Shop, My shop and the Accounts queue, and stays in sync with the agent graph of whatever is running, a money flow, and a trace with a streaming AG Grid money ledger. Every event is tagged PayPal, AI, code or simulated, so a judge always knows what is real.

## How I built it

- **Agents:** LangGraph for the buyer (supervisor and workers), the operator (role agents with a bull and bear debate) and the investment club (parallel member agents in two rounds, then a manager). Any OpenAI-compatible model; the live demo runs OpenAI gpt-5-nano with gpt-5-mini as the fallback, streamed token by token.
- **PayPal:** Orders v2 (create, authorize, capture, void, refund, with the selling creator as payee), Payouts (idempotent batches, a human approval gate), Catalog Products, Customer Disputes (webhook with signature verification, provide-evidence), and a Payouts MCP server.
- **MCP:** three servers built on the Python MCP SDK (payouts, trust, market). The club's agents call the market server over stdio for live prices and news.
- **Deterministic and cryptographic guards:** an allocation LP and cash controller, ES256 signed mandates and agent identity, hash-chained receipts, a Z3 proof that cumulative spend can never exceed the signed budget, and a Pedersen-commitment range proof of solvency.
- **Data:** SQLite for the money ledger, Kuzu for fraud-ring graph queries, an embedded vector store for the agents' financial knowledge base.
- **Control room:** FastAPI with server-sent events from a per-session hub, d3 force and SVG views, AG Grid for the streaming ledger.
- **Sponsor tools:** AG Grid, Channel3, Postman (full collection), APIMatic (generated Python SDK).
- **Hosted** on an isolated AWS EC2 instance.

## Challenges I ran into

- **PayPal said no in ways that looked like yes.** An unapproved order cannot be authorized, so holds that looked successful were not. Every call is now booked only when PayPal accepts it, and a refusal shows PayPal's own issue code.
- **Sandbox Payouts draw from the business account's balance, and card captures do not refill it.** I learned that the hard way, and payday now reports PayPal's exact refusal rather than pretending to pay.
- **Rounding bug.** Property-based testing found that scaled payout shares could exceed the cap by up to 2 cents in about 14% of batches. Shares now round down, with a regression test.
- **Hosted models rate-limit.** The model client retries with the provider's suggested wait and falls through a chain of models, and the UI names which model answered.

## Accomplishments I'm proud of

- The agents propose and the code disposes. A Z3 proof shows no sequence of deals can overspend the signed mandate.
- The platform proves its own solvency in zero knowledge, and an insolvent fund cannot produce a proof at all.
- A planted prompt-injection listing is quarantined before any model reads it.
- Fraud rings are found by multi-hop graph queries, not by labels, and their money freezes on the spot.
- 314 tests, including Hypothesis property tests on every money invariant and live end-to-end tests that fail if any agent silently fell back.

## What I learned

The hard part of agentic payments is not getting a model to choose. It is drawing a clean line between what the model is allowed to decide and what only code and cryptography may do, and then showing that line to a human in real time.

## What's next

Real seller onboarding through PayPal partner referrals so every creator is a real payee, Multiparty platform fees and delayed disbursement once the app is approved, and an attested balance feed so the solvency proof is bound to money at a bank.

## What is real and what is simulated

Real: every PayPal sandbox call, every model call, Alpaca news and paper orders, Channel3 search, the fraud engines, the solver, the signatures and both proofs. Simulated: the other 120 creators and their sales history, the three other investment club members, the AI customers' wallets (their purchases from creators with sandbox seller accounts are still paid on PayPal), and the dispute button (a simulated webhook; the real receiver is live).

## Built with

python, fastapi, langgraph, openai, paypal-orders, paypal-payouts, paypal-catalog, paypal-disputes, mcp, ag-grid, channel3, d3, kuzu, sqlite, z3, hypothesis, postman, apimatic, aws
