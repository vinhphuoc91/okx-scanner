"""Python version compatibility shims (3.10+)."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from datetime import UTC
    from enum import StrEnum
else:
    from datetime import timezone
    from enum import Enum

    UTC = timezone.utc

    class StrEnum(str, Enum):
        pass

__all__ = ["StrEnum", "UTC"]
