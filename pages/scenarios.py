# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from collections import Counter

import streamlit as st

from models.water_budget import evaluate_scenario
from schemas.scenarios import field_alternative
from ui.comparison import farm_water_budget, water_demand_chart
from ui.field_controls import choose_alternative_crop
from ui.shared import (
    CREDIT_HELP, EFF_HELP, ET_HELP, RAIN_HELP, YIELD_HELP, download_farm_plan, errors_panel,
    heading, plain_text, scenario_caption, selected_table_row,
)
from ui.state import (
    activate, baseline_id, identifier, save_scenario, scenario_ids, scenario_label, start_scenario_editor, ui_key,
    validate_scenario, validated_plan, workspace,
)

heading(
    "What-If Scenarios",
    "Save alternate crop or rainfall plans and compare them with your baseline.",
    banner="scenario-comparison",
)
state = workspace()
if not state["reviewed"]:
    st.info("Review your farm plan in Farm Setup before creating alternative scenarios.")
    if st.button("Go to Farm Setup", type="primary"):
        st.switch_page("pages/farm_setup.py")
    st.stop()

scenarios = state["scenarios"]
baseline_key = baseline_id()
baseline_name = scenarios[baseline_key]["name"]
scenario_caption(scenarios[baseline_key])
editor_key = ui_key("scenario-editor")
notice_key = ui_key("scenario-notice")
chart_revision = ui_key("scenario-chart-revision")


if st.button("Add new scenario", type="primary"):
    start_scenario_editor(baseline_key, identifier())
st.caption(plain_text(f"New scenarios start with the fields and water supply from {baseline_name}."))
if notice := st.session_state.get(notice_key):
    st.success(plain_text(f"{notice} is saved and included in the comparison."))
editor_location = st.container()

st.subheader("Whole-farm irrigation comparison")
ordered_ids = scenario_ids()
display_names = {key: scenario_label(key, include_name=True) for key in ordered_ids}
shown = st.multiselect(
    "Scenarios to plot", ordered_ids, default=ordered_ids, format_func=display_names.__getitem__,
    key=ui_key(f"compare/{st.session_state.get(chart_revision, 'initial')}"),
)
comparison = []
budgets = []
for scenario_id in shown:
    draft = scenarios[scenario_id]
    label = scenario_label(scenario_id)
    scenario, errors = validate_scenario(draft)
    if not scenario:
        with st.expander(f"{plain_text(scenario_label(scenario_id, include_name=True))} has incomplete inputs"):
            errors_panel(errors)
        comparison.append({
            "Scenario": label, "Scenario name": draft["name"], "Total irrigation (AF)": None,
            "Expected farm delivery (AF)": None,
            "Farm balance (AF)": None, "Known source shortfall (AF)": None, "Crop plan": "",
            "Water supply assessment": "Review field and water inputs", "Fields budgeted for leaching": "",
            "Source capacity for all-field leaching": "",
            "Fields with notes": None,
        })
        continue
    result = evaluate_scenario(scenario)
    if result.planned_shortfall_af > 1e-8:
        assessment = "At least one water source falls short of planned irrigation."
    elif result.planned_demand_af is None:
        assessment = "Planned irrigation is undetermined."
    else:
        assessment = "Expected delivery covers planned irrigation at every source."
    crops = Counter()
    for field in scenario.fields:
        crops[field.crop.label] += field.acres
    budgets.append({**farm_water_budget(label, result), "Scenario name": scenario.name})
    comparison.append({
        "Scenario": label, "Scenario name": scenario.name,
        "Total irrigation (AF)": result.planned_demand_af, "Expected farm delivery (AF)": result.field_supply_af,
        "Farm balance (AF)": result.planned_balance_af, "Known source shortfall (AF)": result.planned_shortfall_af,
        "Crop plan": " · ".join(f"{crop} ({acres:g} ac)" for crop, acres in sorted(crops.items())),
        "Water supply assessment": assessment,
        "Fields budgeted for leaching": ("All fields" if scenario.leaching_field_ids is None
                                         else ", ".join(scenario.leaching_field_ids) or "None selected"),
        "Source capacity for all-field leaching": "  ·  ".join(
            f"{source.source.id} · {source.leaching_status}" for source in result.sources
        ),
        "Fields with notes": result.salinity_concerns,
    })
if budgets:
    st.altair_chart(water_demand_chart(budgets, row_label="Scenario", details=("Scenario name",)), width="stretch")
    st.caption(
        "Bars show planned irrigation. Ticks mark expected farm delivery. Water remaining is the positive farm-wide balance. "
        "Check the source shortfall column to see whether an individual source falls short."
    )
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
    can_edit = selected not in (None, baseline_key)
    if edit.button("Edit scenario", disabled=not can_edit, width="stretch") and can_edit:
        start_scenario_editor(selected, selected)
    if delete.button("Delete scenario", disabled=not can_edit, width="stretch") and can_edit:
        del scenarios[selected]
        if st.session_state.get(editor_key, {}).get("template_id") == selected:
            st.session_state.pop(editor_key, None)
        st.session_state.pop(notice_key, None)
        st.session_state[chart_revision] = identifier()
        if selected == state["active_scenario_id"]:
            activate(baseline_key)
        st.rerun()
    open_pressed = open_setup.button(
        "Open in Farm Setup", disabled=selected is None, width="stretch",
        help="Use Farm Setup for detailed changes to fields and water sources.",
    )
    if open_pressed and selected is not None:
        activate(selected)
        st.switch_page("pages/farm_setup.py")
    if selected == baseline_key:
        st.caption("The baseline provides the starting plan for new scenarios.")
