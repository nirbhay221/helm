"""The creator-marketplace domain: the world Helm actually controls.

A platform takes money from buyers (via PayPal Orders), owes creators their
earnings (paid via PayPal Payouts), and must hold a rolling reserve against
refunds and chargebacks while keeping cash above a floor. The tension this
package models is the real one: pay creators fast (87% of creators report being
paid late) without ever breaching cash or under-reserving against clawbacks.
"""
from .sim import CreatorMarketplace, MarketplaceParams, MarketObservation
from .controller import CashPayoutController, CashPayoutParams
from .policies import (pay_all_now_policy, pay_monthly_policy, helm_payout_policy,
                       run_marketplace, MarketplaceMetrics)

__all__ = [
    "CreatorMarketplace", "MarketplaceParams", "MarketObservation",
    "CashPayoutController", "CashPayoutParams",
    "pay_all_now_policy", "pay_monthly_policy", "helm_payout_policy",
    "run_marketplace", "MarketplaceMetrics",
]
