# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from models.crop_response import target_ece
from schemas.farm import Crop, CropEtEstimate, FieldPlan, Scenario


def duplicate_scenario(scenario: Scenario, scenario_id: str, name: str) -> Scenario:
    """Create an independently editable scenario with the same input values."""
    values = scenario.model_dump()
    values.update(id=scenario_id, name=name, number=None)
    return Scenario.model_validate(values)


def field_alternative(
    field: FieldPlan, *, crop: Crop | None = None, etc_in: float,
    et_estimate: CropEtEstimate | None = None, desired_yield_pct: float | None = None,
    efficiency_pct: float | None = None, leaching_credit_pct: float | None = None,
    effective_rain_in: float | None = None, target_ece_ds_m: float | None = None,
) -> FieldPlan:
    """Estimate a field change from validated inputs while retaining its observed conditions."""
    values = field.model_dump()
    crop_changed = crop is not None and crop != field.crop
    goal = field.desired_yield_pct if desired_yield_pct is None else desired_yield_pct
    values.update(etc_in=etc_in, desired_yield_pct=goal)
    if effective_rain_in is not None:
        values["effective_rain_in"] = effective_rain_in
    if crop_changed:
        values.update(crop=crop.model_dump(), et_estimate=et_estimate)
    if target_ece_ds_m is not None:
        values.update(target_ece_override=True, target_ece_ds_m=target_ece_ds_m)
    elif crop_changed or goal != field.desired_yield_pct:
        selected_crop = crop if crop_changed else field.crop
        values.update(
            target_ece_override=False,
            target_ece_ds_m=target_ece(goal, selected_crop.threshold_ds_m, selected_crop.slope_pct_per_ds_m),
        )
    if leaching_credit_pct is not None:
        values["leaching_credit_pct"] = leaching_credit_pct
    if efficiency_pct is not None and efficiency_pct != field.irrigation.efficiency_pct:
        method = values["irrigation"]
        bounds = field.irrigation.published_range_pct
        if field.irrigation.id == "custom":
            origin = "Custom parameter"
        else:
            origin = "Published default" if bounds and efficiency_pct == sum(bounds) / 2 else "User override"
        method.update(efficiency_pct=efficiency_pct, efficiency_origin=origin)
    return FieldPlan.model_validate(values)
