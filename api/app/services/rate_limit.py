import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class RateLimiter:
    def __init__(self):
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
        self._memory: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def _safe_identifier(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]

    def _redis_hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        assert self._redis is not None
        pipe = self._redis.pipeline(transaction=True)
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = pipe.execute()
        if count == 1 or ttl < 0:
            self._redis.expire(key, window_seconds)
            ttl = window_seconds
        return count <= limit, max(int(ttl), 1)

    def _memory_hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._memory[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                return False, retry_after
            events.append(now)
            return True, window_seconds

    def enforce(self, scope: str, identifier: str, limit: int, window_seconds: int = 60) -> None:
        key = f"food-saver:rate:{scope}:{self._safe_identifier(identifier)}"
        try:
            allowed, retry_after = (
                self._redis_hit(key, limit, window_seconds)
                if self._redis is not None
                else self._memory_hit(key, limit, window_seconds)
            )
        except RedisError as exc:
            if settings.environment == "production":
                raise HTTPException(status_code=503, detail="请求保护服务暂不可用") from exc
            allowed, retry_after = self._memory_hit(key, limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={"Retry-After": str(retry_after)},
            )

    def health_status(self) -> tuple[bool, str]:
        if self._redis is None:
            return not settings.require_redis, "disabled"
        try:
            available = bool(self._redis.ping())
        except RedisError:
            return False, "unavailable"
        return available, "ok" if available else "unavailable"


limiter = RateLimiter()


def _client_identifier(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def login_rate_limit(request: Request) -> None:
    limiter.enforce("login", _client_identifier(request), settings.login_rate_limit)


def ai_rate_limit(request: Request) -> None:
    authorization = request.headers.get("Authorization", "")
    identifier = authorization or _client_identifier(request)
    limiter.enforce("ai", identifier, settings.ai_rate_limit)
