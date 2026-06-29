"""Contesto per sospendere il mirror sessione → nave (es. tick motore)."""
from __future__ import annotations

import contextvars
from contextlib import contextmanager

_suppress_sessione_nave_sync = contextvars.ContextVar(
    "suppress_sessione_nave_sync", default=False
)


def sessione_nave_sync_enabled() -> bool:
    return not _suppress_sessione_nave_sync.get()


@contextmanager
def suppress_sessione_nave_sync():
    token = _suppress_sessione_nave_sync.set(True)
    try:
        yield
    finally:
        _suppress_sessione_nave_sync.reset(token)
