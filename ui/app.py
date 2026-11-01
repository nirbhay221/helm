"""Live dashboard server: `uvicorn ui.app:app --reload`, then open the URL.

Serves the single control-journal screen at / and the data at /api/data, so the
charts refresh from the running system on each load.
"""
from __future__ import annotations

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
except Exception as exc:  # pragma: no cover
    raise SystemExit("FastAPI not installed; run: pip install fastapi uvicorn") from exc

from .data import build_dashboard_data
from .page import render_page

app = FastAPI(title="Helm")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(render_page())


@app.get("/api/data", response_class=JSONResponse)
def data() -> JSONResponse:
    return JSONResponse(build_dashboard_data())
