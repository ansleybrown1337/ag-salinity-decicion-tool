# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from math import fsum

import streamlit as st

from schemas.farm import WaterSource
from ui.shared import (
    DELIVERY_HELP, ECW_HELP, errors_panel, heading, plain_text, reset_entry,
    scenario_caption, selected_table_row, volume,
)
from ui.state import active, describe_errors, save_source, ui_key, validate_scenario, workspace

heading("Water Supply", "Add each water source, then choose the fields it irrigates.")
scenario_caption()
scenario = active()
fields = scenario["fields"]
sources = scenario["sources"]
field_ids = {field["_key"]: field["id"] for field in fields}

def source_form(selected, key):
    source = selected or {}
    left, right = st.columns(2)
    source_id = left.text_input(
        "Water source ID", source.get("id", ""), placeholder="e.g. East Well", max_chars=120, key=f"{key}/id",
        help="Use one unique name or code you recognize for this water source.",
    )
    types = ["Surface water", "Canal water", "Groundwater", "Other"]
    source_type = right.selectbox(
        "Source type (optional)", types, index=types.index(source.get("source_type", "Other")), key=f"{key}/type",
    )

    delivery = left.number_input(
        "Expected farm delivery (acre-feet)", min_value=0.0, step=1.0, value=source.get("delivery_af"),
        key=f"{key}/delivery", help=DELIVERY_HELP,
    )
    ecw = right.number_input(
        "Water salinity (ECw, dS/m)", min_value=0.0, step=0.1, value=source.get("ecw_ds_m"),
        key=f"{key}/ecw", help=ECW_HELP,
    )

    assigned = st.multiselect(
        "Which fields does this source irrigate?", list(field_ids),
        default=[field["_key"] for field in fields if selected and field.get("source_id") == selected["id"]],
        format_func=field_ids.__getitem__, key=f"{key}/assignments",
        help="Each field uses one source. Selecting a field already assigned elsewhere moves it to this source.",
    )
    if fields:
        reassigned = [
            field["id"] for field in fields
            if field["_key"] in assigned and field.get("source_id") not in (None, source.get("id"))
        ]
        if reassigned:
            st.caption(plain_text(f"Saving will move these fields to this source: {', '.join(reassigned)}."))
    else:
        st.caption("Add your fields in Farm Setup. You can assign them here after saving this source.")

    with st.expander("Water source notes (optional)"):
        notes = st.text_area("Source notes", source.get("notes", ""), max_chars=2000, key=f"{key}/notes")

    if st.button("Save source changes" if selected else "Add water source", type="primary", key=f"{key}/save"):
        try:
            record = WaterSource(id=source_id, delivery_af=delivery, ecw_ds_m=ecw, source_type=source_type, notes=notes)
            save_source(scenario, record, selected, assigned)
        except ValueError as error:
            errors_panel(describe_errors(error))
        else:
            return True
    return False


add_revision = ui_key("add-source-revision")
with st.container(border=True):
    st.subheader("Water source details")
    add_key = ui_key(f"add-source/{st.session_state.get(add_revision, 0)}")
    if source_form(None, add_key):
        reset_entry(add_revision)

st.subheader("Saved water sources")
if sources:
    st.caption("Use the selector at the left of a row to edit or delete that water source.")
    table_revision = ui_key("saved-sources-table-revision")
    selection = selected_table_row([
        {
            "Water source ID": source["id"], "Source type": source["source_type"],
            "Expected farm delivery (AF)": source["delivery_af"], "Water ECw (dS/m)": source["ecw_ds_m"],
            "Fields irrigated": ", ".join(field["id"] for field in fields if field.get("source_id") == source["id"]),
        }
        for source in sources
    ], key=ui_key(f"saved-sources-table/{st.session_state.get(table_revision, 0)}"), column_config={
        "Expected farm delivery (AF)": st.column_config.NumberColumn(help=DELIVERY_HELP),
        "Water ECw (dS/m)": st.column_config.NumberColumn(help=ECW_HELP),
    })

    selected = sources[selection] if selection is not None else None
    editing = ui_key("editing-source")
    edit, delete, _ = st.columns([1.4, 1.4, 3])
    if edit.button("Edit water source", disabled=selected is None, width="stretch") and selected is not None:
        st.session_state[editing] = selected["_key"]
    delete_pressed = delete.button(
        "Delete water source", disabled=selected is None, width="stretch",
        help="Deleting a water source clears its field assignments.",
    )
    if delete_pressed and selected is not None:
        sources.remove(selected)
        for field in fields:
            if field.get("source_id") == selected["id"]:
                field["source_id"] = None
        st.session_state.pop(editing, None)
        reset_entry(table_revision)

    if selected and st.session_state.get(editing) == selected["_key"]:
        edit_revision = ui_key("edit-source-revision")
        edit_key = ui_key(f"edit-source/{selected['_key']}/{st.session_state.get(edit_revision, 0)}")
        with st.container(border=True):
            st.subheader(f"Edit {plain_text(selected['id'])}")
            if source_form(selected, edit_key) or st.button("Cancel source edit"):
                st.session_state.pop(editing, None)
                reset_entry(edit_revision)

    st.metric("Total expected farm delivery", volume(fsum(row["delivery_af"] for row in sources)), help=DELIVERY_HELP)
else:
    st.caption("Water sources and their field assignments appear here after you add them.")

unassigned = [field["id"] for field in fields if not field.get("source_id")]
if unassigned:
    st.warning(plain_text(f"Fields awaiting a water source: {', '.join(unassigned)}."))
st.page_link("pages/farm_setup.py", label="Return to Farm Setup", icon=":material/arrow_back:")

if st.button("Review and Calculate Farm Plan", type="primary"):
    _, issues = validate_scenario(scenario)
    if not workspace()["farm_name"].strip():
        issues.insert(0, "Enter a farm name in Farm Setup.")
    if issues:
        errors_panel(issues)
    elif workspace()["reviewed"]:
        st.switch_page("pages/farm_dashboard.py")
    else:
        workspace()["reviewed"] = True
        st.session_state.open_dashboard = True
        st.rerun()
