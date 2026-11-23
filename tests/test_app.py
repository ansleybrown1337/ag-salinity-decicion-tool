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
    guide = next(item.value for item in app.markdown if "**Add your fields.**" in item.value)
    assert "**Add water sources and assign fields.**" in guide
    assert "**Review your farm plan.**" in guide
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


def test_demo_renders_all_pages_and_field_preview_preserves_saved_plan():
    app = load_demonstration()
    assert app.title[0].value == "Farm Dashboard"
    assert app.session_state.workspace["farm_name"] == "Dry Creek Demonstration Farm"
    assert len(app.session_state.workspace["scenarios"]) == 2
    assert any(item.value == "374.2 AF" for item in app.metric)
    app = resume_workspace(app)
    for path, title in (
        ("scenarios", "Scenario Comparison"), ("about", "About & Methods"),
        ("field_decisions", "Field Decisions"), ("farm_dashboard", "Farm Dashboard"),
    ):
        app.switch_page(f"pages/{path}.py").run()
        assert app.title[0].value == title
        assert not app.exception
    assert any(item.value == "374.2 AF" for item in app.metric)

    app.switch_page("pages/field_decisions.py").run()
    widget(app.selectbox, "Crop to try").set_value("potato").run()
    widget(app.slider, "Seasonal crop ET (in)").set_value(25.0).run()
    rows = app.get("dataframe")[0].value
    assert list(rows["Plan"]) == ["Saved · Barley, grain", "What-if · Potato"]
    assert rows.iloc[0]["Total irrigation (AF)"] != rows.iloc[1]["Total irrigation (AF)"]
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
