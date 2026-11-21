# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from collections import Counter

import streamlit as st

from models.water_budget import evaluate_scenario
from schemas.farm import Scenario
from schemas.scenarios import field_alternative
from ui.comparison import water_demand_chart
from ui.field_controls import choose_alternative_crop
from ui.shared import ET_HELP, download_farm_plan, errors_panel, heading, plain_text, scenario_caption, selected_table_row
from ui.state import activate, as_draft, identifier, ui_key, validate_scenario, validated_plan, workspace

heading("Scenario Comparison", "Compare whole-farm water demand for your saved plan and alternative crop choices.")
scenario_caption()
state = workspace()
scenarios = state["scenarios"]
baseline_id = "baseline" if "baseline" in scenarios else next(iter(scenarios))
baseline_name = scenarios[baseline_id]["name"]
editor_key = ui_key("scenario-editor")
notice_key = ui_key("scenario-notice")
chart_revision = ui_key("scenario-chart-revision")


def start_editor(template_id, scenario_id):
    st.session_state[editor_key] = {"template_id": template_id, "id": scenario_id, "key": identifier()}


if st.button("Add new scenario", type="primary"):
    start_editor(baseline_id, identifier())
st.caption(plain_text(f"New scenarios start with the fields and water supply from {baseline_name}."))
if notice := st.session_state.get(notice_key):
    st.success(plain_text(f"{notice} is saved and included in the comparison."))
new_editor = st.container()

st.subheader("Whole-farm irrigation comparison")
scenario_ids = [baseline_id, *(key for key in scenarios if key != baseline_id)]
shown = st.multiselect(
    "Scenarios to plot", scenario_ids, default=scenario_ids, format_func=lambda key: scenarios[key]["name"],
    key=ui_key(f"compare/{st.session_state.get(chart_revision, 'initial')}"),
)
comparison = []
budgets = []
for scenario_id in shown:
    draft = scenarios[scenario_id]
    scenario, errors = validate_scenario(draft)
    if not scenario:
        with st.expander(f"{plain_text(draft['name'])} has incomplete inputs"):
            errors_panel(errors)
        comparison.append({
            "Scenario": draft["name"], "Total irrigation (AF)": None, "Expected farm delivery (AF)": None,
            "Farm balance (AF)": None, "Known source shortfall (AF)": None, "Crop plan": "",
            "Water supply assessment": "Review field and water inputs", "Fields with notes": None,
        })
        continue
    result = evaluate_scenario(scenario)
    crops = Counter()
    for field in scenario.fields:
        crops[field.crop.label] += field.acres
    budgets.append({
        "Plan": scenario.name, "Crop-only (AF)": result.complete_sum("crop_only_af"),
        "Extra leaching (AF)": result.complete_sum("added_leach_field_af"), "Delivery (AF)": result.field_supply_af,
    })
    comparison.append({
        "Scenario": scenario.name,
        "Total irrigation (AF)": result.field_demand_af, "Expected farm delivery (AF)": result.field_supply_af,
        "Farm balance (AF)": result.field_balance_af, "Known source shortfall (AF)": result.source_shortfall_af,
        "Crop plan": " · ".join(f"{crop} ({acres:g} ac)" for crop, acres in sorted(crops.items())),
        "Water supply assessment": result.allocation_conclusion, "Fields with notes": result.salinity_concerns,
    })
if budgets:
    st.altair_chart(water_demand_chart(budgets, row_label="Scenario"), width="stretch")
    st.caption("Bars show crop-only irrigation and additional leaching water. Ticks mark expected farm delivery.")
