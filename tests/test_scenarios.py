# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from data.catalog import CROPS, ET_EXAMPLES
from models.water_budget import evaluate_scenario
from schemas.farm import FarmPlan, Scenario, WaterSource, export_plan, load_plan
from schemas.scenarios import duplicate_scenario, field_alternative
from ui.state import as_draft, save_source


def test_duplicate_modify_and_restore(demo):
    baseline = demo.active_scenario
    copy = duplicate_scenario(baseline, "dry", "Dry year")
    assert copy.fields == baseline.fields
    assert copy.fields[0] is not baseline.fields[0]
    values = copy.model_dump()
    values["fields"][0]["etc_in"] = 25
    values["sources"][0]["delivery_af"] = 100
    changed = Scenario.model_validate(values)
    plan = FarmPlan.model_validate({
        **demo.model_dump(), "active_scenario_id": "dry", "scenarios": (baseline, changed),
    })
    restored = load_plan(export_plan(plan))
    assert restored.active_scenario == changed
    assert baseline.fields[0].etc_in == 22
    assert baseline.sources[0].delivery_af == 351
    assert evaluate_scenario(restored.active_scenario).field_demand_af > evaluate_scenario(baseline).field_demand_af


def test_example_alternative_reduces_source_demand(demo):
    baseline, alternative = (evaluate_scenario(scenario) for scenario in demo.scenarios)
    assert baseline.sources[0].demand_af == alternative.sources[0].demand_af
    assert alternative.field_demand_af == pytest.approx(344.346711942)
    assert alternative.sources[1].assessment == "Within delivery"


def test_source_form_rename_and_reassignment(demo):
    draft = as_draft(demo.active_scenario)
    north, _, east = draft["fields"]
    canal, _ = draft["sources"]
    source = WaterSource(id="Main Canal", delivery_af=230, ecw_ds_m=0.7, source_type="Canal water")
    save_source(draft, source, canal, [north["_key"], east["_key"]])
    assert [field["source_id"] for field in draft["fields"]] == ["Main Canal", None, "Main Canal"]
    assert draft["sources"][0]["_key"] == canal["_key"]
    assert demo.active_scenario.fields[1].source_id == "Bench Canal"


def test_field_preview_changes_only_chosen_assumptions(demo):
    field = demo.active_scenario.fields[0]
    preview = field_alternative(
        field, crop=CROPS["potato"], etc_in=20.2, et_estimate=ET_EXAMPLES["potato"],
        desired_yield_pct=100, efficiency_pct=75, leaching_credit_pct=30,
    )
    assert field.crop.id == "barley"
    assert preview.crop.id == "potato"
    assert preview.target_ece_ds_m == preview.crop.threshold_ds_m
    assert preview.et_estimate == ET_EXAMPLES["potato"]
    assert preview.current_ece_ds_m == field.current_ece_ds_m
    assert preview.source_id == field.source_id
    assert preview.acres == field.acres
    assert preview.effective_rain_in == field.effective_rain_in
    assert preview.irrigation.efficiency_origin == "User override"
    assert field_alternative(field, etc_in=field.etc_in) == field


def test_chart_components_sum_to_planned_demand(demo):
    for plan in demo.scenarios:
        result = evaluate_scenario(plan)
        assert result.field_demand_af == pytest.approx(
            result.complete_sum("crop_only_af") + result.complete_sum("added_leach_field_af")
        )
