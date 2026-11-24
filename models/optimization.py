# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
from math import fsum

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_array

from models.validation import finite
from models.water_budget import WATER_TOLERANCE_AF, FieldResult, evaluate_field
from schemas.farm import FieldPlan, WaterSource


@dataclass(frozen=True)
class CropOption:
    result: FieldResult
    yield_per_acre: float
    gross_revenue: float
    unit: str

    def required_water(self, require_leaching: bool) -> float | None:
        if not require_leaching:
            return self.result.crop_only_af
        return self.result.field_af if self.result.maintenance_assessable else None


@dataclass(frozen=True)
class OptimizationResult:
    options: tuple[CropOption, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def gross_revenue(self) -> float:
        return fsum(option.gross_revenue for option in self.options)


def crop_option(field: FieldPlan, source: WaterSource, expected_yield: float, price: float, unit: str) -> CropOption:
    """Value the modeled production endpoint at the entered soil salinity."""
    finite(expected_yield, "Expected yield")
    finite(price, "Sale price")
    result = evaluate_field(field, source)
    yield_per_acre = expected_yield * (result.current_yield_pct / 100)
    revenue = finite(field.acres * yield_per_acre * price, "Estimated gross revenue")
    return CropOption(result, yield_per_acre, revenue, unit)


def optimize_crop_plan(
    fields: dict[str, list[CropOption]], sources: tuple[WaterSource, ...], *, require_leaching: bool,
) -> OptimizationResult:
    """Choose one crop per field under the independently assigned source budgets."""
    source_by_id = {source.id: source for source in sources}
    usable = {}
    minima = {key: [] for key in source_by_id}
    issues = []
    for field_id, options in fields.items():
        feasible = [
            (option, water) for option in options if (water := option.required_water(require_leaching)) is not None
        ]
        if not feasible:
            if options:
                issues.append(f"{field_id} ({options[0].result.source.id}) has no eligible crop with an assessable maintenance estimate.")
            else:
                issues.append(f"{field_id} has no eligible crop with complete inputs.")
            continue
        source_id = feasible[0][0].result.source.id
        minima[source_id].append(min(water for _, water in feasible))
        usable[field_id] = feasible

    for source_id, demands in minima.items():
        minimum = fsum(demands)
        delivery = source_by_id[source_id].delivery_af
        if minimum - delivery > WATER_TOLERANCE_AF:
            issues.append(
                f"{source_id} delivers {delivery:,.1f} AF. The lowest demand among eligible crops is "
                f"{minimum:,.1f} AF, a shortfall of {minimum - delivery:,.1f} AF."
            )
    if issues:
        return OptimizationResult(diagnostics=tuple(issues))
    if not usable:
        return OptimizationResult(diagnostics=("Add fields and choose eligible crops to optimize.",))

    source_rows = {key: len(usable) + index for index, key in enumerate(source_by_id)}
    matrix_rows, matrix_cols, weights, candidates = [], [], [], []
    for field_index, feasible in enumerate(usable.values()):
        for option, water in feasible:
            column = len(candidates)
            candidates.append(option)
            matrix_rows.extend((field_index, source_rows[option.result.source.id]))
            matrix_cols.extend((column, column))
            weights.extend((1.0, water))

    n_fields = len(usable)
    n_sources = len(sources)
    matrix = coo_array(
        (weights, (matrix_rows, matrix_cols)), shape=(n_fields + n_sources, len(candidates)),
    ).tocsc()
    field_bounds = np.ones(n_fields)
    deliveries = np.array([source.delivery_af for source in sources])
    constraint = LinearConstraint(matrix, np.r_[field_bounds, np.full(n_sources, -np.inf)], np.r_[field_bounds, deliveries])
    revenues = np.array([option.gross_revenue for option in candidates])
    solution = milp(
        -revenues / max(1.0, revenues.max()), integrality=np.ones(len(candidates)),
        bounds=Bounds(0, 1), constraints=constraint, options={"time_limit": 10.0, "mip_rel_gap": 0.0},
    )
    if not solution.success or solution.x is None:
        return OptimizationResult(diagnostics=("The solver could not confirm an optimal feasible plan.",))
    selected = np.flatnonzero(solution.x > 0.5)
    # Check the rounded integer solution against the original acre-foot limits before it can be saved.
    used = matrix[:, selected].sum(axis=1)
    if (not np.array_equal(used[:n_fields], field_bounds)
            or np.any(used[n_fields:] - deliveries > WATER_TOLERANCE_AF)):
        return OptimizationResult(diagnostics=("The solver returned a plan outside the assigned water limits.",))
    return OptimizationResult(options=tuple(candidates[index] for index in selected))
