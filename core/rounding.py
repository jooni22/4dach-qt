from __future__ import annotations

from math import ceil


def ceil_cm(value_cm: float) -> int:
    return max(0, int(ceil(float(value_cm))))
