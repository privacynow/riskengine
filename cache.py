import time
from collections import OrderedDict
from typing import Any, Optional


class InMemorySignalCache:
    def __init__(self):
        self.cache = OrderedDict()
        self.max_size = 1000

    def make_key(
        self, tenant_id: str, checkpoint_id: str, applicant_id: Optional[str], signal_id: str
    ):
        return (tenant_id, checkpoint_id, applicant_id or "", signal_id)

    def get(
        self, tenant_id: str, checkpoint_id: str, applicant_id: Optional[str], signal_id: str
    ):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id)
        if key not in self.cache:
            return None
        value, expires_ts = self.cache[key]
        if time.time() > expires_ts:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def set(
        self,
        tenant_id: str,
        checkpoint_id: str,
        applicant_id: Optional[str],
        signal_id: str,
        value: Any,
        ttl: int,
    ):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id)
        expires_ts = time.time() + ttl
        self.cache[key] = (value, expires_ts)
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)


in_memory_signal_cache = InMemorySignalCache()
