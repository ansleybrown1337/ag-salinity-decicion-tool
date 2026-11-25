# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import datetime
from math import fsum

import streamlit as st

from config.branding import VERSION
from data.catalog import CROPS, ET_EXAMPLES
from models.optimization import MODE, crop_option, optimize_crop_plan
from schemas.farm import OptimizationOutcome, OptimizationQuote, OptimizationRun, OptimizationSettings, Scenario, crop_key
from schemas.scenarios import field_alternative
from ui.optimization import show_history
from ui.shared import ET_HELP, errors_panel, heading, plain_text
from ui.state import (
    baseline_id, identifier, scenario_ids, scenario_label, validate_scenario, workspace,
)


def produce_options(plan, eligible, quotes, alternative_et):
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
                use_crop_threshold=True,
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
editor_key = f"{root}/{optimization.get('inputs-revision', 'inputs')}"
labels = {key: scenario_label(key, include_name=True) for key in scenario_ids()}
previous = optimization.get("starting-plan")
starting_id = st.selectbox(
    "Starting plan", list(labels), index=list(labels).index(previous) if previous in labels else 0,
    format_func=labels.__getitem__, key=f"{editor_key}/plan",
)
optimization["starting-plan"] = starting_id
plan, issues = validate_scenario(state["scenarios"][starting_id])
if plan is None:
    errors_panel(issues)
    if st.button("Open What-If Scenarios"):
        st.switch_page("pages/scenarios.py")
    show_history(state, root)
    st.stop()
baseline, _ = validate_scenario(state["scenarios"][baseline_id()])
key = f"{editor_key}/{starting_id}"
inputs_by_plan = optimization.setdefault("inputs", {})
previous_settings = inputs_by_plan.get(starting_id)
previous_quotes = previous_settings.quotes_by_crop if previous_settings else {}

st.subheader("Eligible crops and leaching by field")
st.caption(
    "Select crops you would consider on each field. Selecting just one locks that field to that crop. "
    "The optimizer uses each crop’s salinity threshold as its leaching target and estimates yield at the entered soil salinity."
)
leaching_keys = {field.id: f"{key}/field/{field.id}/leaching" for field in plan.fields}
all_leaching_key = f"{key}/all-leaching"
previous_fields = previous_settings.leaching_field_ids if previous_settings else plan.leaching_field_ids
for field_id, widget_key in leaching_keys.items():
    st.session_state.setdefault(widget_key, previous_fields is None or field_id in previous_fields)
st.session_state.setdefault(all_leaching_key, all(st.session_state[item] for item in leaching_keys.values()))


def select_all_leaching():
    for widget_key in leaching_keys.values():
        st.session_state[widget_key] = st.session_state[all_leaching_key]


def synchronize_all_leaching():
    st.session_state[all_leaching_key] = all(st.session_state[item] for item in leaching_keys.values())


st.checkbox("Require adequate leaching on every field", key=all_leaching_key, on_change=select_all_leaching)
eligible, selections, priced = {}, {}, {}
leaching_fields = []
replacement_keys = set()
for field in plan.fields:
    current_key = crop_key(field.crop)
    choices = {crop_key(crop): crop for crop in CROPS.values()}
    choices[current_key] = field.crop
    key_field = f"field/{field.id}"
    crops_col, leaching_col = st.columns([3, 2], vertical_alignment="bottom")
    field_label = plain_text(field.id)
    choices_labels = {crop_id: crop.label for crop_id, crop in choices.items()}
    default_crops = previous_settings.eligible.get(field.id, (current_key,)) if previous_settings else (current_key,)
    selected_keys = crops_col.multiselect(
        f"Eligible crops for {field_label}", list(choices),
        default=[option for option in default_crops if option in choices],
        format_func=choices_labels.__getitem__, key=f"{key}/{key_field}/crops",
    )
    selections[field.id] = selected_keys
    eligible[field.id] = [choices[option] for option in selected_keys]
    if current_key not in selected_keys:
        crops_col.caption(f"Starting crop excluded from the search: {plain_text(field.crop.label)}.")
    priced.update((option, choices[option]) for option in selected_keys)
    priced[current_key] = field.crop
    replacement_keys.update(option for option in selected_keys if option != current_key)
    if leaching_col.checkbox(
        f"Require adequate leaching for {field_label}", key=leaching_keys[field.id], on_change=synchronize_all_leaching,
    ):
        leaching_fields.append(field.id)
if baseline:
    for field in baseline.fields:
        priced.setdefault(crop_key(field.crop), field.crop)

