"""Bounded single-worker demo safeguards; edge rate limits are still required."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from fastapi import Request
from starlette.responses import JSONResponse

_buckets = OrderedDict()
_lock = Lock()


async def limit_auth_requests(request: Request, call_next):
    if request.method == 'POST' and request.url.path in {'/auth/login', '/auth/register'}:
        peer = request.client.host if request.client else 'unknown'
        now = monotonic()
        with _lock:
            bucket = _buckets.setdefault(peer, deque())
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= 120:
                return JSONResponse({'detail': 'Too many authentication attempts'}, 429,
                                    headers={'Retry-After': '60'})
            bucket.append(now)
            _buckets.move_to_end(peer)
            while len(_buckets) > 4096:
                _buckets.popitem(last=False)
    return await call_next(request)
