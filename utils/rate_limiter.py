import asyncio
import time


class RateLimiter:
    def __init__(self, calls_per_second: float = 1.0):
        self._interval = 1.0 / calls_per_second
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
