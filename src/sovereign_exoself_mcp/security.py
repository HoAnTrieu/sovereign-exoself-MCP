"""Secret filtering and safe serialization helpers."""

import re

_SECRET = re.compile(
    r"(?i)(?:api[_-]?key|password|bearer|token|secret|private[_-]?key)\s*[:=]\s*[^\s,;]+"
)


def redact(value: str) -> str:
    """Redact credential-shaped values from text."""
    return _SECRET.sub("[REDACTED]", value)


def contains_secret(value: str) -> bool:
    """Identify credential-shaped memory candidates."""
    return _SECRET.search(value) is not None


def normalize(value: str) -> str:
    """Normalize content for deterministic fingerprinting."""
    return " ".join(value.lower().split())
