# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from copy import deepcopy

from streamlit.testing.v1 import AppTest

from config.branding import CONTACT_URL, COPYRIGHT_YEAR, LICENSE, REPOSITORY_URL, ROOT, TITLE


def button(app, label):
    return next(item for item in app.button if item.label == label)


def widget(elements, label):
    return next(item for item in elements if item.label == label)


def farm_setup():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    return app.switch_page("pages/farm_setup.py").run()


def load_demonstration():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    return button(app, "Load demonstration farm").click().run()


def select_table_row(app, table, index, action=None):
    # AppTest does not carry dataframe widget selections across button events.
    workspace = app.session_state.workspace
    key = f"{workspace['epoch']}/{workspace['active_scenario_id']}/{table}"
    app.session_state[key] = {"selection": {"rows": [index], "columns": [], "cells": []}}
    if action:
        button(app, action).click()
    app.run()


def resume_workspace(app):
    # AppTest can retain widget nodes from before a form-reset rerun.
    # Start a fresh widget tree with the workspace saved by the action.
    resumed = AppTest.from_file(str(ROOT / "app.py"))
    resumed.session_state.workspace = deepcopy(app.session_state.workspace)
    return resumed.switch_page("pages/farm_setup.py").run()


def test_home_guides_new_users_to_farm_setup():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    assert app.title[0].value == TITLE
    assert any(item.value == f"Copyright © {COPYRIGHT_YEAR} · {LICENSE}" for item in app.sidebar.caption)
    guide = next(item.value for item in app.markdown if "1. **Farm Setup.**" in item.value)
    assert "2. **Farm Dashboard.**" in guide
    assert "3. **What-If Scenarios.**" in guide
    assert "4. **Field Details.**" in guide
    assert any(CONTACT_URL in item.value for item in app.markdown)
    assert any(f"{REPOSITORY_URL.rstrip('/')}/issues" in item.value for item in app.markdown)
    button(app, "Get started").click().run()
    assert app.title[0].value == "Farm Setup"
    assert not app.exception


def test_first_review_reports_incomplete_setup():
    app = farm_setup()
    assert app.title[0].value == "Farm Setup"
    app.switch_page("pages/farm_dashboard.py").run()
    assert app.title[0].value == "Farm Dashboard"
    assert "Complete Farm Setup" in app.info[0].value
    assert not app.warning
    assert not app.metric
    app.switch_page("pages/farm_setup.py").run()
    button(app, "Review and Calculate Farm Plan").click().run()
    assert "Add at least one field" in app.error[0].value
    assert "Add at least one water source" in app.error[0].value
    assert not app.exception


def test_demo_renders_all_pages_and_field_details_compare_saved_plans():
    app = load_demonstration()
    assert app.title[0].value == "Farm Dashboard"
    assert app.session_state.workspace["farm_name"] == "Dry Creek Demonstration Farm"
    assert len(app.session_state.workspace["scenarios"]) == 2
    assert any(item.value == "374.2 AF" for item in app.metric)
    app = resume_workspace(app)
    for path, title in (
        ("scenarios", "What-If Scenarios"), ("about", "About & Methods"),
        ("field_decisions", "Field Details"), ("farm_dashboard", "Farm Dashboard"),
    ):
        app.switch_page(f"pages/{path}.py").run()
        assert app.title[0].value == title
        assert not app.exception
    assert any(item.value == "374.2 AF" for item in app.metric)

    app.session_state.selected_field = "east bench"
    app.switch_page("pages/field_decisions.py").run()
    rows = app.get("dataframe")[0].value
    assert list(rows["Scenario"]) == ["Baseline", "Scenario 1"]
    assert list(rows["Crop"]) == ["Corn, silage", "Barley, grain"]
    assert list(rows["Scenario name"]) == ["Baseline", "Barley on East Bench"]
    assert list(rows["Target basis"]) == ["Calculated at 90% relative yield"] * 2
    assert rows.iloc[0]["Total irrigation (AF)"] != rows.iloc[1]["Total irrigation (AF)"]
    app.session_state.workspace["scenarios"]["barley-alternative"]["fields"][-1]["target_ece_override"] = True
    app.run()
    assert list(app.get("dataframe")[0].value["Target basis"]) == ["Calculated at 90% relative yield", "Manually entered"]
    app.session_state.workspace["active_scenario_id"] = "barley-alternative"
    app.switch_page("pages/farm_dashboard.py").run()
    assert any(item.value == "374.2 AF" for item in app.metric)
    assert not app.exception


