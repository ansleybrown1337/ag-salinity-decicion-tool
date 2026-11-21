# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from models.validation import finite


def relative_yield(ece: float, threshold: float, slope: float) -> float:
    """Return relative production (%) from representative root-zone ECe (dS/m).

    Threshold is in dS/m and slope in percentage points per dS/m. The plateau
    and linear decline represent salinity alone (Maas & Hoffman, 1977; FAO 61,
    Annex 1). The extrapolated response is bounded at zero.
    """
    finite(ece, "Soil ECe")
    finite(threshold, "Crop threshold")
    finite(slope, "Yield-loss slope", positive=True)
    return max(0.0, 100 - slope * max(0, ece - threshold))


def target_ece(yield_pct: float, threshold: float, slope: float) -> float:
    """Return maximum ECe (dS/m) at a desired production level in (0, 100]%.

    Uses the inverse of Maas & Hoffman (1977) with threshold in dS/m and slope
    in percentage points per dS/m. At 100% choose the plateau boundary. Zero
    production has no unique maximum ECe in the bounded model.
    """
    finite(yield_pct, "Target relative yield", positive=True)
    finite(threshold, "Crop threshold")
    finite(slope, "Yield-loss slope", positive=True)
    if yield_pct > 100:
        raise ValueError("Target relative yield must be at most 100%.")
    return finite(threshold + (100 - yield_pct) / slope, "Derived target ECe")
