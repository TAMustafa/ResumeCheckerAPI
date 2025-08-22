from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any, Callable, Optional, Awaitable


class TTLCache:
    """
    Simple in-memory TTL cache with an LRU eviction policy.
    - thread/async safe via a single asyncio.Lock
    - no external storage
    """

    def __init__(self, maxsize: int = 256, ttl_seconds: int = 900):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _is_expired(self, ts: float) -> bool:
        return (time.time() - ts) > self.ttl

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            ts, value = item
            if self._is_expired(ts):
                # expired
                self._store.pop(key, None)
                return None
            # touch for LRU
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.time(), value)
            # evict
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)

    async def get_or_set(self, key: str, compute: Callable[[], Awaitable[Any]]) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await compute()
        await self.set(key, value)
        return value


# Default shared cache instance for the app process
shared_cache = TTLCache(maxsize=512, ttl_seconds=20 * 60)
