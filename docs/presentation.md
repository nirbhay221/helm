# Helm: what to show

There are two parts:

- **Part A** is the 3-minute video. Judges stop watching at 3:00, so it covers every major capability
  quickly, mostly in the control room.
- **Part B** is the full tour: every feature, where it lives, what to click and what to say. Use it
  for a live demo, a longer walkthrough, or to check that nothing is missed.

## Before you record or present

1. **Top up the platform's sandbox balance.**
   - Go to developer.paypal.com, then Sandbox Accounts, then the business account, then Edit balance.
   - Add $100,000 or more.
   - Each payday sends about $1,200 to $2,000, so without this payday fails with INSUFFICIENT_FUNDS.
2. **Open https://184-194-177-73.sslip.io/live in a fresh browser profile**, at 1600 by 1000 or
   larger. A fresh profile means a fresh account.
3. **Turn the market off.** Zoom the browser to 100%.
4. **Do one warm-up buy, then reload.** The first model call of the day is slower.

---

## Part A: the 3-minute video

Eleven scenes, 2:56 in all, narration at about 2.4 words a second, said the way you would say it
to a person. The same scenes, with a screenshot for each, are in the video storyboard PDF.

**0:00 to 0:12. Hook**
*Click:* Cold open: in the edit, put 12 seconds of the finished payday (from scene 9) first; No clicks; the map with frozen rings and paid creators sits on screen.
*Say:* "Creators wait weeks to get paid. Buyers pay before they know what they're getting. Helm's AI agents buy, check deliveries and pay creators, inside limits set in code."

**0:12 to 0:26. Buyer: shop and Buy now**
*Click:* Role Buyer, click the Shop tab: every creator's sales and return rate; Click Buy now on a preset pack; Point at the new card in Needs your approval.
*Say:* "Let's start as a buyer. Every item shows its sales and its return rate. I hit Buy now, and PayPal holds my money until the delivery checks out."

**0:26 to 0:44. Ask my agent**
*Click:* Buyer panel: type I need a botanical art print, signed budget 65; Tick a seller hid a hijack in a listing, click Send my buyer agent; Watch the buyer graph (about 10 seconds), then click the red Safety node.
*Say:* "Or I let my agent shop. I give it a sixty-five dollar limit, signed, so it can't spend more. One listing is trying to trick it into ignoring that limit, so Helm pulls that listing before the AI ever sees it."

**0:44 to 1:06. Who confirms delivery**
*Click:* Point at the file names, sizes and SHA-256 on the card; Click the Inspect node: read the verdict; Click Open it, then Accept on one hold and Reject on the other.
*Say:* "So who confirms it arrived? The seller delivers through Helm, so we see every file and its size; here they're simulated. A second AI checks them against the listing, real presets, not an empty zip. Accept, and the payment goes through. Reject, and I'm never charged."

**1:06 to 1:16. Creator: sell and get briefed**
*Click:* Role Creator: under Sell something click List it; Click Brief me.
*Say:* "Now I'm the creator. List it puts my item into PayPal's catalog, and Brief me reads my sales and forecasts next month."

**1:16 to 1:42. Get paid early: less sure, less money**
*Click:* Under Get paid early, leave the amount blank, click Take it; Inspector: point at Could really be (the range); Point at Cut for uncertainty (for example $1,213 to $894).
*Say:* "Get paid early lends me money against what I've already earned. Helm figures out how likely I am not to pay it back, then plays out my next six months hundreds of ways, using my own sales, to see how sure it is. The less sure, the wider this range, and the less I get. The loan book itself is simulated."

**1:42 to 1:54. A buyer disputes a sale**
*Click:* Click Receive a dispute; Point at the amount taken back and the evidence line.
*Say:* "If a buyer disputes a sale, the money comes back out of my earnings, and Helm pulls the evidence from its receipt log. This dispute is simulated."

**1:54 to 2:06. Operator: find the fraud rings**
*Click:* Role Operator, glance at the Accounts tab's Evidence column; Click Scan the marketplace; point at the two red rings.
*Say:* "Now I'm running the marketplace. One scan links accounts sharing a card, a device or an IP, finds the two fraud rings we planted, and freezes their money."

**2:06 to 2:32. Payday: AI sets amounts, code checks each**
*Click:* Click Run payday (about 16 to 20 seconds); Click the Bear node while it streams; Click the Dispose node when it finishes.
*Say:* "Payday. One AI reads this week's risk alert, another sizes up each creator, a bull and a bear argue about how much to release, and a manager sets the amounts. Then code checks every number: nobody gets more than they're owed, the fund stays covered, no sanctioned names. Only then does PayPal send the payouts."

**2:32 to 2:44. Prove it**
*Click:* Click Prove solvency; Click the Money ledger tab under the graph.
*Say:* "Prove solvency shows the fund can cover everything creators are owed, without showing the balance. And every payment's in this ledger with its PayPal ID."

**2:44 to 2:56. How it is built, and close**
*Click:* Click Trace: model, code and PayPal steps with HTTP codes; Cut to the architecture slide for the last 4 seconds.
*Say:* "Every step's in the trace: what the AI decided, what the code checked, what PayPal's sandbox said. The AI decides who gets paid. Code caps how much."

