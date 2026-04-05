"""Thread-safe in-memory TTL cache."""
import time
import threading


class TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self.ttl = ttl_seconds
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        """Return fresh value, or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if (time.time() - ts) >= self.ttl:
            return None
        return value

    def get_stale(self, key):
        """Return value even if expired (for graceful degradation)."""
        with self._lock:
            entry = self._store.get(key)
        return entry[1] if entry else None

    def set(self, key, value):
        with self._lock:
            self._store[key] = (time.time(), value)

    def has_fresh(self, key) -> bool:
        return self.get(key) is not None
