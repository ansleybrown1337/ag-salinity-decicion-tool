# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from math import fsum

import streamlit as st

from data.catalog import CROPS, ET_EXAMPLES
from models.optimization import crop_option, optimize_crop_plan
from models.water_budget import WATER_TOLERANCE_AF, evaluate_scenario
from schemas.farm import Scenario
from schemas.scenarios import field_alternative
from ui.shared import ET_HELP, TARGET_ECE_HELP, errors_panel, heading, plain_text, source_rows, volume
from ui.state import (
    baseline_id, identifier, save_scenario, scenario_ids, scenario_label, ui_key, validate_scenario, workspace,
)


MODE = {True: "Require maintenance leaching", False: "Cover crop irrigation"}


def crop_key(crop):
    return (crop.id, crop.label.casefold(), crop.endpoint.casefold()) if crop.id == "custom" else (crop.id,)


def produce_options(plan, eligible, targets, quotes, alternative_et):
    sources = {source.id: source for source in plan.sources}
    options = {}
    for field in plan.fields:
        options[field.id] = []
        for crop in eligible[field.id]:
            key = crop_key(crop)
            changed = key != crop_key(field.crop)
            candidate = field_alternative(
                field, crop=crop if changed else None,
                etc_in=alternative_et[key] if changed else field.etc_in,
                et_estimate=ET_EXAMPLES.get(crop.id) if changed else None,
                target_ece_ds_m=targets[field.id],
            )
            expected_yield, price, unit = quotes[key]
            options[field.id].append(crop_option(candidate, sources[field.source_id], expected_yield, price, unit))
    return options


def reference_revenue(plan, quotes):
    sources = {source.id: source for source in plan.sources}
    return fsum(
        crop_option(field, sources[field.source_id], *quotes[crop_key(field.crop)]).gross_revenue for field in plan.fields
    )


heading(
    "Optimization",
    "Find crop plans with the highest estimated gross revenue under your assigned water supply.",
    banner="scenario-comparison",
)
st.info(
    "**Experimental research tool.** Results estimate gross crop revenue before production costs. "
    "They depend on your price, yield, crop and water assumptions."
)
state = workspace()
if not state["reviewed"]:
    st.write("Review a farm plan before running the optimizer.")
    if st.button("Go to Farm Setup", type="primary"):
        st.switch_page("pages/farm_setup.py")
    st.stop()

root = f"{state['epoch']}/optimization"
optimization = state.setdefault("optimization", {})
labels = {key: scenario_label(key, include_name=True) for key in scenario_ids()}
previous = optimization.get("starting-plan")
starting_id = st.selectbox(
    "Starting plan", list(labels), index=list(labels).index(previous) if previous in labels else 0,
    format_func=labels.__getitem__, key=f"{root}/plan",
)
optimization["starting-plan"] = starting_id
plan, issues = validate_scenario(state["scenarios"][starting_id])
if plan is None:
    errors_panel(issues)
    if st.button("Open What-If Scenarios"):
        st.switch_page("pages/scenarios.py")
    st.stop()
baseline, _ = validate_scenario(state["scenarios"][baseline_id()])
key = f"{root}/{starting_id}"
plan_settings = optimization.setdefault("plans", {}).setdefault(starting_id, {})
settings = plan_settings.setdefault("inputs", {})

st.subheader("Crops and soil targets by field")
st.caption(
    "Select crops you would consider on each field. Selecting just one locks that field to that crop. "
    "Both runs use the same soil target across crop choices."
)
eligible, selections, targets, priced = {}, {}, {}, {}
replacement_keys = set()
for field in plan.fields:
    current_key = crop_key(field.crop)
    choices = {crop_key(crop): crop for crop in CROPS.values()}
    choices[current_key] = field.crop
    key_field = f"field/{field.id}"
    crops_col, target_col = st.columns([3, 2])
    field_label = plain_text(field.id)
    choices_labels = {crop_id: crop.label for crop_id, crop in choices.items()}
    selected_keys = crops_col.multiselect(
        f"Eligible crops for {field_label}", list(choices),
        default=[option for option in settings.get(f"{key_field}/eligible", [current_key]) if option in choices],
        format_func=choices_labels.__getitem__, key=f"{key}/{key_field}/crops",
    )
    settings[f"{key_field}/eligible"] = selected_keys
    selections[field.id] = selected_keys
    eligible[field.id] = [choices[option] for option in selected_keys]
    priced.update((option, choices[option]) for option in selected_keys)
    priced[current_key] = field.crop
    replacement_keys.update(option for option in selected_keys if option != current_key)
    target = target_col.number_input(
        f"Soil salinity target for {field_label} (dS/m)", min_value=0.0,
        value=settings.get(f"{key_field}/fixed-target", field.target_ece_ds_m),
        step=0.1, key=f"{key}/{key_field}/target", help=TARGET_ECE_HELP,
    )
    settings[f"{key_field}/fixed-target"] = targets[field.id] = target
