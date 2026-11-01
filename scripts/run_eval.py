"""Run Helm's controller against a strong base-stock baseline across many
randomized scenarios, and print an honest win/loss report.

The deviation result is flagged as partly circular (the controller optimizes
deviation). The findings that matter are the ones Helm does NOT directly
optimize: service (fill rate), capital tied up in inventory, order cost, and
how often cash fell below the floor.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation import evaluate  # noqa: E402


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    s = evaluate(n=n, seed=0)

    print(f"scenarios: {s['n_scenarios']} (randomized demand, noise, lead time, "
          f"margin, starting cash, cash floor, shocks)\n")

    print("[partly circular] inventory deviation is the controller's own objective:")
    print(f"  Helm {s['helm_mean_deviation']} vs base-stock {s['base_stock_mean_deviation']} "
          f"(strawman {s['constant_mean_deviation']}); Helm wins "
          f"{s['helm_deviation_win_rate']*100:.1f}% -- expected, so not the real test.\n")

    print("[the real tests -- metrics Helm does NOT optimize]")
    print(f"  service (fill rate):  Helm {s['helm_mean_fill']} vs base-stock "
          f"{s['base_stock_mean_fill']}")
    print(f"    base-stock matches-or-beats Helm on service in "
          f"{s['base_fill_not_worse_rate']*100:.1f}% of scenarios")
    print(f"  stockout periods:     Helm {s['helm_mean_stockout_periods']} vs base-stock "
          f"{s['base_stock_mean_stockout_periods']}")
    print(f"  capital held (avg inventory): Helm {s['helm_mean_avg_inventory']} vs base-stock "
          f"{s['base_stock_mean_avg_inventory']}")
    print(f"  order cost (mean):    Helm {s['helm_mean_order_cost']} vs base-stock "
          f"{s['base_stock_mean_order_cost']}")
    print(f"  cash-floor breaches (total): Helm {s['helm_total_cash_breaches']} vs base-stock "
          f"{s['base_stock_total_cash_breaches']}\n")

    print("[does the verifier's hard cash floor actually help?]")
    print(f"  cash-floor breaches: raw Helm {s['helm_total_cash_breaches']} -> "
          f"verifier-gated Helm {s['helm_verified_total_cash_breaches']} "
          f"(base-stock {s['base_stock_total_cash_breaches']})")
    print(f"  cost of the guard: fill {s['helm_mean_fill']} -> "
          f"{s['helm_verified_mean_fill']}, stockout periods "
          f"{s['helm_mean_stockout_periods']} -> {s['helm_verified_mean_stockout_periods']}\n")

    print(f"Helm loses on deviation in {s['n_losses_vs_base']} scenarios.")
    for L in s["worst_losses"]:
        print(f"  {L['scenario']}: helm_dev={L['helm_dev']} vs base_dev={L['base_dev']}")


if __name__ == "__main__":
    main()
