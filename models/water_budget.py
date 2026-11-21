# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
from math import fsum

from models.crop_response import relative_yield
from models.irrigation import IrrigationDepths, acre_feet, irrigation_depths, net_crop_depth
from models.leaching import leaching_requirement
from schemas.farm import FieldPlan, Scenario, WaterSource


@dataclass(frozen=True)
class FieldResult:
    field: FieldPlan
    source: WaterSource
    current_yield_pct: float
    yield_at_target_pct: float
    net_crop_af: float
    lr: float | None
    depths: IrrigationDepths | None
    field_af: float | None
    all_credit_field_af: float | None
    zero_credit_field_af: float | None
    warnings: tuple[str, ...]

    @property
    def crop_only_af(self):
        return acre_feet(self.depths.crop_only_gross_in, self.field.acres) if self.depths else None

    @property
    def added_leach_field_af(self):
        return acre_feet(self.depths.additional_gross_in, self.field.acres) if self.depths else None


@dataclass(frozen=True)
class SourceResult:
    source: WaterSource
    demand_af: float | None
    known_demand_af: float

    @property
    def balance_af(self):
        return self.source.delivery_af - self.demand_af if self.demand_af is not None else None

    @property
    def shortfall_af(self):
        return max(0.0, self.known_demand_af - self.source.delivery_af)

    @property
    def assessment(self):
        if self.shortfall_af > 1e-8:
            return "Shortfall" if self.demand_af is not None else "Known demand exceeds delivery"
        return "Within delivery" if self.demand_af is not None else "Undetermined"


@dataclass(frozen=True)
class FarmResult:
    fields: tuple[FieldResult, ...]
    sources: tuple[SourceResult, ...]

    @property
    def acres(self):
        return fsum(row.field.acres for row in self.fields)

    @property
    def net_crop_af(self):
        return fsum(row.net_crop_af for row in self.fields)

    @property
    def field_supply_af(self):
        return fsum(row.source.delivery_af for row in self.sources)

    def complete_sum(self, attribute: str) -> float | None:
        """Aggregate a field result in shared units only when all fields have a value."""
        values = [getattr(row, attribute) for row in self.fields]
        return fsum(values) if None not in values else None

    @property
    def field_demand_af(self):
        return self.complete_sum("field_af")

    @property
    def field_balance_af(self):
        demand = self.field_demand_af
        return self.field_supply_af - demand if demand is not None else None

    @property
    def source_shortfall_af(self):
        return fsum(row.shortfall_af for row in self.sources)

    @property
    def allocation_conclusion(self):
        if self.source_shortfall_af > 1e-8:
            return "At least one water source falls short of assigned demand."
        if self.field_demand_af is None:
            return "Water sufficiency is undetermined because at least one field has no feasible estimate."
        return "Expected farm deliveries cover estimated demand at each assigned source."

    @property
    def salinity_concerns(self):
        return sum(bool(row.warnings) for row in self.fields)


def evaluate_field(field: FieldPlan, source: WaterSource) -> FieldResult:
    """Calculate production response, annual depths (in), and volumes (AF).

    Inputs are a validated field and its assigned source. Uses Maas & Hoffman
    (1977), FAO 29 section 2.4 and the budget assumptions in models.irrigation.
    Infeasible leaching remains explicit while crop deficit and response remain
    available. Gross irrigation volume describes water applied to the field.
    """
    if field.source_id != source.id:
        raise ValueError("Water source does not match the field assignment.")
    crop = field.crop
    target = field.target_ece_ds_m
    current_yield = relative_yield(field.current_ece_ds_m, crop.threshold_ds_m, crop.slope_pct_per_ds_m)
    target_yield = relative_yield(target, crop.threshold_ds_m, crop.slope_pct_per_ds_m)
    warnings = []
    if crop.id == "corn_grain" and "Published default" in (crop.threshold_origin, crop.slope_origin):
        warnings.append("The grain-corn salinity coefficients come from a single cultivar on organic muck soil "
                        "(FAO 61, Annex 1). Review their applicability locally.")
    if field.current_ece_ds_m > target:
        warnings.append("Current ECe exceeds the target. Maintenance leaching does not estimate reclamation.")
    if current_yield < field.desired_yield_pct - 1e-9:
        warnings.append("Estimated production at current ECe is below the desired relative yield.")
    if target_yield < field.desired_yield_pct - 1e-9:
        warnings.append("The manual ECe target implies a lower relative yield than the desired yield.")
    if field.irrigation.id == "drip":
        warnings.append("The FAO equation is a screening approximation for drip wetting patterns.")
    net = net_crop_depth(field.etc_in, field.effective_rain_in)
    net_af = acre_feet(net, field.acres)
    lr = None
    try:
        lr = leaching_requirement(source.ecw_ds_m, target)
        if lr > 0.25:
            warnings.append("The theoretical leaching requirement exceeds 25%. Confirm drainage and consider a "
                            "more salt-tolerant crop or a lower-ECw source (FAO 29, section 2.4).")
        efficiency = field.irrigation.efficiency_pct / 100
        depths = irrigation_depths(net, efficiency, lr, field.leaching_credit_pct / 100)
        field_af = acre_feet(depths.gross_in, field.acres)
        lower = acre_feet(irrigation_depths(net, efficiency, lr, 1).gross_in, field.acres)
        upper = acre_feet(irrigation_depths(net, efficiency, lr, 0).gross_in, field.acres)
        if net == 0:
            warnings.append("Crop deficit is zero. The budget does not estimate rain-driven leaching.")
    except ValueError as error:
        warnings.append(str(error))
        depths = field_af = lower = upper = None
    return FieldResult(
        field, source, current_yield, target_yield, net_af, lr, depths,
        field_af, lower, upper, tuple(warnings),
    )


def evaluate_scenario(scenario: Scenario) -> FarmResult:
    """Aggregate field demand in AF and compare it with expected farm deliveries.

    Uses FAO 29 maintenance estimates via evaluate_field and simple volume
    accounting. A supply surplus at one source cannot offset another source's
    deficit. Supply is already net of losses upstream of the farm.
    """
    sources = {source.id: source for source in scenario.sources}
    fields = tuple(evaluate_field(field, sources[field.source_id]) for field in scenario.fields)
    assigned = {source_id: [] for source_id in sources}
    for result in fields:
        assigned[result.source.id].append(result.field_af)
    source_results = []
    for source_id, volumes in assigned.items():
        subtotal = fsum(volume for volume in volumes if volume is not None)
        source_results.append(SourceResult(sources[source_id], None if None in volumes else subtotal, subtotal))
    return FarmResult(fields, tuple(source_results))
