"""Live sandbox check: run one week's commission batch through the PayPal executor.

Needs PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET and PAYPAL_ENV=sandbox in the environment.
Run twice to see PayPal refuse the replayed batch.
"""

from datetime import date

from helm.model import Action
from helm.paypal.client import PayPalClient
from helm.paypal.executor import PayPalExecutor
from helm.produce import paymaster
from helm.year import build_year

y = build_year()
emails = {h: f"helm-{h.strip('@')}@personal.example.com" for h in y.affiliates}
ex = PayPalExecutor(y.world, PayPalClient.from_env(), affiliate_emails=emails)
monday = date(2026, 1, 5)
action = Action(payouts=paymaster.batch(y.world.commission_owed, y.affiliates))
for r in ex.execute(monday, action, key=f"live-demo:{monday.isoformat()}"):
    print(r)
