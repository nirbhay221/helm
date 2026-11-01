"""The Payout Engine: turn a payout target into correct, un-gameable, legal,
tax-handled, atomically-executed disbursements. Five sub-parts run in sequence
on the same pot: Mete -> Bulwark -> Clearwright -> Tollgate -> Keystone."""
from .mete import Contribution, MeteResult, shapley_split
from .bulwark import BulwarkResult, Party, harden_split
from .clearwright import ClearwrightResult, MoneyEdge, check_plan
from .tollgate import TollgateResult, withhold
from .keystone import KeystoneResult, execute_batch
from .pipeline import PayoutEngineResult, run_payout_engine

__all__ = [
    "Contribution", "MeteResult", "shapley_split",
    "Party", "BulwarkResult", "harden_split",
    "MoneyEdge", "ClearwrightResult", "check_plan",
    "TollgateResult", "withhold",
    "KeystoneResult", "execute_batch",
    "PayoutEngineResult", "run_payout_engine",
]