def test_scenario_page_compares_baseline_then_saves_crop_changes():
    app = resume_workspace(load_demonstration())
    workspace = app.session_state.workspace
    workspace["scenarios"].pop("barley-alternative")
    app.switch_page("pages/scenarios.py").run()
    assert list(app.get("dataframe")[0].value["Scenario"]) == ["Baseline"]
    button(app, "Add new scenario").click().run()
    assert list(workspace["scenarios"]) == ["baseline"]
    widget(app.text_input, "Scenario name").set_value("Potatoes and wheat")
    widget(app.selectbox, "Crop · North Bench").set_value("potato")
    widget(app.selectbox, "Crop · Creek Flat").set_value("wheat")
    app.run()
    assert widget(app.number_input, "Seasonal crop ET for North Bench (in)").value == 20.2
    assert widget(app.number_input, "Seasonal crop ET for Creek Flat (in)").value == 17.9
    button(app, "Save scenario").click().run()
    assert list(workspace["scenarios"])[0] == "baseline"
    baseline, saved = workspace["scenarios"].values()
    assert saved["name"] == "Potatoes and wheat"
    assert [row["crop"]["id"] for row in baseline["fields"][:2]] == ["barley", "alfalfa"]
    assert [row["crop"]["id"] for row in saved["fields"][:2]] == ["potato", "wheat"]
    assert workspace["active_scenario_id"] == "baseline"


def test_drought_scenario_uses_effective_precipitation_without_changing_crops_or_et():
    app = resume_workspace(load_demonstration()).switch_page("pages/scenarios.py").run()
    state = app.session_state.workspace
    button(app, "Add new scenario").click().run()
    widget(app.text_input, "Scenario name").set_value("Dry year")
    widget(app.number_input, "Effective precipitation to apply (in)").set_value(1.0)
    app.run()
    button(app, "Apply to all fields").click().run()
    widget(app.number_input, "Expected effective precipitation for East Bench (in)").set_value(0.0)
    button(app, "Save scenario").click().run()

    baseline = state["scenarios"]["baseline"]["fields"]
    saved = next(item["fields"] for item in state["scenarios"].values() if item["name"] == "Dry year")
    assert [row["effective_rain_in"] for row in baseline] == [5.0, 5.0, 4.0]
    assert [row["effective_rain_in"] for row in saved] == [1.0, 1.0, 0.0]
    assert [(row["crop"], row["etc_in"]) for row in saved] == [(row["crop"], row["etc_in"]) for row in baseline]
    rows = app.get("dataframe")[0].value.set_index("Scenario name")
    assert rows.loc["Dry year", "Total irrigation (AF)"] > rows.loc["Baseline", "Total irrigation (AF)"]
    assert rows.loc["Dry year", "Scenario"] == "Scenario 2"

    table = f"scenario-table/{hash(tuple(state['scenarios']))}"
    select_table_row(app, table, 1, "Delete scenario")
    rows = app.get("dataframe")[0].value.set_index("Scenario name")
    assert rows.loc["Dry year", "Scenario"] == "Scenario 2"


def test_dashboard_reports_salinity_loss_even_when_a_lower_yield_target_is_met():
    app = load_demonstration()
    for field in app.session_state.workspace["scenarios"]["baseline"]["fields"]:
        field["desired_yield_pct"] = 70.0
    app.switch_page("pages/farm_dashboard.py").run()

    assert any("yield loss in **2 of 3 fields**" in item.value for item in app.warning)


