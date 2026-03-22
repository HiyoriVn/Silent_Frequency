"""
Silent Frequency — Lightweight Metrics Helper

Minimal in-process counter helper for operational visibility.
Designed as a stub so real metrics backends can be integrated later.
"""

from __future__ import annotations

import logging
from threading import Lock

logger = logging.getLogger(__name__)

_COUNTERS: dict[str, int] = {}
_LOCK = Lock()


def increment(name: str, value: int = 1) -> None:
    if value <= 0:
        return

    with _LOCK:
        _COUNTERS[name] = _COUNTERS.get(name, 0) + value
        current = _COUNTERS[name]

    logger.info("metric.increment name=%s value=%d total=%d", name, value, current)


def get_counter(name: str) -> int:
    with _LOCK:
        return _COUNTERS.get(name, 0)


def reset_counters() -> None:
    with _LOCK:
        _COUNTERS.clear()


def snapshot() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)
