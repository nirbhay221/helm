"""The marketplace: personas who buy and sell, and the trust engine over them.

A two-sided creator marketplace. Accounts have a persona (they sell listings and
buy from others), money moves on PayPal (buyers pay via Orders, sellers are paid
via Payouts), and returns and chargebacks happen. The abuse engine watches both
sides, attributes fault when returns cluster, and suspends the party actually
responsible, with a recorded reason.
"""
from .marketplace import Account, Listing, Order, Marketplace
from .abuse import AbuseEngine, AbuseVerdict
from .linkage import LinkageEngine, Ring

__all__ = ["Account", "Listing", "Order", "Marketplace", "AbuseEngine", "AbuseVerdict",
           "LinkageEngine", "Ring"]