def test_optimization_saves_a_numbered_alternative_and_keeps_the_baseline():
    app = resume_workspace(load_demonstration()).switch_page("pages/optimization.py").run()
    state = app.session_state.workspace
    existing_fields = deepcopy(state["scenarios"]["baseline"]["fields"])
    widget(app.multiselect, "Eligible crops for East Bench").set_value([("corn_silage",), ("barley",)]).run()
    for label, unit, expected_yield, price in (
        ("Alfalfa", "dry ton", 6.0, 180.0), ("Barley, grain", "bu", 110.0, 4.0),
        ("Corn, silage", "dry ton", 12.0, 145.0),
    ):
        widget(app.text_input, f"Sale unit for {label}").set_value(unit)
        widget(app.number_input, f"Expected yield per acre for {label}").set_value(expected_yield)
        widget(app.number_input, f"Sale price ($/unit) for {label}").set_value(price)
    button(app, "Run optimization").click().run()
    assert not app.exception
    widget(app.text_input, "Optimized scenario name").set_value("Optimized demo")
    button(app, "Save as what-if scenario").click().run()
    assert app.title[0].value == "What-If Scenarios"
    saved = next(scenario for scenario in state["scenarios"].values() if scenario["name"] == "Optimized demo")
    assert saved["number"] == 2
    assert saved["fields"][-1]["crop"]["id"] == "barley"
    assert saved["fields"][-1]["target_ece_ds_m"] == existing_fields[-1]["target_ece_ds_m"]
    assert state["scenarios"]["baseline"]["fields"] == existing_fields


def test_field_details_opens_a_focused_editor_for_the_selected_alternative():
    app = resume_workspace(load_demonstration())
    app.session_state.selected_field = "east bench"
    app.switch_page("pages/field_decisions.py").run()
    widget(app.selectbox, "Scenario to edit").set_value("barley-alternative").run()
    button(app, "Edit this field in a scenario").click().run()
    assert app.title[0].value == "What-If Scenarios"
    assert [item.label for item in app.selectbox] == ["Crop · East Bench"]
    state = app.session_state.workspace
    before = deepcopy(state["scenarios"]["barley-alternative"]["fields"])
    widget(app.number_input, "Expected effective precipitation for East Bench (in)").set_value(0.5)
    # Keep the scenario page selected on subsequent AppTest reruns.
    app.switch_page("pages/scenarios.py")
    button(app, "Save scenario").click().run()
    after = state["scenarios"]["barley-alternative"]["fields"]
    assert state["scenarios"]["barley-alternative"]["number"] == 1
    assert after[-1]["effective_rain_in"] == 0.5
    assert state["scenarios"]["baseline"]["fields"][-1]["effective_rain_in"] == 4.0
    assert [{k: v for k, v in row.items() if k != "_key"} for row in after[:-1]] == [
        {k: v for k, v in row.items() if k != "_key"} for row in before[:-1]
    ]