if comparison:
    unresolved = [row["Scenario"] for row in comparison if row["Total irrigation (AF)"] is None]
    if unresolved:
        st.warning(plain_text(f"Total demand is undetermined for {', '.join(unresolved)}."))
    st.caption("Use the selector at the left of a row to edit, open or delete that scenario.")
    selection = selected_table_row(
        comparison, key=ui_key(f"scenario-table/{hash(tuple(shown))}"),
        column_config={key: st.column_config.NumberColumn(format="%.1f")
                       for key in comparison[0] if key.endswith("(AF)")},
    )
    selected = shown[selection] if selection is not None else None
    edit, delete, open_setup, _ = st.columns([1, 1, 1.4, 3])
    can_edit = selected not in (None, baseline_id)
    if edit.button("Edit scenario", disabled=not can_edit, width="stretch") and can_edit:
        start_editor(selected, selected)
    if delete.button("Delete scenario", disabled=not can_edit, width="stretch") and can_edit:
        del scenarios[selected]
        if st.session_state.get(editor_key, {}).get("template_id") == selected:
            st.session_state.pop(editor_key, None)
        st.session_state.pop(notice_key, None)
        st.session_state[chart_revision] = identifier()
        if selected == state["active_scenario_id"]:
            activate(baseline_id)
        st.rerun()
    open_pressed = open_setup.button(
        "Open in Farm Setup", disabled=selected is None, width="stretch",
        help="Use Farm Setup and Water Supply for detailed changes.",
    )
    if open_pressed and selected is not None:
        activate(selected)
        st.switch_page("pages/farm_setup.py")
    if selected == baseline_id:
        st.caption("The baseline provides the starting plan for new scenarios.")
elif not shown:
    st.caption("Select a saved scenario to see its water budget.")

edit_editor = st.container()
if editor := st.session_state.get(editor_key):
    template, errors = validate_scenario(scenarios[editor["template_id"]])
    editing_saved = editor["id"] in scenarios
    location = edit_editor if editing_saved else new_editor
    with location.container(border=True):
        st.subheader("Edit scenario" if editing_saved else "New scenario")
        key = ui_key(f"scenario-form/{editor['key']}")
        if not template:
            errors_panel(errors)
            st.caption("Open the starting plan in Farm Setup and complete its field and water inputs.")
        else:
            name = st.text_input(
                "Scenario name", template.name if editing_saved else "", max_chars=120,
                placeholder="e.g. Wheat and barley rotation", key=f"{key}/name",
            ).strip()
            st.caption("Choose the crop for each field and review its seasonal water use. "
                       "The scenario starts with the saved field areas, soil salinity and water supply.")
            revised = []
            for index, field in enumerate(template.fields):
                field_col, crop_col, et_col = st.columns([2, 3, 2], vertical_alignment="bottom")
                field_col.markdown(f"**{plain_text(field.id)}**")
                field_col.caption(f"{field.acres:g} acres")
                with crop_col:
                    crop, estimate = choose_alternative_crop(
                        field, f"Crop · {plain_text(field.id)}", f"{key}/{index}/crop",
                    )
                etc = et_col.number_input(
                    f"Seasonal crop ET for {plain_text(field.id)} (in)", min_value=0.0, step=0.1,
                    value=estimate.etc_in if estimate else field.etc_in, help=ET_HELP,
                    key=f"{key}/{index}/et/{crop.id if crop else 'saved'}",
                )
                revised.append((field, crop, estimate, etc))
            if st.button("Save scenario", type="primary", disabled=not name,
                         help="Save it to this session. Download the farm plan to reopen it later."):
                if any(draft["name"].casefold() == name.casefold() and draft["id"] != editor["id"]
                       for draft in scenarios.values()):
                    st.error("Choose a unique scenario name.")
                else:
                    try:
                        changed_fields = [
                            field_alternative(field, crop=crop, etc_in=etc, et_estimate=estimate)
                            for field, crop, estimate, etc in revised
                        ]
                        saved = Scenario(id=editor["id"], name=name, fields=changed_fields, sources=template.sources)
                    except ValueError as error:
                        errors_panel([str(error)])
                    else:
                        scenarios[saved.id] = as_draft(saved)
                        st.session_state.pop(editor_key, None)
                        st.session_state[notice_key] = saved.name
                        st.session_state[chart_revision] = identifier()
                        st.rerun()
        if st.button("Cancel scenario edit"):
            st.session_state.pop(editor_key, None)
            st.rerun()

plan, _ = validated_plan()
if plan:
    download_farm_plan(plan)
