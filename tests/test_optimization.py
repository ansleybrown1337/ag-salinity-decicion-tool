# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from data.catalog import CROPS, ET_EXAMPLES
from models.optimization import crop_option, optimize_crop_plan
from models.water_budget import evaluate_scenario
from schemas.scenarios import field_alternative


def test_leaching_constraint_changes_the_revenue_optimum_at_fixed_target(demo):
    baseline = demo.active_scenario
    canal, well = baseline.sources
    well = well.model_copy(update={"delivery_af": 90.0})
    corn = baseline.fields[-1]
    barley = field_alternative(corn, crop=CROPS["barley"], etc_in=ET_EXAMPLES["barley"].etc_in,
                               target_ece_ds_m=corn.target_ece_ds_m)
    options = {field.id: [crop_option(field, canal, 100, 4, "unit")] for field in baseline.fields[:-1]}
    options[corn.id] = [crop_option(corn, well, 40, 145, "dry ton"), crop_option(barley, well, 70, 4, "bu")]

    crop_only = optimize_crop_plan(options, (canal, well), require_leaching=False)
    protect_soil = optimize_crop_plan(options, (canal, well), require_leaching=True)
    assert not crop_only.diagnostics and not protect_soil.diagnostics
    assert [option.result.field.crop.id for option in crop_only.options] == ["barley", "alfalfa", "corn_silage"]
    assert [option.result.field.crop.id for option in protect_soil.options] == ["barley", "alfalfa", "barley"]
    assert protect_soil.options[-1].result.field.target_ece_ds_m == corn.target_ece_ds_m
    assert crop_only.options[-1].gross_revenue == pytest.approx(36 * 40 * 0.778 * 145)
    assert crop_only.gross_revenue > protect_soil.gross_revenue


def test_deliveries_from_other_sources_cannot_offset_an_optimizer_shortfall(demo):
    plan = demo.active_scenario
    sources = {source.id: source for source in plan.sources}
    options = {field.id: [crop_option(field, sources[field.source_id], 100, 4, "unit")] for field in plan.fields}
    result = optimize_crop_plan(options, plan.sources, require_leaching=False)
    assert not result.options
    assert len(result.diagnostics) == 1
    assert "East Well delivers 70.0 AF" in result.diagnostics[0]
    assert "11.2 AF" in result.diagnostics[0]


def test_rain_covered_crop_is_not_certified_for_saline_water_maintenance(demo):
    baseline = demo.active_scenario
    field = baseline.fields[-1].model_copy(update={"effective_rain_in": 100.0})
    well = baseline.sources[-1]
    options = {field.id: [crop_option(field, well, 40, 145, "dry ton")]}
    crop_only = optimize_crop_plan(options, (well,), require_leaching=False)
    maintenance = optimize_crop_plan(options, (well,), require_leaching=True)
    assert crop_only.options[0].result.crop_only_af == 0
    assert not maintenance.options
    assert "no eligible crop with an assessable maintenance estimate" in maintenance.diagnostics[0]


def test_leaching_coverage_distinguishes_source_gap_and_unallocated_field_water(demo):
    plan = demo.active_scenario
    canal, well = plan.sources
    original = evaluate_scenario(plan)
    canal_summary, well_summary = original.sources
    assert canal_summary.leaching_status == "Covers crops and leaching"
    assert well_summary.leaching_status == "Short before leaching"
    assert well_summary.leaching_gap_af == pytest.approx(12.6, abs=0.01)
    assert well_summary.field_leaching_status(original.fields[-1]) == "Leaching gap"

    shared = evaluate_scenario(plan.model_copy(update={
        "sources": (canal.model_copy(update={"delivery_af": 275.0}), well),
    }))
    source = shared.sources[0]
    assert source.leaching_status == "Covers crops with a leaching gap"
    assert source.leaching_gap_af == pytest.approx(5.42, abs=0.01)
    assert source.field_leaching_status(shared.fields[0]) == "Field allocation needed"
