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
    active, demo_plan, describe_errors, field_model, install_plan, save_entry, ui_key, validated_plan, workspace,
)

heading("Farm Setup", "Add the fields you plan to irrigate. You’ll assign their water sources in Water Supply.")
state = workspace()
scenario_caption()
farm, year = st.columns([3, 1])
state["farm_name"] = farm.text_input(
    "Farm name", state["farm_name"], max_chars=120, key=ui_key("farm"),
)
state["planning_year"] = year.number_input(
    "Planning year", min_value=1900, max_value=9999, step=1,
    value=state["planning_year"], key=ui_key("year"),
)
fields = active()["fields"]
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

    st.page_link("pages/water_supply.py", label="Continue to Water Supply", icon=":material/arrow_forward:")
else:
    st.caption("Fields appear here after you add them.")

st.divider()
with st.expander("Farm notes (optional)"):
    state["notes"] = st.text_area("Planning context", state["notes"], max_chars=2000, key=ui_key("farm-notes"))

with st.expander("Load an existing farm plan or try the demonstration (optional)"):
    st.caption(
        "Use a Farm Plan (.json) previously downloaded from Ag Salinity Manager, or load a sample farm "
        "to see a completed plan. Loading either replaces the current session."
    )
    upload = st.file_uploader("Farm Plan (.json)", type="json", key=ui_key("upload"))
    uploaded, demo = st.columns(2)
    if uploaded.button("Load uploaded plan", disabled=upload is None):
        try:
            plan = load_plan(upload.getvalue())
        except ValidationError as error:
            errors_panel(describe_errors(error))
        else:
            install_plan(plan)
            st.rerun()
    if demo.button("Load demonstration farm"):
        install_plan(demo_plan())
        st.rerun()

plan, errors = validated_plan()
if plan:
    download_farm_plan(plan)
elif state["reviewed"]:
    with st.expander("Entries to resolve before exporting JSON"):
        errors_panel(errors)
