# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from math import isfinite


def finite(value: float, label: str, *, minimum: float = 0, positive: bool = False) -> float:
    """Validate a real scalar and a lower bound for a scientific input or result."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < minimum
        or (positive and value <= 0)
    ):
        qualifier = "positive" if positive else f"at least {minimum}"
        raise ValueError(f"{label} must be a finite number that is {qualifier}.")
    return value


def fraction(value: float, label: str, *, positive: bool = False) -> float:
    """Validate a dimensionless fraction in [0, 1] or (0, 1]."""
    if finite(value, label, positive=positive) > 1:
        raise ValueError(f"{label} must be at most 1.")
    return value
