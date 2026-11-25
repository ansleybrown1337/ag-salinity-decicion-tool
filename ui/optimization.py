# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from models.optimization import MODE, crop_option, crop_shortfalls, excluded_starting_crops, reference_label
from models.water_budget import WATER_TOLERANCE_AF, evaluate_scenario
from reports.pdf_report import optimization_report
from schemas.farm import crop_key, report_filename
from ui.comparison import farm_water_budget, revenue_comparison_chart, water_demand_chart
from ui.shared import errors_panel, plain_text, source_rows, volume
from ui.state import identifier, save_scenario, scenario_label, ui_key


def show_history(state, root, *, plan=None, baseline=None, settings=None):
    runs = state.get("optimization", {}).get("runs", ())
    if not runs:
        return
    st.subheader("Compare results")
    labels = {
        run.id: f"Run {i} · {run.starting_plan.name} · {run.completed_at:%Y-%m-%d %H:%M:%S %z}"
        for i, run in enumerate(runs, 1)
    }
    run_id = st.selectbox("Optimization run", list(reversed(labels)), format_func=labels.__getitem__, key=f"{root}/history")
    run = next(item for item in runs if item.id == run_id)
    reference = baseline if plan and baseline and baseline.id != plan.id else None
    current_quotes = settings.quotes_by_crop if settings else {}
    if (run.starting_plan != plan or run.baseline != reference or settings is None
            or run.settings.eligible != settings.eligible or run.settings.leaching_field_ids != settings.leaching_field_ids
            or any(current_quotes.get(key) != value for key, value in run.settings.quotes_by_crop.items())):
        st.info("This comparison uses the inputs saved with the selected run. Run optimization to compare the current inputs.")
        starting_id = run.settings.starting_plan_id
        if starting_id in state["scenarios"] and st.button("Load this run’s inputs"):
            optimization = state["optimization"]
            optimization["inputs"][starting_id] = run.settings
            optimization["starting-plan"] = starting_id
            optimization["inputs-revision"] = identifier()
            st.rerun()

    st.caption(
        "Estimated gross revenue uses salinity-related yield loss at the entered soil salinity. "
        "Optimized plans must cover crop irrigation at each assigned source. The required-leaching plan also budgets "
        "leaching for the checked fields."
    )
    revenue_rows, water_rows = [], []
    if run.baseline:
        _reference_rows("Baseline", run.baseline, run.baseline_revenue, revenue_rows, water_rows)
    _reference_rows("Starting plan", run.starting_plan, run.starting_revenue, revenue_rows, water_rows)
    if excluded := excluded_starting_crops(run):
        entries = ", ".join(f"{field} ({crop})" for field, crop in excluded.items())
        st.warning(plain_text(f"Starting crops excluded from this search: {entries}."))

    optimized = {}
    for outcome in run.outcomes:
        label = MODE[outcome.requires_leaching]
        if outcome.plan is None:
            st.markdown(f"**{label}**")
            errors_panel(outcome.diagnostics)
            continue
        farm_result = evaluate_scenario(outcome.plan)
        optimized[outcome.requires_leaching] = (outcome.plan, farm_result)
        revenue_rows.append({"Plan": label, "Revenue": outcome.gross_revenue, "Benchmark": False})
        water_rows.append(farm_water_budget(label, farm_result))

    st.subheader("Estimated gross revenue")
    st.altair_chart(revenue_comparison_chart(revenue_rows), width="stretch")
    st.subheader("Irrigation budget")
    st.altair_chart(water_demand_chart(water_rows, row_label="Plan"), width="stretch")
    st.caption("The chart shows crop irrigation and the extra leaching water budgeted in each plan.")
    if not run.settings.leaching_field_ids:
        st.caption("Select at least one field for adequate leaching to compare a second optimized result.")
    if False in optimized:
        _all_field_coverage(optimized[False][1])
    if True in optimized:
        fields = ", ".join(run.settings.leaching_field_ids)
        st.success(plain_text(f"The constrained plan budgets adequate salinity leaching for {fields}."))
    if optimized:
        _crop_comparison(run, optimized)
        for rule, (optimized_plan, result) in optimized.items():
            _details(run, rule, optimized_plan, result)
        _save_scenario(run, optimized)

    st.subheader("Save a comparison report")
    st.download_button(
        "Download Optimization Comparison (PDF)",
        lambda: optimization_report(state["farm_name"], state["planning_year"], run),
        file_name=report_filename("optimization-comparison"), mime="application/pdf", on_click="ignore",
    )


