# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from config.branding import ROOT, VERSION
from data.catalog import ET_EXAMPLES, REFERENCES
from models.water_budget import evaluate_scenario
from schemas.farm import export_plan, farm_plan_filename, load_plan


def test_export_import_restores_entire_plan(demo):
    restored = load_plan(export_plan(demo))
    assert restored == demo
    assert len(restored.scenarios) == 2
    assert len(restored.active_scenario.fields) == 3
    assert restored.active_scenario.fields[2].irrigation.efficiency_origin == "User override"
    assert restored.active_scenario.fields[2].target_ece_ds_m == demo.active_scenario.fields[2].target_ece_ds_m


def test_export_filename_identifies_version_and_local_timestamp():
    local_time = datetime(2026, 11, 20, 14, 35, 12, tzinfo=timezone(timedelta(hours=-7)))
    assert farm_plan_filename(local_time) == f"ag-salinity-farm-plan_v{VERSION}_2026-11-20_143512-0700.json"


@pytest.mark.parametrize("value", ["broken", "[]", '{"schema_version":"9.0"}'])
def test_invalid_json_shape_or_version(value):
    with pytest.raises(ValidationError):
        load_plan(value)


@pytest.mark.parametrize("key, value, expected", [
    ("acres", 0, "greater than 0"), ("acres", "22", "valid number"),
    ("current_ece_ds_m", -2, "greater than or equal to 0"),
    ("desired_yield_pct", 0, "greater than 0"), ("desired_yield_pct", 101, "less than or equal"),
    ("source_id", "missing", "existing water source"), ("target_ece_ds_m", 2, "Derived target ECe"),
])
def test_import_rejects_bad_field_values(demo, key, value, expected):
    payload = demo.model_dump(mode="json")
    payload["scenarios"][0]["fields"][0][key] = value
    with pytest.raises(ValidationError, match=expected):
        load_plan(json.dumps(payload))


def test_import_reports_missing_values_and_duplicate_fields(demo):
    payload = demo.model_dump(mode="json")
    del payload["scenarios"][0]["fields"][0]["etc_in"]
    with pytest.raises(ValidationError, match="etc_in"):
        load_plan(json.dumps(payload))
    fields = payload["scenarios"][0]["fields"]
    fields[0]["etc_in"] = 20
    fields[1]["id"] = fields[0]["id"].upper()
    with pytest.raises(ValidationError, match="field ID must be unique"):
        load_plan(json.dumps(payload))


def test_delivery_required_and_nonnegative(demo):
    payload = demo.model_dump(mode="json")
    del payload["scenarios"][0]["sources"][0]["delivery_af"]
    payload["scenarios"][0]["sources"][1]["delivery_af"] = -1
    with pytest.raises(ValidationError) as error:
        load_plan(json.dumps(payload))
    assert "Field required" in str(error.value)
    assert "greater than or equal to 0" in str(error.value)


def test_load_legacy_plan_preserves_budget_and_relinks_descriptive_ids(demo):
    payload = demo.model_dump(mode="json")
    payload["schema_version"] = "1.0"
    for scenario in payload["scenarios"]:
        old_ids = {}
        for index, source in enumerate(scenario["sources"]):
            old_id = f"source-{index}"
            old_ids[source["id"]] = old_id
            source["name"], source["id"] = source["id"], old_id
            source.pop("delivery_af")
            source.update(allocation_af=390 if index == 0 else 70, meter="Farm turnout" if index == 0 else "Field",
                          conveyance_efficiency_pct=90 if index == 0 else None)
        for index, field in enumerate(scenario["fields"]):
            field["name"], field["id"] = field["id"], f"field-{index}"
            field["source_id"] = old_ids[field["source_id"]]
            field.pop("et_estimate")
            if field["crop"]["id"] == "corn_silage":
                field["crop"].update(id="corn_forage", label="Corn, forage")
    migrated = load_plan(json.dumps(payload))
    assert migrated.schema_version == "2.0"
    assert migrated.scenarios == demo.scenarios
    result = evaluate_scenario(migrated.active_scenario)
    assert result.field_supply_af == 421
    assert result.source_shortfall_af == pytest.approx(23.774156567)


def test_et_override_and_reference_round_trip(demo):
    payload = demo.model_dump(mode="json")
    corn = payload["scenarios"][0]["fields"][-1]
    corn["et_estimate"] = ET_EXAMPLES["corn_silage"].model_dump()
    restored = load_plan(export_plan(load_plan(json.dumps(payload))))
    field = restored.active_scenario.fields[-1]
    assert field.etc_in == 27.0
    assert field.et_estimate.etc_in == 22.9
    assert field.et_estimate.location == "Greeley, Colorado"


def test_resolved_crop_and_efficiency_snapshots_survive(demo):
    payload = demo.model_dump(mode="json")
    field = payload["scenarios"][0]["fields"][0]
    field["crop"].update(threshold_ds_m=7.25, slope_pct_per_ds_m=4.125,
                         threshold_origin="User override", slope_origin="User override")
    field.update(target_ece_override=True, target_ece_ds_m=5.75)
    field["irrigation"].update(efficiency_pct=75, efficiency_origin="User override")
    restored = load_plan(export_plan(load_plan(json.dumps(payload)))).active_scenario.fields[0]
    assert restored.crop.threshold_ds_m == 7.25
    assert restored.crop.slope_pct_per_ds_m == 4.125
    assert restored.target_ece_ds_m == 5.75
    assert restored.irrigation.efficiency_pct == 75


def test_readme_cites_reference_registry():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for reference in REFERENCES.values():
        assert reference.citation in readme
        assert reference.url in readme