elif not shown:
    st.caption("Select a saved scenario to see its water budget.")

if editor := st.session_state.get(editor_key):
    template, errors = validate_scenario(scenarios[editor["template_id"]])
    editing_saved = editor["id"] in scenarios
    number = scenarios[editor["id"]]["number"] if editing_saved else state["next_scenario_number"]
    with editor_location.container(border=True):
        st.subheader("Edit scenario" if editing_saved else "New scenario")
        st.caption(f"Scenario {number}")
        key = ui_key(f"scenario-form/{editor['key']}")
        if not template:
            errors_panel(errors)
            st.caption("Open the starting plan in Farm Setup and complete its field and water inputs.")
        else:
            name = st.text_input(
                "Scenario name", template.name if editing_saved else "", max_chars=120,
                placeholder="e.g. Dry year or wheat and barley rotation", key=f"{key}/name",
            ).strip()
            focus = editor["field_id"]
            editable_fields = [field for field in template.fields if focus is None or field.id.casefold() == focus]
            if focus and editable_fields:
                st.caption(plain_text(f"Editing {editable_fields[0].id}. Other fields retain their saved inputs."))
            else:
                st.caption("Change crops, seasonal crop water use, or effective precipitation for this scenario.")
            if len(editable_fields) > 1:
                with st.expander("Set the same effective precipitation for all fields (optional)"):
                    rainfall = st.number_input(
                        "Effective precipitation to apply (in)", min_value=0.0, step=0.1, value=None,
                        key=f"{key}/bulk-rain", help=RAIN_HELP,
                    )
                    if st.button("Apply to all fields", disabled=rainfall is None):
                        editor["rain_default"] = rainfall
                        editor["rain_revision"] = identifier()
            revised = {}
            for index, field in enumerate(editable_fields):
                field_col, crop_col, et_col, rain_col = st.columns([1.6, 2.3, 1.7, 2], vertical_alignment="bottom")
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
                rain = rain_col.number_input(
                    f"Expected effective precipitation for {plain_text(field.id)} (in)", min_value=0.0, step=0.1,
                    value=editor.get("rain_default", field.effective_rain_in), help=RAIN_HELP,
                    key=f"{key}/{index}/rain/{editor.get('rain_revision', 'initial')}",
                )
                with st.expander(f"Advanced settings for {plain_text(field.id)} (optional)"):
                    goal, efficiency, credit = st.columns(3)
                    yield_goal = goal.number_input(
                        "Desired relative yield (%)", min_value=min(1.0, field.desired_yield_pct), max_value=100.0,
                        value=field.desired_yield_pct, step=1.0, help=YIELD_HELP, key=f"{key}/{index}/yield",
                    )
                    application_efficiency = efficiency.number_input(
                        "Field application efficiency (%)", min_value=min(1.0, field.irrigation.efficiency_pct),
                        max_value=100.0, value=field.irrigation.efficiency_pct, step=0.5,
                        help=EFF_HELP, key=f"{key}/{index}/efficiency",
                    )
                    leaching_credit = credit.number_input(
                        "Effective leaching credit (%)", min_value=0.0, max_value=100.0,
                        value=field.leaching_credit_pct, step=1.0, help=CREDIT_HELP, key=f"{key}/{index}/credit",
                    )
                revised[field.id] = dict(
                    crop=crop, etc_in=etc, et_estimate=estimate, effective_rain_in=rain,
                    desired_yield_pct=yield_goal, efficiency_pct=application_efficiency, leaching_credit_pct=leaching_credit,
                )
            if st.button("Save scenario", type="primary", disabled=not name or not revised,
                         help="Save it to this session. Download the farm plan to reopen it later."):
                try:
                    changed_fields = [
                        field_alternative(field, **revised[field.id]) if field.id in revised else field
                        for field in template.fields
                    ]
                    saved = save_scenario(editor["id"], name, changed_fields, template.sources,
                                          leaching_field_ids=template.leaching_field_ids)
                except ValueError as error:
                    errors_panel([str(error)])
                else:
                    st.session_state.pop(editor_key, None)
                    st.session_state[notice_key] = scenario_label(saved.id, include_name=True)
                    st.session_state[chart_revision] = identifier()
                    st.rerun()
        if st.button("Cancel scenario edit"):
            st.session_state.pop(editor_key, None)
            st.rerun()

if st.button("Inspect fields across scenarios"):
    st.switch_page("pages/field_decisions.py")
plan, _ = validated_plan()
if plan:
    download_farm_plan(plan)
