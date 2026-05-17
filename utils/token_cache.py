from __future__ import annotations

import hashlib
import time
from collections import OrderedDict

_MAX_ENTRIES = 5000
_TTL_SEC = 24 * 3600

_cache: "OrderedDict[str, tuple[str, str, float]]" = OrderedDict()


def _make_key(chain: str, address: str) -> str:
    h = hashlib.blake2b(f"{chain}:{address}".encode(), digest_size=6).hexdigest()
    return h


def put(chain: str, address: str) -> str:
    key = _make_key(chain, address)
    now = time.time()
    _cache[key] = (chain, address, now)
    _cache.move_to_end(key)
    while len(_cache) > _MAX_ENTRIES:
        _cache.popitem(last=False)
    return key


def get(key: str) -> tuple[str, str] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    chain, address, ts = entry
    if time.time() - ts > _TTL_SEC:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return chain, address
