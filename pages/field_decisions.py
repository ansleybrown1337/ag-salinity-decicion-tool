# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from models.water_budget import evaluate_field, evaluate_scenario
from ui.comparison import water_demand_chart, yield_response_chart
from ui.shared import TARGET_ECE_HELP, errors_panel, heading, plain_text, target_basis
from ui.state import (
    baseline_id, describe_errors, field_model, field_names, identifier, scenario_ids, scenario_label, source_model,
    start_scenario_editor, ui_key, validate_scenario, workspace,
)


heading("Field Details", "Choose a field in the sidebar to see how it compares across saved plans.", banner="field-decisions")
with st.container(horizontal=True):
    if st.button("Back to What-If Scenarios", icon=":material/arrow_back:"):
        st.switch_page("pages/scenarios.py")
    if st.button("Back to Farm Dashboard", icon=":material/arrow_back:"):
        st.switch_page("pages/farm_dashboard.py")

names = field_names()
if not names:
    st.info("Add a field in Farm Setup to see its details.")
    if st.button("Go to Farm Setup", type="primary"):
        st.switch_page("pages/farm_setup.py")
    st.stop()

selected = st.session_state.get("selected_field")
if selected not in names:
    selected = next(iter(names))
field_name = plain_text(names[selected])
st.subheader(field_name)

state = workspace()
first = baseline_id()
ordered_ids = scenario_ids()
matches = {}
missing = []
for scenario_id in ordered_ids:
    draft = state["scenarios"][scenario_id]
    row = next((field for field in draft["fields"] if field["id"].casefold() == selected), None)
    if row is None:
        missing.append(scenario_label(scenario_id))
    else:
        matches[scenario_id] = (draft, row)

labels = {key: scenario_label(key) for key in matches}
shown = st.multiselect(
    "Plans to compare", list(matches), default=list(matches)[:3],
    format_func=labels.__getitem__,
    key=ui_key(f"field-plans/{selected}/{tuple(matches)}"),
)
if missing:
    st.caption(plain_text(f"Field ID not found in: {', '.join(missing)}."))

options = []
positions = []
coverage = {}
for scenario_id in shown:
    draft, row = matches[scenario_id]
    try:
        field = field_model(row)
        source = next((item for item in draft["sources"] if item["id"] == field.source_id), None)
        if source is None:
            raise ValueError(f"Assign {field.id} to a water source in Farm Setup.")
        result = evaluate_field(field, source_model(source))
    except ValueError as error:
        errors_panel([f"{scenario_label(scenario_id)}. {message}" for message in describe_errors(error)])
    else:
        label = labels[scenario_id]
        options.append((label, draft["name"], result))
        positions.append(0 if scenario_id == first else draft["number"])
        plan, _ = validate_scenario(draft)
        if plan is None:
            coverage[label] = "Maintenance coverage undetermined"
        else:
            farm_sources = evaluate_scenario(plan).sources
            source_result = next(item for item in farm_sources if item.source.id == result.source.id)
            coverage[label] = source_result.field_leaching_status(result)

if options:
    st.header("Yield response to salinity")
    st.altair_chart(yield_response_chart(options, scenario_positions=positions), width="stretch")
    st.caption(
        "The circle marks current soil salinity and the diamond marks the leaching target. "
        "Plans with the same crop salinity response can have overlapping curves. "
        "Changes to effective rainfall appear in the irrigation comparison."
    )
    st.caption("At 100% relative yield, the calculated target is the crop’s salinity threshold. "
               "See **Target basis** below for the value used in each plan.")

    st.header(f"Seasonal irrigation for {field_name}")
    st.altair_chart(water_demand_chart([
        {"Plan": label, "Scenario name": name, "Crop": result.field.crop.label,
         "Crop-only (AF)": result.crop_only_af, "Extra leaching (AF)": result.added_leach_field_af}
        for label, name, result in options
    ], row_label="Scenario", details=("Scenario name", "Crop")), width="stretch")
    undetermined = [label for label, _, result in options if result.field_af is None]
    if undetermined:
        st.warning(plain_text(f"Irrigation demand is undetermined for: {', '.join(undetermined)}."))

    st.subheader(f"{field_name} results by scenario")
    st.dataframe([
        {
            "Scenario": label, "Crop": result.field.crop.label, "Current salinity (dS/m)": result.field.current_ece_ds_m,
            "Crop threshold (dS/m)": result.field.crop.threshold_ds_m,
            "Leaching target (dS/m)": result.field.target_ece_ds_m, "Target basis": target_basis(result.field),
            "Total irrigation (AF)": result.field_af, "Scenario name": name,
            "Required drainage below roots (in)": result.depths.theoretical_leach_in if result.maintenance_assessable else None,
            "Maintenance leaching": coverage[label],
            "Estimated yield (%)": result.current_yield_pct, "Yield lost (%)": 100 - result.current_yield_pct,
            "Crop ET (in)": result.field.etc_in, "Effective precipitation (in)": result.field.effective_rain_in,
            "Water source": result.source.id, "Notes": " ".join(result.warnings),
        }
        for label, name, result in options
    ], hide_index=True, width="stretch", column_config={
        "Leaching target (dS/m)": st.column_config.NumberColumn(format="%.2f", help=TARGET_ECE_HELP),
        "Required drainage below roots (in)": st.column_config.NumberColumn(
            format="%.2f", help="Estimated effective drainage through the root zone needed for maintenance. "
                                "Extra applied irrigation also accounts for field losses and credited drainage.",
        ),
    })
elif not shown:
    st.info("Select a saved plan to see its field results.")

if state["reviewed"]:
    display_names = {key: scenario_label(key, include_name=True) for key in matches}
    editing_options = [key for key in matches if key != first]
    if first in matches:
        editing_options.insert(0, None)
    target = st.selectbox(
        "Scenario to edit", editing_options,
        format_func=lambda key: display_names[key] if key else "New scenario from baseline",
        key=ui_key(f"edit-field-scenario/{selected}/{tuple(editing_options)}"),
    )
    if st.button("Edit this field in a scenario", type="primary"):
        start_scenario_editor(target or first, target or identifier(), field_id=selected)
        st.switch_page("pages/scenarios.py")
if st.button("Edit farm inputs in Farm Setup"):
    st.switch_page("pages/farm_setup.py")
