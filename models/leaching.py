# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from models.validation import finite


def leaching_requirement(ecw: float, target_ece: float) -> float:
    """Return theoretical maintenance LR as a fraction of infiltrated irrigation.

    ECw and target mean root-zone ECe are in dS/m. Uses FAO Paper 29 Rev. 1
    equation (9) and FAO Paper 61 Annex 4. Assumes approximate steady state,
    ordinary surface irrigation, effective mixing and adequate drainage.
    Infeasible targets raise ValueError. Zero ECw gives zero LR for positive ECe.
    """
    finite(ecw, "Irrigation water ECw")
    finite(target_ece, "Target soil ECe", positive=True)
    # Normalize by target first to avoid overflow in 5 * target.
    ratio = ecw / target_ece
    if ratio >= 5:
        raise ValueError("Target ECe is too low for this ECw: the LR denominator is zero or negative.")
    if ratio >= 2.5:
        raise ValueError("Target ECe is too low for this ECw: required leaching is at least 100%.")
    return ratio / (5 - ratio)
