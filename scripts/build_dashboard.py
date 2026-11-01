"""Write a self-contained dashboard.html with the data embedded, so it opens in
a browser with no server. Run: python scripts/build_dashboard.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.data import build_dashboard_data  # noqa: E402
from ui.page import render_page  # noqa: E402


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "dashboard.html")
    html = render_page(embedded_data=build_dashboard_data())
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out} ({len(html):,} bytes) -- open it in a browser (needs internet for the chart CDN)")


if __name__ == "__main__":
    main()
