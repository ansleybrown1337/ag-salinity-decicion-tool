# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from math import ceil

import streamlit as st

from data.catalog import REFERENCES
from models.water_budget import evaluate_field
from schemas.scenarios import field_alternative
from ui.comparison import water_demand_chart, yield_response_chart
from ui.field_controls import choose_alternative_crop, choose_field
from ui.shared import (
    CREDIT_HELP, EFF_HELP, ET_HELP, ESTIMATED_YIELD_HELP, GROSS_DEMAND_HELP, LR_HELP, TARGET_ECE_HELP, YIELD_HELP,
    errors_panel, heading, plain_text, reference_link, reset_entry, scenario_caption,
)
from ui.state import active, describe_errors, field_model, source_model, ui_key

heading("Field Decisions", "Compare a crop or irrigation change on one field before changing your farm plan.")
scenario_caption()
field_selector, crop_selector = st.columns(2)
with field_selector:
    row = choose_field("Field to analyze", st.session_state.get("selected_field"))
if not row:
    st.page_link("pages/farm_setup.py", label="Add fields in Farm Setup")
    st.stop()
st.session_state.selected_field = row["_key"]
preview_revision = ui_key(f"field-preview-revision/{row['_key']}")
key = ui_key(f"field-preview/{row['_key']}/{st.session_state.get(preview_revision, 0)}")

sources = {item["id"]: item for item in active()["sources"]}


def field_and_source(draft):
    field = field_model(draft)
    if field.source_id not in sources:
        raise ValueError(f"Assign {field.id} to a source in Water Supply.")
    return field, source_model(sources[field.source_id])


try:
    field, source = field_and_source(row)
except ValueError as error:
    errors_panel(describe_errors(error))
    st.page_link("pages/water_supply.py", label="Assign water sources")
    st.stop()

with crop_selector:
    crop, et_example = choose_alternative_crop(field, "Crop to try", f"{key}/crop")

st.caption(plain_text(
    f"{field.id} · {field.acres:g} acres · Current salinity {field.current_ece_ds_m:g} dS/m (ECe) · "
    f"{source.id}, water ECw {source.ecw_ds_m:g} dS/m"
))
saved_label = f"Saved · {field.crop.label}"
options = [(saved_label, field, evaluate_field(field, source))]
chart, controls = st.columns([3, 2])
with controls.container(border=True):
    st.subheader("Try a change")
    st.caption("The preview uses this field’s acreage, soil salinity, effective rain and water source. "
               "Changing the crop or yield goal recalculates the salinity target.")
    start_et = et_example.etc_in if et_example else field.etc_in
    etc = st.slider(
        "Seasonal crop ET (in)", 0.0, max(60.0, float(ceil(start_et))), start_et, step=0.1,
        key=f"{key}/et/{crop.id if crop else 'saved'}", help=ET_HELP,
    )
    if et_example:
        reference = reference_link(REFERENCES[et_example.reference_id], "CSU Extension Table 1")
        st.caption(f"{plain_text(et_example.location)} starting estimate · {start_et:g} in. {reference}")
    goal = st.slider(
        "Desired relative yield (%)", min(1.0, field.desired_yield_pct), 100.0,
        float(field.desired_yield_pct), step=1.0, key=f"{key}/goal", help=YIELD_HELP,
    )
    efficiency = st.slider(
        "Field application efficiency (%)", min(1.0, field.irrigation.efficiency_pct), 100.0,
        float(field.irrigation.efficiency_pct), step=0.5, key=f"{key}/efficiency", help=EFF_HELP,
    )
    credit = st.slider(
        "Effective leaching credit (%)", 0.0, 100.0, float(field.leaching_credit_pct), step=1.0,
        key=f"{key}/credit", help=CREDIT_HELP,
    )

trial = field_alternative(field, crop=crop, etc_in=etc, et_estimate=et_example, desired_yield_pct=goal,
                          efficiency_pct=efficiency, leaching_credit_pct=credit)
if trial != field:
    options.append((f"What-if · {trial.crop.label}", trial, evaluate_field(trial, source)))

with chart:
    st.subheader("Yield response to salinity")
    st.altair_chart(yield_response_chart(options), width="stretch")
    st.caption("Each curve shows yield relative to that crop’s potential. The circle marks current salinity "
               "and the diamond marks target salinity.")
    if len(options) == 2 and options[0][1].crop == trial.crop:
        st.caption("The curves overlap when the crop stays the same. Irrigation changes appear in the water budget.")

st.subheader("Seasonal irrigation by field")
other_fields = {draft["_key"]: draft for draft in active()["fields"] if draft["_key"] != row["_key"]}
shown = st.multiselect(
    "Additional fields to plot (optional)", list(other_fields), format_func=lambda option: other_fields[option]["id"],
    key=ui_key(f"field-chart-selection/{row['_key']}"),
    help="Add other saved fields to the chart. Use the × next to a field to remove it from the chart.",
)
bars = [(f"{field.id} · {plan}", result) for plan, _, result in options]
for selected in shown:
    try:
        extra_field, extra_source = field_and_source(other_fields[selected])
        bars.append((f"{extra_field.id} · Saved", evaluate_field(extra_field, extra_source)))
    except ValueError as error:
        errors_panel(describe_errors(error))

budgets = [
    {"Plan": label, "Crop-only (AF)": result.crop_only_af, "Extra leaching (AF)": result.added_leach_field_af}
    for label, result in bars
]
st.altair_chart(water_demand_chart(budgets, row_label="Field and option"), width="stretch")
st.caption("Crop-only irrigation includes application losses. The leaching segment shows the additional water "
           "needed beyond that budget.")
missing = [label for label, result in bars if result.field_af is None]
if missing:
    st.warning(plain_text(f"No feasible irrigation estimate for {', '.join(missing)}."))

st.dataframe([
    {
        "Plan": label, "Yield at current salinity (%)": result.current_yield_pct,
        "Target salinity (dS/m)": selected.target_ece_ds_m,
        "Leaching requirement (%)": result.lr * 100 if result.lr is not None else None,
        "Crop-only (AF)": result.crop_only_af, "Extra leaching (AF)": result.added_leach_field_af,
        "Total irrigation (AF)": result.field_af, "Notes": " ".join(result.warnings),
    }
    for label, selected, result in options
], hide_index=True, column_config={
    "Yield at current salinity (%)": st.column_config.NumberColumn(format="%.1f", help=ESTIMATED_YIELD_HELP),
    "Target salinity (dS/m)": st.column_config.NumberColumn(format="%.2f", help=TARGET_ECE_HELP),
    "Leaching requirement (%)": st.column_config.NumberColumn(format="%.1f", help=LR_HELP),
    "Total irrigation (AF)": st.column_config.NumberColumn(format="%.1f", help=GROSS_DEMAND_HELP),
})
if len(options) > 1 and st.button("Remove what-if row", help="Reset the crop and sliders to the saved field."):
    reset_entry(preview_revision)
st.page_link("pages/farm_setup.py", label="Edit or delete a saved field in Farm Setup")
st.page_link("pages/scenarios.py", label="Compare whole-farm scenarios")
