# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from models.water_budget import evaluate_scenario
from reports.pdf_report import management_report
from schemas.farm import report_filename
from ui.shared import download_farm_plan, errors_panel, heading
from ui.state import scenario_label, validated_plan, workspace


heading(
    "Download Full Report",
    "Download the farm management report, or save the farm plan and optimization history to reopen later.",
    banner="farm-dashboard",
)
plan, errors = validated_plan()
if plan is None:
    st.write("Complete Farm Setup before downloading a report or farm plan.")
    if workspace()["reviewed"]:
        errors_panel(errors)
    if st.button("Go to Farm Setup", type="primary"):
        st.switch_page("pages/farm_setup.py")
    st.stop()

st.subheader("Full report (PDF)")
scenarios = {scenario.id: scenario for scenario in plan.scenarios}
labels = {key: scenario_label(key, include_name=True) for key in scenarios}
scenario_id = st.selectbox(
    "Plan for the management report", list(scenarios), index=list(scenarios).index(plan.active_scenario_id),
    format_func=labels.__getitem__, key=f"{workspace()['epoch']}/report-plan",
)
scenario = scenarios[scenario_id]
runs = plan.optimization.runs if plan.optimization else ()
if runs:
    run_label = "comparison" if len(runs) == 1 else "comparisons"
    st.caption(f"The PDF includes the selected farm plan’s management report and {len(runs)} optimization {run_label}.")
else:
    st.caption("The PDF includes the selected farm plan’s management report. Completed optimization runs appear here when available.")
st.download_button(
    "Download Full Report (PDF)",
    lambda: management_report(plan.farm_name, plan.planning_year, plan.notes, scenario,
                              evaluate_scenario(scenario), plan.references, optimization_runs=runs),
    file_name=report_filename("full-report"), mime="application/pdf", on_click="ignore", type="primary",
)

st.subheader("Farm plan and optimization history (JSON)")
st.caption("Upload this file in Farm Setup to restore your saved plans, optimization inputs, and completed comparisons.")
download_farm_plan(plan)
