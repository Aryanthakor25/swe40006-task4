"""Storage for study sessions.

RedisStore is used when REDIS_HOST is set (compose setup). MemoryStore is a
fallback so the container still starts with a plain `docker run`, but the
data is lost on restart.
"""
import json
import logging
import threading
from typing import Protocol

log = logging.getLogger("studypulse.store")

SESSIONS_KEY = "studypulse:sessions"
VISITS_KEY = "studypulse:visits"


class Store(Protocol):
    backend: str

    def add_session(self, session: dict) -> None: ...
    def list_sessions(self, limit: int = 50) -> list[dict]: ...
    def incr_visits(self) -> int: ...
    def ping(self) -> bool: ...


class MemoryStore:
    backend = "memory"

    def __init__(self) -> None:
        self._sessions: list[dict] = []
        self._visits = 0
        self._lock = threading.Lock()

    def add_session(self, session: dict) -> None:
        with self._lock:
            self._sessions.insert(0, session)

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._sessions[:limit])

    def incr_visits(self) -> int:
        with self._lock:
            self._visits += 1
            return self._visits

    def ping(self) -> bool:
        return True


class RedisStore:
    backend = "redis"

    def __init__(self, client) -> None:
        self.r = client

    def add_session(self, session: dict) -> None:
        self.r.lpush(SESSIONS_KEY, json.dumps(session))
        self.r.ltrim(SESSIONS_KEY, 0, 999)  # keep the newest 1000 only

    def list_sessions(self, limit: int = 50) -> list[dict]:
        return [json.loads(item) for item in self.r.lrange(SESSIONS_KEY, 0, limit - 1)]

    def incr_visits(self) -> int:
        return int(self.r.incr(VISITS_KEY))

    def ping(self) -> bool:
        try:
            return bool(self.r.ping())
        except Exception:  # connection refused, timeout, DNS failure etc.
            return False


def build_store(settings) -> Store:
    if not settings.redis_host:
        log.warning("REDIS_HOST not set, using in-memory store (data is not persisted)")
        return MemoryStore()

    import redis

    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    log.info("Using Redis store at %s:%s", settings.redis_host, settings.redis_port)
    return RedisStore(client)