st.subheader("Crop prices and yields")
st.caption(
    "Enter expected yield per acre without salinity stress and the sale price for the same unit. "
    "Use values consistent with the crop’s production endpoint. The starting crop keeps its saved seasonal ET."
)
with st.expander("USDA yield and price references"):
    st.markdown(
        "- [USDA NASS Quick Stats](https://www.nass.usda.gov/Quick_Stats/) has historical crop yields by county and state where available.\n"
        "- [USDA NASS Prices Received](https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Prices_Received_and_Prices_Received_Indexes/) "
        "links to monthly producer price estimates.\n"
        "- [USDA AMS Market News](https://www.ams.usda.gov/market-news) and "
        "[regional hay reports](https://www.ams.usda.gov/market-news/hay-reports) provide market prices by location and commodity."
    )
    st.caption("Match the crop, region and sale unit to your farm. Use farm records to estimate yield without salinity stress when available.")
quotes, alternative_et = {}, {}
updated_quotes = dict(previous_quotes)
for crop_id, crop in sorted(priced.items(), key=lambda item: item[1].label.casefold()):
    st.markdown(f"**{plain_text(crop.label)}**")
    st.caption(f"Production endpoint · {plain_text(crop.endpoint)}")
    unit_col, yield_col, price_col, et_col = st.columns(4)
    key_crop = f"crop/{crop_id}"
    quote = previous_quotes.get(crop_id, OptimizationQuote(crop=crop))
    unit = unit_col.text_input(
        f"Sale unit for {plain_text(crop.label)}", quote.unit, placeholder="e.g. bu or dry ton",
        max_chars=30, key=f"{key}/{key_crop}/unit",
    ).strip()
    expected_yield = yield_col.number_input(
        f"Expected yield per acre for {plain_text(crop.label)}", min_value=0.0, step=1.0,
        value=quote.expected_yield, key=f"{key}/{key_crop}/yield",
    )
    price = price_col.number_input(
        f"Sale price ($/unit) for {plain_text(crop.label)}", min_value=0.0, step=0.01,
        value=quote.price, key=f"{key}/{key_crop}/price",
    )
    quotes[crop_id] = (expected_yield, price, unit)
    et = quote.alternative_et_in
    if crop_id in replacement_keys:
        preset = ET_EXAMPLES.get(crop.id)
        et = et_col.number_input(
            f"Alternative seasonal ET for {plain_text(crop.label)} (in)", min_value=0.0, step=0.1,
            value=et if et is not None else (preset.etc_in if preset else None),
            key=f"{key}/{key_crop}/et", help=ET_HELP,
        )
        alternative_et[crop_id] = et
    updated_quotes[crop_id] = OptimizationQuote(
        crop=crop, unit=unit, expected_yield=expected_yield, price=price, alternative_et_in=et,
    )

settings = inputs_by_plan[starting_id] = OptimizationSettings(
    starting_plan_id=starting_id, eligible={field: tuple(crops) for field, crops in selections.items()},
    leaching_field_ids=leaching_fields, quotes=tuple(updated_quotes.values()),
)
history_key = f"{root}/history"
if st.button("Run optimization", type="primary"):
    issues = [f"Select at least one eligible crop for {field_id}." for field_id, crops in eligible.items() if not crops]
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
                candidates = produce_options(plan, eligible, quotes, alternative_et)
                outcomes = []
                for requires_leaching in (False, True) if leaching_fields else (False,):
                    required = leaching_fields if requires_leaching else ()
                    result = optimize_crop_plan(candidates, plan.sources, leaching_fields=frozenset(required))
                    optimized = Scenario(
                        id="optimization-result", name=MODE[requires_leaching],
                        fields=[option.result.field for option in result.options], sources=plan.sources,
                        leaching_field_ids=required,
                    ) if result.options else None
                    outcomes.append(OptimizationOutcome(
                        requires_leaching=requires_leaching, plan=optimized,
                        gross_revenue=result.gross_revenue if optimized else None, diagnostics=result.diagnostics,
                    ))
                reference = baseline if baseline and baseline.id != plan.id else None
                run = OptimizationRun(
                    id=identifier(), completed_at=datetime.now().astimezone(), model_version=VERSION,
                    settings=settings.model_copy(update={"quotes": tuple(updated_quotes[key] for key in quotes)}),
                    starting_plan=plan, starting_revenue=reference_revenue(plan, quotes),
                    baseline=reference, baseline_revenue=reference_revenue(reference, quotes) if reference else None,
                    outcomes=outcomes,
                )
        except (ValueError, OverflowError) as error:
            errors_panel([str(error)])
        else:
            optimization.setdefault("runs", []).append(run)
            st.session_state[history_key] = run.id

show_history(state, root, plan=plan, baseline=baseline, settings=settings)