if baseline:
    for field in baseline.fields:
        priced.setdefault(crop_key(field.crop), field.crop)

st.subheader("Crop prices and yields")
st.caption(
    "Enter expected yield per acre without salinity stress and the sale price for the same unit. "
    "Use values consistent with the crop’s production endpoint. The starting crop keeps its saved seasonal ET."
)
quotes, alternative_et = {}, {}
for crop_id, crop in sorted(priced.items(), key=lambda item: item[1].label.casefold()):
    st.markdown(f"**{plain_text(crop.label)}**")
    st.caption(f"Production endpoint · {plain_text(crop.endpoint)}")
    unit_col, yield_col, price_col, et_col = st.columns(4)
    key_crop = f"crop/{crop_id}"
    previous_yield, previous_price, previous_unit = settings.get(key_crop, (None, None, ""))
    unit = unit_col.text_input(
        f"Sale unit for {plain_text(crop.label)}", previous_unit, placeholder="e.g. bu or dry ton",
        max_chars=30, key=f"{key}/{key_crop}/unit",
    ).strip()
    expected_yield = yield_col.number_input(
        f"Expected yield per acre for {plain_text(crop.label)}", min_value=0.0, step=1.0,
        value=previous_yield, key=f"{key}/{key_crop}/yield",
    )
    price = price_col.number_input(
        f"Sale price ($/unit) for {plain_text(crop.label)}", min_value=0.0, step=0.01,
        value=previous_price, key=f"{key}/{key_crop}/price",
    )
    settings[key_crop] = quotes[crop_id] = (expected_yield, price, unit)
    if crop_id in replacement_keys:
        preset = ET_EXAMPLES.get(crop.id)
        et = et_col.number_input(
            f"Alternative seasonal ET for {plain_text(crop.label)} (in)", min_value=0.0, step=0.1,
            value=settings.get(f"{key_crop}/alternative-et", preset.etc_in if preset else None),
            key=f"{key}/{key_crop}/et", help=ET_HELP,
        )
        settings[f"{key_crop}/alternative-et"] = alternative_et[crop_id] = et

require_leaching = st.checkbox(
    "Require maintenance leaching on every field", value=settings.get("require-leaching", True), key=f"{key}/require",
    help="The selected rule is shown first. Both runs maximize gross revenue using the same crop and price inputs.",
)
settings["require-leaching"] = require_leaching
signature = (plan, baseline, selections, targets, quotes, alternative_et)
if st.button("Run optimization", type="primary"):
    plan_settings.pop("run", None)
    issues = [f"Select at least one eligible crop for {field_id}." for field_id, crops in eligible.items() if not crops]
    issues.extend(f"Enter a positive soil salinity target for {field_id}." for field_id, target in targets.items() if not target)
    issues.extend(
        f"Enter a sale unit, expected yield and price for {priced[crop_id].label}."
        for crop_id, (expected_yield, price, unit) in quotes.items() if expected_yield is None or price is None or not unit
    )
    issues.extend(f"Enter alternative seasonal ET for {priced[crop_id].label}."
                  for crop_id, etc in alternative_et.items() if etc is None)
    if issues:
        errors_panel(issues)
    else:
        try:
            with st.spinner("Comparing feasible crop plans…"):
                candidates = produce_options(plan, eligible, targets, quotes, alternative_et)
                results = {rule: optimize_crop_plan(candidates, plan.sources, require_leaching=rule) for rule in MODE}
                starting_revenue = reference_revenue(plan, quotes)
                baseline_revenue = reference_revenue(baseline, quotes) if baseline and baseline.id != plan.id else None
        except (ValueError, OverflowError) as error:
            errors_panel([str(error)])
        else:
            plan_settings["run"] = (signature, results, starting_revenue, baseline_revenue)

run = plan_settings.get("run")
if run is None:
    st.stop()
