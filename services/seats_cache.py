import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

CACHE_TTL_SECONDS = 30


@dataclass
class _Entry:
    seats: list[str]
    expires_at: float


class SeatsCache:
    def __init__(self, ttl: int = CACHE_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._store: dict[str, _Entry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    async def _lock_for(self, key: str) -> asyncio.Lock:
        async with self._meta_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    async def get_or_fetch(
        self,
        key: str,
        fetch: Callable[[], Awaitable[list[str]]],
    ) -> list[str]:
        now = time.monotonic()
        entry = self._store.get(key)
        if entry and entry.expires_at > now:
            return entry.seats

        async with await self._lock_for(key):
            entry = self._store.get(key)
            now = time.monotonic()
            if entry and entry.expires_at > now:
                return entry.seats

            seats = await fetch()
            self._store[key] = _Entry(seats=seats, expires_at=now + self._ttl)
            return seats

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


seats_cache = SeatsCache()