def test_setup_adds_field_with_crop_estimate_then_assigns_water():
    app = farm_setup()
    assert not app.get("dataframe")
    assert widget(app.number_input, "Desired relative yield (%)").value == 100.0
    widget(app.text_input, "Farm name").set_value("Test Farm")
    widget(app.text_input, "Field ID").set_value("North Pivot")
    widget(app.number_input, "Field area (acres)").set_value(40.0)
    widget(app.number_input, "Soil salinity (ECe, dS/m)").set_value(2.1)
    widget(app.selectbox, "Irrigation method").set_value("pivot")
    widget(app.selectbox, "Crop").set_value("corn_grain")
    app.run()
    assert widget(app.number_input, "Seasonal crop ET (in)").value == 23.9
    widget(app.selectbox, "Crop").set_value("corn_silage").run()
    assert widget(app.number_input, "Seasonal crop ET (in)").value == 22.9
    widget(app.number_input, "Seasonal crop ET (in)").set_value(24.0)
    button(app, "Add field").click().run()
    fields = app.session_state.workspace["scenarios"]["baseline"]["fields"]
    field_key = fields[0]["_key"]
    assert fields[0]["id"] == "North Pivot"
    assert fields[0]["etc_in"] == 24.0
    assert fields[0]["et_estimate"]["etc_in"] == 22.9
    assert fields[0]["source_id"] is None
    assert fields[0]["desired_yield_pct"] == 100.0
    assert fields[0]["target_ece_ds_m"] == fields[0]["crop"]["threshold_ds_m"]

    app = resume_workspace(app)
    widget(app.text_input, "Water source ID").set_value("East Well")
    widget(app.number_input, "Expected farm delivery (acre-feet)").set_value(150.0)
    widget(app.number_input, "Water salinity (ECw, dS/m)").set_value(1.2)
    widget(app.multiselect, "Which fields does this source irrigate?").set_value([field_key])
    button(app, "Add water source").click().run()
    scenario = app.session_state.workspace["scenarios"]["baseline"]
    assert scenario["fields"][0]["source_id"] == "East Well"
    assert scenario["sources"][0]["delivery_af"] == 150.0
    app = resume_workspace(app)
    button(app, "Review and Calculate Farm Plan").click().run()
    assert app.title[0].value == "Farm Dashboard"
    assert any(item.value == "150.0 AF" for item in app.metric)
    assert not app.exception


def test_saved_field_can_be_edited_and_deleted_from_table_controls():
    app = resume_workspace(load_demonstration())
    assert button(app, "Edit field").proto.disabled
    assert button(app, "Delete field").proto.disabled

    select_table_row(app, "saved-fields-table/0", 0, "Edit field")
    targets = [item.value for item in app.number_input if item.label == "Desired relative yield (%)"]
    assert targets == [100.0, 90.0]
    editors = [item for item in app.text_input if item.label == "Field ID"]
    editors[-1].set_value("North Bench Updated")
    select_table_row(app, "saved-fields-table/0", 0, "Save field changes")
    saved = app.session_state.workspace["scenarios"]["baseline"]["fields"][0]
    assert saved["id"] == "North Bench Updated"
    assert saved["source_id"] == "Bench Canal"
    assert saved["desired_yield_pct"] == 90.0

    app = resume_workspace(app)
    select_table_row(app, "saved-fields-table/0", 0, "Delete field")
    fields = app.session_state.workspace["scenarios"]["baseline"]["fields"]
    assert [field["id"] for field in fields] == ["Creek Flat", "East Bench"]
    assert len(app.session_state.workspace["scenarios"]["barley-alternative"]["fields"]) == 3


def test_deleting_source_unassigns_its_fields_in_the_active_scenario():
    app = resume_workspace(load_demonstration())
    assert button(app, "Delete water source").proto.disabled
    select_table_row(app, "saved-sources-table/0", 0, "Delete water source")

    plans = app.session_state.workspace["scenarios"]
    assert [source["id"] for source in plans["baseline"]["sources"]] == ["East Well"]
    assert [field["source_id"] for field in plans["baseline"]["fields"]] == [None, None, "East Well"]
    assert plans["barley-alternative"]["fields"][0]["source_id"] == "Bench Canal"


def test_deleting_active_alternative_returns_to_baseline():
    app = resume_workspace(load_demonstration())
    state = app.session_state.workspace
    state["active_scenario_id"] = "barley-alternative"
    app.switch_page("pages/scenarios.py").run()
    table = f"scenario-table/{hash(tuple(state['scenarios']))}"
    select_table_row(app, table, 0)
    assert button(app, "Delete scenario").proto.disabled
    select_table_row(app, table, 1, "Delete scenario")
    assert list(state["scenarios"]) == ["baseline"]
    assert state["active_scenario_id"] == "baseline"
