"""Run one Helm MCP server by domain: payouts (default), market, or trust.

    python -m mcp_server            # payouts (money-out + ops)
    python -m mcp_server market     # live quotes + investing
    python -m mcp_server trust      # abuse + fraud-ring scans

Each is its own bounded context with a handful of namespaced tools, the split the
2026 MCP guidance recommends over one monolith.
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass

    which = (sys.argv[1] if len(sys.argv) > 1 else "payouts").lower()
    if which == "market":
        from .market_server import build_market_server as build
    elif which == "trust":
        from .trust_server import build_trust_server as build
    else:
        from .server import build_server as build
    build().run(transport="stdio")


if __name__ == "__main__":
    main()
