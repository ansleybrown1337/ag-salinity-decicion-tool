# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import altair as alt
import pandas as pd
import streamlit as st

from config.branding import BROWN, DARK_GREEN, LIGHT_GREEN
from models.water_budget import evaluate_scenario
from reports.pdf_report import management_report
from ui.field_controls import choose_field
from ui.shared import (
    DELIVERY_HELP, ECE_HELP, ESTIMATED_YIELD_HELP, GROSS_DEMAND_HELP, LR_HELP, NET_DEFICIT_HELP,
    TARGET_ECE_HELP, YIELD_HELP,
    current_scenario, download_farm_plan, errors_panel, field_rows, heading, plain_text, results_csv,
    scenario_caption, source_rows, volume,
)
from ui.state import ui_key, validated_plan, workspace

heading("Farm Dashboard", banner="farm-dashboard")
state = workspace()
with st.container(border=True):
    st.subheader("How to use this tool")
    st.markdown(
        "1. **Add your fields in Farm Setup.** Enter the area, crop, soil salinity, and irrigation method for each field.\n"
        "2. **Add water sources and assign fields.** Enter each source’s expected delivery and salinity, "
        "then select the fields it irrigates.\n"
        "3. **Review your farm plan.** Select **Review and Calculate Farm Plan** to see where irrigation demand "
        "may exceed delivery."
    )
    if st.button("Go to Farm Setup", type="secondary" if state["reviewed"] else "primary"):
        st.switch_page("pages/farm_setup.py")

if not state["reviewed"]:
    st.stop()

scenario_caption()
scenario = current_scenario()
if scenario is None:
    st.stop()
result = evaluate_scenario(scenario)
if result.source_shortfall_af > 1e-8:
    qualifier = "at least " if result.field_demand_af is None else ""
    st.warning(f"{result.allocation_conclusion} Assigned-source shortfall totals "
               f"{qualifier}{volume(result.source_shortfall_af)}.")
else:
    st.info(result.allocation_conclusion)

st.caption("Use Field Decisions to try a change on one field. Use Scenario Comparison to compare plans for the whole farm.")
st.page_link("pages/scenarios.py", label="Compare whole-farm plans")

field_count = len(result.fields)
field_label = "field" if field_count == 1 else "fields"
metrics = (
    ("Farm area", f"{result.acres:,.1f} ac · {field_count} {field_label}", None),
    ("Expected farm delivery", volume(result.field_supply_af), DELIVERY_HELP),
    ("Net crop water deficit", volume(result.net_crop_af), NET_DEFICIT_HELP),
    ("Extra field water for maintenance", volume(result.complete_sum("added_leach_field_af")),
     "Extra water to apply beyond the crop-only irrigation budget to help keep soil salinity at the target."),
    ("Total field irrigation demand", volume(result.field_demand_af), GROSS_DEMAND_HELP),
    ("Combined field balance", volume(result.field_balance_af, signed=True),
     "Total expected farm delivery minus total field irrigation demand. A surplus at one source "
     "can coexist with a shortfall at another."),
)
for columns, entries in ((st.columns(3), metrics[:3]), (st.columns(3), metrics[3:])):
    for column, (label, value, help_text) in zip(columns, entries):
        column.metric(label, value, help=help_text)

if result.field_demand_af is not None:
    st.caption(
        f"Field demand ranges from {volume(result.complete_sum('all_credit_field_af'))} at full effective "
        f"leaching credit to {volume(result.complete_sum('zero_credit_field_af'))} at zero credit, "
        "holding other inputs fixed. Use the source assessments to identify constrained fields."
    )
    largest = max(result.fields, key=lambda row: row.field_af)
    st.write(f"**Largest field demand** · {plain_text(largest.field.id)} ({volume(largest.field_af)}).")
if result.salinity_concerns:
    st.write(f"**Fields with salinity or model notes** · {result.salinity_concerns}. Review the field table.")

st.subheader("Demand by water source")
sources = source_rows(result)
chart_rows = [
    {"Source": row.source.id, "Measure": title, "Volume (AF)": value}
    for row in result.sources
    for title, value in (("Expected farm delivery", row.source.delivery_af),
                         ("Estimated demand" if row.demand_af is not None else "Known demand only",
                          row.known_demand_af))
]
measure_colors = {"Expected farm delivery": LIGHT_GREEN, "Estimated demand": BROWN, "Known demand only": DARK_GREEN}
measures = [key for key in measure_colors if any(row["Measure"] == key for row in chart_rows)]
source_chart = alt.Chart(pd.DataFrame(chart_rows)).mark_bar(size=13).encode(
    y=alt.Y("Source:N", title="Source ID"),
    yOffset="Measure:N",
    x=alt.X("Volume (AF):Q", title="Acre-feet"),
    color=alt.Color("Measure:N", scale=alt.Scale(
        domain=measures, range=[measure_colors[measure] for measure in measures],
    ), legend=alt.Legend(orient="top"), title=None),
    tooltip=["Source", "Measure", alt.Tooltip("Volume (AF):Q", format=",.1f")],
).properties(height=alt.Step(34))
st.altair_chart(source_chart, width="stretch")
st.dataframe(sources, hide_index=True, width="stretch", column_config={
    key: st.column_config.NumberColumn(format="%.1f") for key in sources[0] if key.endswith("(AF)")
})
st.page_link("pages/farm_setup.py", label="Manage water sources in Farm Setup")

st.subheader("Field results")
rows = field_rows(result)
column_help = {
    "Current ECe (dS/m)": ECE_HELP,
    "Current relative yield (%)": ESTIMATED_YIELD_HELP,
    "Desired yield (%)": YIELD_HELP,
    "Target ECe (dS/m)": TARGET_ECE_HELP,
    "LR (%)": LR_HELP,
    "Gross field depth (in)": GROSS_DEMAND_HELP,
    "Gross field volume (AF)": GROSS_DEMAND_HELP,
}
st.dataframe(
    rows, hide_index=True, width="stretch", height=min(560, 37 + 35 * len(rows)),
    column_config={
        key: st.column_config.NumberColumn(
            format="%.2f" if key.endswith("(dS/m)") else "%.1f", help=column_help.get(key),
        )
        for key in rows[0] if key.endswith(("(dS/m)", "(%)", "(AF)", "(ac)", "(in)"))
    },
)
st.page_link("pages/farm_setup.py", label="Edit or delete a saved field")
field = choose_field("Open a field analysis")
if st.button("Go to Field Decisions", key=ui_key("open-field")):
    st.session_state.selected_field = field["_key"]
    st.switch_page("pages/field_decisions.py")

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
