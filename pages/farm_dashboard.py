# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from models.water_budget import evaluate_scenario
from reports.pdf_report import management_report
from ui.comparison import farm_water_budget, field_yield_chart, water_demand_chart
from ui.shared import (
    DELIVERY_HELP, GROSS_DEMAND_HELP, download_farm_plan, errors_panel, field_rows, heading, plain_text,
    require_scenario, results_csv, scenario_caption, source_rows, volume,
)
from ui.state import baseline_id, validated_plan, workspace


heading("Farm Dashboard", "Review water supply and salinity for your baseline farm plan.", banner="farm-dashboard")
state = workspace()
if not state["reviewed"]:
    st.info("Complete Farm Setup and select **Review and Calculate Farm Plan** to see your results here.")
    if st.button("Go to Farm Setup", type="primary"):
        st.switch_page("pages/farm_setup.py")
    st.stop()

baseline = state["scenarios"][baseline_id()]
scenario_caption(baseline)
scenario = require_scenario(baseline)
if scenario is None:
    st.stop()
result = evaluate_scenario(scenario)

with st.container(horizontal=True):
    if st.button("Try a what-if scenario", type="primary"):
        st.switch_page("pages/scenarios.py")
    if st.button("Explore optimization"):
        st.switch_page("pages/optimization.py")

st.header("Water")
balance = result.field_balance_af
short_sources = [item for item in result.sources if item.shortfall_af > 1e-8]
source_shortfalls = ", ".join(
    f"{item.source.id} ({'at least ' if item.demand_af is None else ''}{volume(item.shortfall_af)})"
    for item in short_sources
)
source_note = f" Shortfalls by source include {plain_text(source_shortfalls)}." if short_sources else ""
if balance is None:
    st.warning("Total farm irrigation demand is undetermined because a field has no feasible estimate." + source_note)
elif balance < -1e-8:
    st.error(f"Expected farm delivery falls short of estimated farm demand by {volume(-balance)}." + source_note)
elif short_sources:
    st.warning("Expected delivery covers estimated demand farm-wide." + source_note)
else:
    st.success("Expected farm deliveries cover estimated demand at each assigned source.")
if short_sources:
    st.caption("Too little irrigation for crop water needs or leaching can increase the risk of yield loss or salt buildup.")

supply, demand, leaching = st.columns(3)
supply.metric("Expected farm delivery", volume(result.field_supply_af), help=DELIVERY_HELP)
demand.metric("Total irrigation demand", volume(result.field_demand_af), help=GROSS_DEMAND_HELP)
leaching.metric(
    "Extra irrigation for salinity leaching", volume(result.complete_sum("added_leach_field_af")),
    help="Water to apply beyond crop-only irrigation to help maintain the target soil salinity.",
)
st.altair_chart(water_demand_chart([farm_water_budget(scenario.name, result)], row_label="Farm plan"), width="stretch")

st.subheader("Can each source cover leaching?")
sources = source_rows(result)
st.dataframe(sources, hide_index=True, width="stretch", column_order=[
    "Source ID", "Expected farm delivery (AF)", "Crop-only irrigation (AF)", "Extra leaching needed (AF)",
    "Leaching gap (AF)", "Leaching coverage",
], column_config={
    key: st.column_config.NumberColumn(format="%.1f") for key in sources[0] if key.endswith("(AF)")
})
st.caption(
    "The leaching gap is the additional irrigation still needed after covering crop demand at that source. "
    "Coverage is a planning check for maintaining the stated soil target under the model’s drainage assumptions."
)

st.header("Salinity")
ordered_fields = sorted(result.fields, key=lambda item: item.current_yield_pct)
fields_with_loss = sum(item.current_yield_pct < 100 - 1e-9 for item in ordered_fields)
if fields_with_loss:
    st.warning(
        f"At the entered soil salinity, the model estimates yield loss in **{fields_with_loss} of {len(ordered_fields)} fields**."
    )
else:
    st.success("The model estimates no yield loss from salinity at the levels entered.")
st.caption("Estimated yield retained and lost at the entered root-zone salinity, as percentages of each crop’s potential.")
st.altair_chart(field_yield_chart(ordered_fields), width="stretch")
sources_by_id = {item.source.id: item for item in result.sources}
for item in ordered_fields:
    field = item.field
    name, estimates, details = st.columns([2, 3, 2], vertical_alignment="center")
    name.markdown(f"**{plain_text(field.id)}**")
    name.caption(plain_text(field.crop.label))
    estimates.caption(
        f"Current salinity {field.current_ece_ds_m:g} dS/m (ECe) · "
        f"{item.current_yield_pct:.1f}% yield retained · {100 - item.current_yield_pct:.1f}% lost"
    )
    status = sources_by_id[item.source.id].field_leaching_status(item)
    color = {"Maintenance leaching covered": "green", "Leaching gap": "red", "Field allocation needed": "orange"}
    estimates.badge(status, color=color.get(status, "gray"))
    if details.button("View field details", key=f"dashboard-field/{field.id}"):
        st.session_state.selected_field = field.id.casefold()
        st.switch_page("pages/field_decisions.py")

rows = field_rows(result)
with st.expander("Water-source details"):
    st.dataframe(
        sources, hide_index=True, width="stretch", column_config={
            key: st.column_config.NumberColumn(format="%.1f") for key in sources[0] if key.endswith("(AF)")
        },
    )
    st.caption("The source assessment applies to all fields assigned to that source. You decide how to allocate its water.")
    if balance is not None:
        st.caption(
            f"Estimated field demand ranges from {volume(result.complete_sum('all_credit_field_af'))} at full "
            f"effective leaching credit to {volume(result.complete_sum('zero_credit_field_af'))} at zero credit, "
            "holding other inputs fixed."
        )
    if st.button("Manage water sources in Farm Setup"):
        st.switch_page("pages/farm_setup.py")
with st.expander("Full field results"):
    st.dataframe(rows, hide_index=True, width="stretch", column_order=[
        column for column in rows[0] if column not in {"Desired yield (%)", "Target ECe (dS/m)", "Salinity and model notes"}
    ])

st.subheader("Downloads")
cols = st.columns(3)
plan, errors = validated_plan()
if plan:
    with cols[0]:
        download_farm_plan(plan)
else:
    with cols[0].expander("Resolve entries to download JSON"):
        errors_panel(errors)

if state["farm_name"].strip():
    report = management_report(state["farm_name"], state["planning_year"], state["notes"],
                               scenario, result, state["references"])
    cols[1].download_button(
        "Download Management Report (PDF)", report, "ag-salinity-management-report.pdf", "application/pdf",
    )
cols[2].download_button("Export Field Results (.csv)", results_csv(rows), "ag-salinity-field-results.csv", "text/csv")
