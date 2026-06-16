"""Normalized envelopes for /ui mutation endpoints."""


def admin_mutation(action: str, entity_id: str, **extra) -> dict:
    """Return a consistent write-response shape: ok, action, id, plus optional fields."""
    body: dict = {"ok": True, "action": action, "id": str(entity_id)}
    body.update(extra)
    return body