---

## Part B: the full tour (every feature)

### Control room, https://184-194-177-73.sslip.io/live

- **What is real?** (header): every PayPal and model call is real; the creators' history and the
  customers' wallets are simulated and tagged.
- **KPIs** (header): the safety fund, what is owed to creators, the solvency margin, your earnings,
  the money on hold, the frozen money, suspended accounts and orders. Each one moves live.

**Buyer**

- **Shop:**
  - search, filter by category and price;
  - see each seller's sales and return rate;
  - "paid via PayPal" marks creators who are real sandbox payees;
  - real stores come from Channel3, with images.
- **Buy now:** a PayPal Orders authorization (HTTP 201), and the hold appears in Needs your
  approval.
- **Ask my agent / Send my buyer agent:** the buyer graph runs in the order understand, search,
  safety, select, authorize, settle. Toggle the hijack box to show a quarantine.
- **Delivery:** each hold shows the delivered files and hash (or tracking), the AI inspector's
  verdict (click **Inspect** in the buyer graph for its checks), and an auto-release countdown.
- **Open it / Accept / Reject:** access logged as proof; PayPal capture or void. The money flow
  and the ledger update.

**Creator**

- **My shop:**
  - summary (listings, orders, return rate, owed to you, payable now, PayPal payee);
  - the listings grid, with the price editable in place and Take down;
  - recent sales.
- **Sell something:** a PayPal Catalog product (HTTP 201) plus a live listing.
- **Brief me:** the AI manager's briefing and recommendations from your own sales.
- **Get paid early:** an advance priced from proven earnings and capped by the safety fund. The
  solvency margin drops.
- **A buyer disputes my sale:** a chargeback is clawed back, with evidence from the receipt chain.

**Operator**

- **Accounts:**
  - all 121 accounts ranked by risk, with evidence;
  - search, plus Needs review and Frozen filters;
  - click a row for the record, and Freeze or Clear it.
- **Scan for fraud:** the abuse engine and Kuzu ring linkage. Rings are circled and $740 freezes.
- **Run payday:** the payout graph. The inspector shows each agent's streamed tokens and decision.
- **Prove we can pay everyone:** the zero-knowledge solvency proof.
- **Open the market for a round / market toggle:** the AI customers, with real PayPal payments to
  creators who are payees.

**Views**

- **Live map:** hover for the account card, click to highlight neighbors and open the account in the
  inspector.
- **Agents:** tabs for Buyer, Payday, Customers and Fraud; click a node to inspect it.
- **Money flow.**
- **Trace:** the Langfuse-style tree and waterfall.
- **Money ledger:** AG Grid with one row per dollar movement, sortable and filterable.
- **Inspector and Activity:** everything is clickable and cross-linked.

### Full console, https://184-194-177-73.sslip.io

**Start here row:** Run the agents, Run the buyer, Prove solvency, Run the proof.

**Earn lane**

- **Your creator page:** forecast, recommendations, approvals and tax.
- **Policy compiler:** type a policy in English and show the compiled weights and constraints.
- **Signal reader:** a signal becomes a bounded forecast adjustment.
- **Advance pricing:** the default-risk band from the creator's own history; a thin or volatile file lends less.
- **RL advance-sizer:** the learned policy, against the rules.
- **Tax regime:** 1099-K and DAC7.
- **Invest at live prices:** an Alpaca paper order.
- **Investment club:** four member agents read live prices and news over MCP, pick alone, revise after seeing each other, and code caps each stock at 35% and keeps each person's money out of what they ruled out.

**Spend lane**

- **Spend earnings:** tick "plant a prompt-injection listing" and "tamper".
- **Buyer (multi-agent).**
- **Agent negotiates:** the counteroffers down to the cap.
- **Agent mandate (crypto):** a forged mandate is refused.
- **Agent identity.**
- **Pool together:** the Shapley split.
- **Pay on proof:** tick "cheat" and the hold is voided.
- **x402 micropayment.**

**Platform lane**

- **Your marketplace.**
- **Operator (multi-agent).**
- **Platform P&L:** RAROC and the provision.
- **Agent grounding:** retrieval with sources.
- **Proven safe (Z3):** tick "forge", or remove a guard, to see the counterexample.
- **Zero-knowledge reserves:** set liabilities above the lots and it becomes unprovable.
- **Fraud graph:** multi-hop Cypher.
- **Audit and reconcile:** the receipts against PayPal; the tamper demo breaks the chain on a copy.

### Developer surface (mention in 10 seconds)

- 47 HTTP endpoints, documented in `docs/openapi.json`.
- A Postman collection.
- An APIMatic Python SDK.
- Three MCP servers: payouts, market and trust.
- 314 tests, including Hypothesis property tests and live end-to-end tests, with CI on every push.

---

## Lines that land

- "AI decides who gets paid. Code caps how much."
- "Nothing is paid until the delivery is checked: by an AI, and by me."
- "A listing that tries to give my agent orders is removed before any AI reads it."
- "It proves it can pay every creator without revealing a single balance."
- "Every line on screen says whether it is PayPal, AI, code or simulated."
