"""Live dashboard server: `uvicorn ui.app:app`, then open the URL.

Serves the single control-journal screen at / and the same data at /api/data.
The payload is a full system run (controller loop + 120-scenario evaluation,
about five seconds), so it is computed once at startup and cached: every page
load after that is instant. The page ships with its data embedded, so it renders
even if the data endpoint is never called. /healthz is a cheap liveness probe
for the host's health check.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
except Exception as exc:  # pragma: no cover
    raise SystemExit("FastAPI not installed; run: pip install fastapi uvicorn") from exc

from .data import dashboard_data_cached
from .page import render_page


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    # Warm the cache before the first request so no visitor pays the build cost.
    dashboard_data_cached()
    yield


app = FastAPI(title="Helm", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    # Data is embedded in the page, so it renders with no second round trip.
    return HTMLResponse(render_page(embedded_data=dashboard_data_cached()))


@app.get("/api/data", response_class=JSONResponse)
def data() -> JSONResponse:
    return JSONResponse(dashboard_data_cached())


@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")
