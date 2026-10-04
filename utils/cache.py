"""
Two-tier cache: in-memory TTL cache (fast, per-process) backed by an optional
on-disk JSON cache (survives restarts). Keys are derived from the function
name + arguments, so services can decorate any async fetch function.

This intentionally avoids Redis/SQLite as hard dependencies (per the spec,
those are optional) - the on-disk layer is just flat JSON files, which is
enough for a portfolio-grade project and trivial to swap out later.
"""
from __future__ import annotations

import functools
import hashlib
import json
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, TypeVar

from cachetools import TTLCache

from config import log, settings

T = TypeVar("T")

# In-memory cache: up to 2048 entries, fallback TTL if a call site doesn't specify one.
_memory_cache: TTLCache = TTLCache(maxsize=2048, ttl=settings.ttl_default_seconds)


def _make_key(namespace: str, args: tuple, kwargs: dict) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"{namespace}:{digest}"


# If we ever fail to create/write the cache directory (e.g. permission
# denied), stop trying for the rest of the process instead of raising on
# every single tool call - the in-memory cache still works fine on its own.
_disk_cache_disabled = False


def _disk_path(key: str) -> Path | None:
    global _disk_cache_disabled
    if _disk_cache_disabled:
        return None
    try:
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning(
            "Disk cache directory %s is not writable (%s) - disabling disk cache for this run, "
            "falling back to in-memory cache only. Set CACHE_DIR in .env to a writable path to fix this.",
            settings.cache_dir,
            exc,
        )
        _disk_cache_disabled = True
        return None
    return settings.cache_dir / f"{key}.json"


def _disk_read(key: str, ttl_seconds: int) -> Any | None:
    path = _disk_path(key)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except OSError as exc:
        log.warning("Failed to read disk cache %s: %s", key, exc)
        return None
    except json.JSONDecodeError:
        return None
    if time.time() - payload.get("_cached_at", 0) > ttl_seconds:
        return None
    return payload.get("value")


def _disk_write(key: str, value: Any) -> None:
    path = _disk_path(key)
    if path is None:
        return
    try:
        path.write_text(json.dumps({"_cached_at": time.time(), "value": value}, default=str))
    except OSError as exc:  # non-fatal: cache is best-effort
        log.warning("Failed to write disk cache %s: %s", key, exc)


def async_cached(namespace: str, ttl_seconds: int, disk: bool = True):
    """
    Decorator for async functions that fetch data from external APIs.

    Usage:
        @async_cached("uniprot.entry", ttl_seconds=settings.ttl_uniprot_seconds)
        async def get_entry(accession: str) -> dict: ...
    """

    def decorator(fn: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            key = _make_key(namespace, args, kwargs)

            if key in _memory_cache:
                log.debug("cache hit (memory) %s", key)
                return _memory_cache[key]

            if disk:
                disk_value = _disk_read(key, ttl_seconds)
                if disk_value is not None:
                    log.debug("cache hit (disk) %s", key)
                    _memory_cache[key] = disk_value
                    return disk_value  # type: ignore[return-value]

            log.debug("cache miss %s -> calling %s", key, fn.__name__)
            result = await fn(*args, **kwargs)

            _memory_cache[key] = result
            if disk:
                _disk_write(key, result)
            return result

        return wrapper

    return decorator
