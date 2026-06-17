import time
from collections import OrderedDict
from typing import Any, Optional


class InMemorySignalCache:
    def __init__(self):
        self.cache = OrderedDict()
        self.max_size = 1000

    def make_key(
        self,
        tenant_id: str,
        checkpoint_id: Optional[str],
        applicant_id: Optional[str],
        signal_id: str,
        cache_scope: str,
    ):
        if cache_scope == "tenant_signal":
            return ("tenant_signal", tenant_id, signal_id)
        if cache_scope == "tenant_applicant_signal":
            return ("tenant_applicant", tenant_id, applicant_id or "", signal_id)
        if cache_scope == "tenant_case_signal":
            return ("tenant_case", tenant_id, applicant_id or "", signal_id)
        # tenant_checkpoint_applicant (legacy default)
        return ("checkpoint", tenant_id, checkpoint_id or "", applicant_id or "", signal_id)

    def get(
        self,
        tenant_id: str,
        checkpoint_id: Optional[str],
        applicant_id: Optional[str],
        signal_id: str,
        cache_scope: str = "tenant_checkpoint_applicant",
    ):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id, cache_scope)
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
        checkpoint_id: Optional[str],
        applicant_id: Optional[str],
        signal_id: str,
        value: Any,
        ttl: int,
        cache_scope: str = "tenant_checkpoint_applicant",
    ):
        key = self.make_key(tenant_id, checkpoint_id, applicant_id, signal_id, cache_scope)
        expires_ts = time.time() + ttl
        self.cache[key] = (value, expires_ts)
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)


in_memory_signal_cache = InMemorySignalCache()
