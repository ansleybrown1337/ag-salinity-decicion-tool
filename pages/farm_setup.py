# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st
from pydantic import ValidationError

from schemas.farm import load_plan
from ui.field_controls import field_inputs
from ui.shared import (
    ECE_HELP, ET_HELP, download_farm_plan, errors_panel, heading, plain_text, reset_entry,
    scenario_caption, selected_table_row,
)
from ui.state import (
    active, describe_errors, field_model, install_plan, save_entry, ui_key,
    validate_scenario, validated_plan, workspace,
)
from ui.water_sources import show_water_sources

heading(
    "Farm Setup",
    "Upload a saved farm plan or create one using the steps below.",
    banner="farm-setup",
)

with st.container(border=True):
    st.subheader("Upload an existing farm plan")
    st.caption(
        "Choose a .json file previously downloaded from Ag Salinity Manager. "
        "Uploading a plan replaces the current session’s plan."
    )
    upload = st.file_uploader(
        "Upload a farm plan (.json)", type="json", key=ui_key("upload"), label_visibility="collapsed",
    )
    if upload is not None:
        try:
            plan = load_plan(upload.getvalue())
        except ValidationError as error:
            errors_panel(describe_errors(error))
        else:
            install_plan(plan)
            st.toast("Farm plan loaded.")
            st.rerun()

state = workspace()
st.header("Review or edit your farm plan" if state["reviewed"] else "Or create a new farm plan")
scenario_caption()
farm, year = st.columns([3, 1])
state["farm_name"] = farm.text_input(
    "Farm name", state["farm_name"], max_chars=120, key=ui_key("farm"),
)
state["planning_year"] = year.number_input(
    "Planning year", min_value=1900, max_value=9999, step=1,
    value=state["planning_year"], key=ui_key("year"),
)
st.header("1. Add your fields")
st.write(
    "Enter the area, crop, soil salinity, and irrigation method for each field you plan to irrigate. "
    "Select **Add field** after each entry."
)
scenario = active()
fields = scenario["fields"]
add_revision = ui_key("add-field-revision")
add_key = ui_key(f"add-field/{st.session_state.get(add_revision, 0)}")
with st.container(border=True):
    st.subheader("Field details")
    record = field_inputs(None, add_key)
    if st.button("Add field", type="primary", key=f"{add_key}/save"):
        try:
            save_entry(fields, field_model(record), None)
        except ValueError as error:
            errors_panel(describe_errors(error))
        else:
            reset_entry(add_revision)

st.subheader("Saved fields")
if fields:
    st.caption("Use the selector at the left of a row to edit or delete that field.")
    table_revision = ui_key("saved-fields-table-revision")
    selection = selected_table_row([
        {
            "Field ID": row["id"], "Area (ac)": row["acres"], "Crop": row["crop"]["label"],
            "Soil ECe (dS/m)": row["current_ece_ds_m"], "Irrigation method": row["irrigation"]["label"],
            "Crop ET (in)": row["etc_in"],
        }
        for row in fields
    ], key=ui_key(f"saved-fields-table/{st.session_state.get(table_revision, 0)}"), column_config={
        "Soil ECe (dS/m)": st.column_config.NumberColumn(help=ECE_HELP),
        "Crop ET (in)": st.column_config.NumberColumn(help=ET_HELP),
    })

    selected = fields[selection] if selection is not None else None
    selected_key = selected["_key"] if selected else None
    editing = ui_key("editing-field")
    edit, delete, _ = st.columns([1, 1, 3])

    def close_editor():
        st.session_state.pop(editing, None)

    if edit.button("Edit field", disabled=selected is None, width="stretch") and selected is not None:
        st.session_state[editing] = selected_key
    if delete.button("Delete field", disabled=selected is None, width="stretch") and selected is not None:
        fields.remove(selected)
        close_editor()
        reset_entry(table_revision)

    if selected and st.session_state.get(editing) == selected_key:
        edit_revision = ui_key("edit-field-revision")
        key = ui_key(f"edit-field/{selected_key}/{st.session_state.get(edit_revision, 0)}")
        with st.container(border=True):
            st.subheader(f"Edit {plain_text(selected['id'])}")
            changes = field_inputs(selected, key)
            save, cancel = st.columns(2)
            if save.button("Save field changes", type="primary"):
                try:
                    save_entry(fields, field_model(changes), selected)
                except ValueError as error:
                    errors_panel(describe_errors(error))
                else:
                    close_editor()
                    reset_entry(edit_revision)
            if cancel.button("Cancel edit"):
                close_editor()
                reset_entry(edit_revision)
else:
    st.caption("Fields appear here after you add them.")

st.header("2. Add water sources and assign fields")
st.write(
    "For each source, enter the volume you expect to reach the farm this year and the water salinity. "
    "Select all the fields it irrigates, then select **Add water source**. Assign each field to one source."
)
show_water_sources(scenario)

st.header("3. Review your farm plan")
st.write(
    "When every field has a water source, calculate the plan to see how much irrigation your fields need "
    "and where delivery may fall short."
)
state["notes"] = st.text_area(
    "Add additional farm notes as needed (optional)", state["notes"], height=90, max_chars=2000,
    key=ui_key("farm-notes"), placeholder="e.g. Planning assumptions or changes to revisit next season",
)
if st.button("Review and Calculate Farm Plan", type="primary"):
    _, issues = validate_scenario(scenario)
    if not state["farm_name"].strip():
        issues.insert(0, "Enter a farm name at the top of Farm Setup.")
    if issues:
        errors_panel(issues)
    else:
        state["reviewed"] = True
        st.switch_page("pages/farm_dashboard.py")

plan, errors = validated_plan()
if plan:
    download_farm_plan(plan)
elif state["reviewed"]:
    with st.expander("Entries to resolve before exporting JSON"):
        errors_panel(errors)
