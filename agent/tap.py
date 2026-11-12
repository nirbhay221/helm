"""Live event tap: lets the UI watch a graph run as it happens.

A run started by the live view attaches a sink; every agent node, model call, model token, PayPal
call and guardrail then emits small events into it. With no sink attached (normal API calls,
tests) every emit is a no-op, so nothing changes for the rest of the system.
"""
from __future__ import annotations

import contextvars
import time
from typing import Callable, Optional

_SINK: contextvars.ContextVar[Optional[Callable[[dict], None]]] = contextvars.ContextVar("helm_tap", default=None)
_NODE: contextvars.ContextVar[str] = contextvars.ContextVar("helm_tap_node", default="")
_T0: contextvars.ContextVar[float] = contextvars.ContextVar("helm_tap_t0", default=0.0)


def attach(sink: Callable[[dict], None]):
    return _SINK.set(sink), _T0.set(time.time())


def detach(tokens) -> None:
    s, t = tokens
    _SINK.reset(s)
    _T0.reset(t)


def active() -> bool:
    return _SINK.get() is not None


def current_node() -> str:
    return _NODE.get()


def emit(kind: str, **data) -> None:
    sink = _SINK.get()
    if sink is None:
        return
    ev = {"kind": kind, "t": round(time.time() - _T0.get(), 3), "node": data.pop("node", None) or _NODE.get()}
    ev.update(data)
    try:
        sink(ev)
    except Exception:
        pass


class node:
    """Tag everything emitted inside the block (model tokens included) with this node name."""
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self._tok = _NODE.set(self.name)
        return self

    def __exit__(self, *exc):
        _NODE.reset(self._tok)
        return False


def traced(graph: str, name: str, fn, summarize: Optional[Callable[[str, dict], dict]] = None):
    """Wrap a LangGraph node so the live view sees it start, finish, how long it took, which model
    answered and what it decided."""
    def run(state):
        if _SINK.get() is None:
            return fn(state)
        tok = _NODE.set(name)
        t = time.time()
        emit("node_start", graph=graph)
        try:
            out = fn(state)
        except Exception as exc:
            emit("node_error", graph=graph, error=f"{type(exc).__name__}: {str(exc)[:200]}")
            raise
        finally:
            _NODE.reset(tok)
        st = out if isinstance(out, dict) else state
        rec = (st.get("nodes") or {}).get(name) or {}
        summary = {}
        if summarize:
            try:
                summary = summarize(name, st) or {}
            except Exception as exc:
                summary = {"note": f"summary unavailable: {exc}"}
        emit("node_end", node=name, graph=graph, ms=int((time.time() - t) * 1000),
             driver=rec.get("driver"), model=rec.get("model"), error=rec.get("error"), **summary)
        return out
    run.__name__ = getattr(fn, "__name__", name)
    return run
