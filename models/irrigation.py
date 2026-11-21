# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass

from models.validation import finite, fraction


@dataclass(frozen=True)
class IrrigationDepths:
    net_crop_in: float
    crop_only_gross_in: float
    credited_existing_in: float
    theoretical_leach_in: float
    additional_gross_in: float
    gross_in: float
    effective_drainage_in: float
    nonbeneficial_loss_in: float


def net_crop_depth(etc_in: float, rain_in: float) -> float:
    """Return seasonal crop deficit (inches) from ETc and effective rain in inches.

    FAO 56 water balance concept with zero net change in storage and no capillary
    rise. Effective rain meets ET only in this budget.
    """
    finite(etc_in, "Seasonal crop ET")
    finite(rain_in, "Effective precipitation")
    return max(0.0, etc_in - rain_in)


def irrigation_depths(net_in: float, efficiency: float, lr: float, credit: float) -> IrrigationDepths:
    """Return annual field depths (inches) for crop water and maintenance leaching.

    Efficiency, LR and credit are fractions. Crop-only efficiency converts net
    crop demand to baseline gross depth. Credit is the assumed share of baseline
    inefficiency that mixes and drains through the root zone. Gross water beyond
    baseline retains the same fraction of nonbeneficial losses. This planning
    mass balance adapts FAO 29 section 2.4 and FAO 61 Annex 4; the loss partition
    is a user assumption informed by site evidence, independent of OSU presets.
    """
    finite(net_in, "Net crop depth")
    fraction(efficiency, "Application efficiency", positive=True)
    fraction(lr, "Leaching requirement")
    fraction(credit, "Effective leaching credit")
    if lr == 1:
        raise ValueError("Leaching requirement must be less than 100%.")
    baseline = finite(net_in / efficiency, "Crop-only depth")
    existing = credit * (baseline - net_in)
    mixing_fraction = efficiency + credit * (1 - efficiency)
    infiltrated = finite(net_in / (1 - lr), "Required mixing water depth")
    gross = finite(max(baseline, infiltrated / mixing_fraction), "Gross irrigation depth")
    extra = gross - baseline
    drainage = existing + extra * mixing_fraction
    losses = (baseline - net_in - existing) + extra * (1 - mixing_fraction)
    return IrrigationDepths(net_in, baseline, existing, infiltrated * lr, extra, gross, drainage, losses)


def acre_feet(depth_in: float, area_ac: float) -> float:
    """Convert uniform nonnegative irrigation depth (in) over positive acres to AF."""
    finite(depth_in, "Irrigation depth")
    finite(area_ac, "Field acreage", positive=True)
    return finite((depth_in / 12) * area_ac, "Water volume")