def _reference_rows(name, scenario, revenue, revenue_rows, water_rows):
    result = evaluate_scenario(scenario)
    label = reference_label(name, result)
    shortfalls = crop_shortfalls(result)
    if shortfalls:
        amounts = ", ".join(f"{source} by {volume(gap)}" for source, gap in shortfalls.items())
        st.warning(plain_text(f"{name} is a full-irrigation benchmark. Crop water demand exceeds delivery at {amounts}."))
    revenue_rows.append({"Plan": label, "Revenue": revenue, "Benchmark": bool(shortfalls)})
    water_rows.append(farm_water_budget(label, result))


def _all_field_coverage(result):
    gaps = [f"{row.source.id} ({volume(row.leaching_gap_af)})" for row in result.sources
            if (row.leaching_gap_af or 0.0) > WATER_TOLERANCE_AF]
    unknown = [row.source.id for row in result.sources if row.leaching_gap_af is None]
    if gaps:
        st.warning(plain_text(f"The highest-revenue crops would need more water to cover leaching on all fields at "
                              f"{', '.join(gaps)}."))
    if unknown:
        st.info(plain_text(f"All-field leaching coverage is undetermined at {', '.join(unknown)}."))
    if not gaps and not unknown:
        st.success("The highest-revenue crop choices can also cover salinity leaching on every field.")


def _crop_comparison(run, optimized):
    st.subheader("Crop choices by field")
    plans = {"Starting crop": run.starting_plan}
    if run.baseline:
        plans = {"Baseline crop": run.baseline, **plans}
    plans.update((MODE[rule], scenario) for rule, (scenario, _) in optimized.items())
    crops = {label: {field.id: field.crop.label for field in scenario.fields} for label, scenario in plans.items()}
    st.dataframe([
        {
            "Field": field_id, **{label: fields.get(field_id) for label, fields in crops.items()},
            "Leaching required in the constrained run": field_id in run.settings.leaching_field_ids,
        }
        for field_id in dict.fromkeys(field_id for fields in crops.values() for field_id in fields)
    ], hide_index=True)


def _details(run, rule, plan, result):
    quotes = run.settings.quotes_by_crop
    sources = {row.source.id: row for row in result.sources}
    with st.expander(f"{MODE[rule]} · field and water details"):
        rows = []
        for field in plan.fields:
            source = sources[field.source_id]
            quote = quotes[crop_key(field.crop)]
            option = crop_option(field, source.source, quote.expected_yield, quote.price, quote.unit)
            rows.append({
                "Field": field.id, "Crop": field.crop.label, "Crop threshold (dS/m)": field.target_ece_ds_m,
                "Estimated yield (%)": option.result.current_yield_pct, "Yield per acre": option.yield_per_acre,
                "Sale unit": option.unit, "Estimated gross revenue ($)": option.gross_revenue,
                "Salinity leaching": source.field_leaching_status(option.result),
                "Model notes": " ".join(option.result.warnings),
            })
        st.dataframe(rows, hide_index=True)
        st.dataframe(source_rows(result), hide_index=True, column_order=[
            "Source ID", "Expected farm delivery (AF)", "Crop-only irrigation (AF)", "Planned irrigation (AF)",
            "Extra leaching needed (AF)", "Leaching gap (AF)", "Leaching coverage",
        ])
        st.caption("Source coverage shows delivery capacity for leaching on all assigned fields.")


def _save_scenario(run, optimized):
    st.subheader("Save result as a scenario")
    key = f"optimization-result/{run.id}"
    selected = st.selectbox("Result to save", list(optimized), index=None, format_func=MODE.__getitem__, key=f"{key}/mode")
    name = st.text_input("Optimized scenario name", max_chars=120, key=f"{key}/name",
                         placeholder="e.g. Optimized with salinity leaching").strip()
    st.caption("The scenario records the crop and irrigation plan. The farm JSON also records this run and its assumptions.")
    if st.button("Save as what-if scenario", type="primary", disabled=selected is None or not name):
        try:
            chosen, _ = optimized[selected]
            saved = save_scenario(identifier(), name, chosen.fields, chosen.sources,
                                  leaching_field_ids=chosen.leaching_field_ids)
        except ValueError as error:
            errors_panel([str(error)])
        else:
            st.session_state[ui_key("scenario-notice")] = scenario_label(saved.id, include_name=True)
            st.session_state[ui_key("scenario-chart-revision")] = identifier()
            st.switch_page("pages/scenarios.py")
