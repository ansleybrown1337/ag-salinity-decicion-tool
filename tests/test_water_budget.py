# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from models.water_budget import evaluate_scenario
from schemas.farm import Scenario


def test_single_field_zero_delivery(demo):
    original = demo.active_scenario
    source = original.sources[1].model_copy(update={"delivery_af": 0, "ecw_ds_m": 0})
    field = original.fields[0].model_copy(update={"source_id": source.id, "acres": 12})
    result = evaluate_scenario(Scenario(id="one", name="One", fields=[field], sources=[source]))
    assert result.net_crop_af == 17
    assert result.field_demand_af == pytest.approx(17 / .7)
    assert result.field_demand_af == result.sources[0].demand_af
    assert result.field_balance_af == -result.field_demand_af


def test_multi_field_delivered_balance_and_source_shortfall(demo):
    result = evaluate_scenario(demo.active_scenario)
    assert result.acres == 149
    assert result.field_supply_af == 421
    assert result.net_crop_af == pytest.approx((65 * 17 + 48 * 29 + 36 * 23) / 12)
    assert result.field_demand_af == pytest.approx(374.193338572)
    canal, well = result.sources
    assert canal.demand_af == pytest.approx(result.fields[0].field_af + result.fields[1].field_af)
    assert well.balance_af == pytest.approx(-23.774156567)
    assert result.field_balance_af > 0
    assert well.assessment == "Shortfall"
    assert result.source_shortfall_af == pytest.approx(-well.balance_af)
    assert result.salinity_concerns == 2


def test_infeasible_target_does_not_hide_known_source_deficit(demo):
    scenario = demo.active_scenario
    field = scenario.fields[1].model_copy(update={"target_ece_override": True, "target_ece_ds_m": 0.2})
    canal = scenario.sources[0].model_copy(update={"delivery_af": 0, "ecw_ds_m": 1})
    changed = Scenario(id="drought", name="Drought", fields=[scenario.fields[0], field, scenario.fields[2]],
                       sources=[canal, scenario.sources[1]])
    result = evaluate_scenario(changed)
    assert result.fields[1].field_af is None
    assert result.fields[1].current_yield_pct > 0
    assert result.field_demand_af is None
    assert result.field_balance_af is None
    assert result.sources[0].assessment == "Known demand exceeds delivery"
    assert result.sources[0].known_demand_af > 0


def test_high_leaching_and_manual_target_warning(demo):
    scenario = demo.active_scenario
    field = scenario.fields[-1].model_copy(
        update={"target_ece_override": True, "target_ece_ds_m": 5, "desired_yield_pct": 100})
    source = scenario.sources[-1].model_copy(update={"ecw_ds_m": 6})
    changed = Scenario(id="salt", name="Salt", fields=[field], sources=[source])
    row = evaluate_scenario(changed).fields[0]
    assert row.field_af > 0
    assert any("exceeds 25%" in warning for warning in row.warnings)
    assert any("manual ECe target" in warning for warning in row.warnings)