if run[0] != signature:
    st.caption("Run optimization again to compare plans using the updated inputs.")
    st.stop()

_, results, starting_revenue, baseline_revenue = run
st.subheader("Compare results")
st.caption(
    "Estimated revenue uses salinity-related yield loss at the entered soil salinity. "
    "Water feasibility applies to each assigned source. Maintenance estimates assume adequate drainage."
)
st.metric(
    "Starting plan estimated gross revenue", f"${starting_revenue:,.0f}",
    help="A common benchmark using your price and yield inputs and assuming full crop irrigation.",
)
starting_sources = evaluate_scenario(plan).sources
crop_short_sources = [source.source.id for source in starting_sources
                      if source.crop_only_af - source.source.delivery_af > WATER_TOLERANCE_AF]
if crop_short_sources:
    st.caption(
        "Starting-plan revenue assumes full crop irrigation. Expected delivery falls short of crop demand at "
        f"{plain_text(', '.join(crop_short_sources))}."
    )
if baseline_revenue is not None:
    st.metric("Baseline estimated gross revenue", f"${baseline_revenue:,.0f}")
order = (require_leaching, not require_leaching)
optimized_fields, farm_results = {}, {}
for column, rule in zip(st.columns(2), order):
    column.subheader(MODE[rule])
    result = results[rule]
    if not result.options:
        with column:
            errors_panel(result.diagnostics)
    else:
        fields = optimized_fields[rule] = [option.result.field for option in result.options]
        irrigation_plan = Scenario(id="optimization-result", name=MODE[rule], fields=fields, sources=plan.sources)
        farm_result = farm_results[rule] = evaluate_scenario(irrigation_plan)
        column.metric(
            "Estimated gross revenue", f"${result.gross_revenue:,.0f}",
            delta=f"${result.gross_revenue - starting_revenue:+,.0f} vs. starting plan",
        )
        extras = [source.extra_leaching_af for source in farm_result.sources]
        extra_leaching = fsum(extras) if None not in extras else None
        gaps = [source.leaching_gap_af for source in farm_result.sources]
        gap = fsum(gaps) if None not in gaps else None
        column.caption(
            f"Extra irrigation needed for leaching {volume(extra_leaching)} · "
            f"Leaching gap across sources {volume(gap)}"
        )

for rule, farm_result in farm_results.items():
    result = results[rule]
    source_results = {source.source.id: source for source in farm_result.sources}
    with st.expander(f"{MODE[rule]} · field and water details", expanded=rule == require_leaching):
        st.dataframe([
            {
                "Field": option.result.field.id, "Crop": option.result.field.crop.label,
                "Soil target (dS/m)": option.result.field.target_ece_ds_m,
                "Estimated yield (%)": option.result.current_yield_pct, "Yield per acre": option.yield_per_acre,
                "Sale unit": option.unit, "Estimated gross revenue ($)": option.gross_revenue,
                "Maintenance leaching": source_results[option.result.source.id].field_leaching_status(option.result),
                "Model notes": " ".join(option.result.warnings),
            }
            for option in result.options
        ], hide_index=True)
        st.dataframe(source_rows(farm_result), hide_index=True, column_order=[
            "Source ID", "Expected farm delivery (AF)", "Crop-only irrigation (AF)", "Extra leaching needed (AF)",
            "Leaching gap (AF)", "Leaching coverage",
        ])

if optimized_fields:
    st.subheader("Save a result")
    selected = st.selectbox(
        "Result to save", list(optimized_fields), index=0 if require_leaching in optimized_fields else None,
        format_func=MODE.__getitem__, key=f"{key}/save-mode",
    )
    name = st.text_input(
        "Optimized scenario name", max_chars=120, key=f"{key}/save-name",
        placeholder="e.g. Optimized crop plan with maintenance leaching",
    ).strip()
    st.caption("The saved scenario carries the crop and water inputs. Prices and yield assumptions stay in this session.")
    if st.button("Save as what-if scenario", type="primary", disabled=selected is None or not name):
        try:
            saved = save_scenario(identifier(), name, optimized_fields[selected], plan.sources)
        except ValueError as error:
            errors_panel([str(error)])
        else:
            st.session_state[ui_key("scenario-notice")] = scenario_label(saved.id, include_name=True)
            st.session_state[ui_key("scenario-chart-revision")] = identifier()
            st.switch_page("pages/scenarios.py")
