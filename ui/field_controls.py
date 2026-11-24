# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from copy import deepcopy

import streamlit as st

from data.catalog import CROPS, ET_EXAMPLES, METHODS
from schemas.farm import DEFAULT_DESIRED_YIELD_PCT
from ui.shared import (
    CREDIT_HELP, ECE_HELP, EFF_HELP, ET_HELP, RAIN_HELP, TARGET_ECE_HELP, YIELD_HELP,
    plain_text, ref_help, reference_link,
)
from ui.state import ui_key, workspace


def choose_alternative_crop(field, label, key):
    """Return the chosen crop and its ET starting point for a field comparison."""
    options = sorted((crop_id for crop_id in CROPS if crop_id != field.crop.id),
                     key=lambda crop_id: CROPS[crop_id].label)
    crop_id = st.selectbox(
        label, [None, *options], format_func=lambda option: CROPS[option].label if option else field.crop.label,
        key=key,
    )
    crop = CROPS.get(crop_id)
    estimate = ET_EXAMPLES.get(crop_id)
    return crop, estimate


def _show_reference(reference_id):
    ref = workspace()["references"].get(reference_id)
    if ref:
        st.caption(reference_link(ref))


def edit_parameters(row, *, include_et=False, key=None):
    key = key or ui_key(f"parameters/{row['_key']}")
    crop = row.get("crop")
    method = row.get("irrigation")
    if crop:
        crop_key = f"{key}/crop/{crop['id']}"
        preset = CROPS.get(crop["id"])
        if preset:
            st.caption(
                f"Crop catalog defaults · {preset.threshold_ds_m:g} dS/m threshold · "
                f"{preset.slope_pct_per_ds_m:g} percentage points per dS/m · {plain_text(crop['endpoint'])}"
            )
        _show_reference(crop.get("reference_id"))
        if crop["id"] == "custom":
            crop["label"] = st.text_input(
                "Custom crop name", crop.get("label", ""), max_chars=120, key=f"{crop_key}/custom-crop",
            )
            crop["endpoint"] = st.text_input(
                "Production endpoint", crop.get("endpoint", ""), max_chars=120, key=f"{crop_key}/endpoint",
                help="Enter what the coefficients describe, such as grain yield or shoot dry weight.",
            )
        for column, (name, label, origin, help_text) in zip(st.columns(2), (
            ("threshold_ds_m", "Crop threshold (dS/m)", "threshold_origin",
             "The highest soil salinity at which this model estimates no crop yield loss."),
            ("slope_pct_per_ds_m", "Yield-loss slope (percentage points per dS/m)", "slope_origin",
             "Percentage points of modeled yield lost for each extra dS/m of soil salinity above the crop threshold."),
        )):
            before = crop.get(name)
            value = column.number_input(
                label, min_value=0.0, step=0.1, value=before, key=f"{crop_key}/{name}",
                help=ref_help("maas-hoffman", help_text),
            )
            if crop["id"] == "custom":
                crop[origin] = "Custom parameter"
            elif value != before:
                crop[origin] = "Published default" if preset and value == getattr(preset, name) else "User override"
            crop[name] = value
            column.caption(crop.get(origin, "Published default"))
        if preset:
            def reset_crop():
                st.session_state[f"{crop_key}/threshold_ds_m"] = preset.threshold_ds_m
                st.session_state[f"{crop_key}/slope_pct_per_ds_m"] = preset.slope_pct_per_ds_m

            st.button("Reset crop coefficients to catalog defaults", key=f"{crop_key}/reset-crop", on_click=reset_crop)

    cols = st.columns(2)
    row["desired_yield_pct"] = cols[0].number_input(
        "Desired relative yield (%)", min_value=0.0, max_value=100.0,
        value=row.get("desired_yield_pct", DEFAULT_DESIRED_YIELD_PCT), step=1.0, key=f"{key}/yield", help=YIELD_HELP,
    )
    manual = cols[1].checkbox(
        "Set target ECe manually", value=row.get("target_ece_override", False), key=f"{key}/manual-target",
        help=TARGET_ECE_HELP,
    )
    if manual:
        row["target_ece_ds_m"] = cols[1].number_input(
            "Target soil ECe (dS/m)", min_value=0.0, step=0.1,
            value=row.get("target_ece_ds_m") if row.get("target_ece_override") else None,
            key=f"{key}/target", help=TARGET_ECE_HELP,
        )
    else:
        row["target_ece_ds_m"] = None
        cols[1].caption("The automatic leaching target uses the desired relative yield. At 100%, it equals the crop threshold.")
    row["target_ece_override"] = manual
    if include_et:
        row["etc_in"] = st.number_input(
            "Seasonal crop ET (in)", min_value=0.0, step=0.1, value=row.get("etc_in"),
            key=f"{key}/et", help=ET_HELP,
        )

    if method:
        method_key = f"{key}/method/{method['id']}"
        bounds = method.get("published_range_pct")
        if method["id"] == "custom":
            method["label"] = st.text_input(
                "Custom irrigation method name", method.get("label", ""), max_chars=120, key=f"{method_key}/custom",
            )
        if bounds:
            st.caption(f"Published range {bounds[0]:g}–{bounds[1]:g}% · midpoint {sum(bounds) / 2:g}%")
        _show_reference(method.get("reference_id"))
        before = method.get("efficiency_pct")
        value = st.number_input(
            "Field application efficiency (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=before, key=f"{method_key}/efficiency", help=EFF_HELP,
        )
        if method["id"] == "custom":
            method["efficiency_origin"] = "Custom parameter"
        elif value != before:
            method["efficiency_origin"] = (
                "Published default" if bounds and value == sum(bounds) / 2 else "User override"
            )
        method["efficiency_pct"] = value
        st.caption(method["efficiency_origin"])
        if bounds:
            def reset_efficiency():
                st.session_state[f"{method_key}/efficiency"] = sum(bounds) / 2

            st.button("Reset application efficiency to midpoint", key=f"{method_key}/reset-efficiency",
                      on_click=reset_efficiency)

    row["leaching_credit_pct"] = st.number_input(
        "Effective leaching credit (% of crop-only inefficiency)", min_value=0.0, max_value=100.0,
        step=5.0, value=row.get("leaching_credit_pct", 0.0), key=f"{key}/credit", help=CREDIT_HELP,
    )
    row["notes"] = st.text_area("Field notes (optional)", row.get("notes") or "", key=f"{key}/notes", max_chars=2000)


def field_inputs(selected, key):
    """Render the same field questions for a new or saved field."""
    record = deepcopy(selected) if selected else {}
    crop = record.get("crop", {})
    method = record.get("irrigation", {})
    ids, area, salinity = st.columns([2, 1, 1])
    record["id"] = ids.text_input(
        "Field ID", record.get("id", ""), placeholder="e.g. North Pivot", max_chars=120, key=f"{key}/id",
        help="Use one unique name or code you recognize for this field.",
    )
    record["acres"] = area.number_input(
        "Field area (acres)", min_value=0.0, step=1.0, value=record.get("acres"), key=f"{key}/acres",
    )
    record["current_ece_ds_m"] = salinity.number_input(
        "Soil salinity (ECe, dS/m)", min_value=0.0, step=0.1, value=record.get("current_ece_ds_m"),
        key=f"{key}/ece", help=ECE_HELP,
    )
    left, right = st.columns(2)
    crop_labels = {k: item.label for k, item in CROPS.items()}
    method_labels = {k: item.label for k, item in METHODS.items()}
    if crop and crop["id"] != "custom":
        crop_labels[crop["id"]] = crop["label"]
    if method and method["id"] != "custom":
        method_labels[method["id"]] = method["label"]
    crop_labels["custom"] = "Custom crop"
    method_labels["custom"] = "Custom method"
    crop_ids = sorted(crop_labels, key=lambda item: crop_labels[item])
    method_ids = list(method_labels)
    crop_id = left.selectbox(
        "Crop", crop_ids, index=crop_ids.index(crop["id"]) if crop else None,
        format_func=crop_labels.__getitem__, key=f"{key}/crop",
    )
    method_id = right.selectbox(
        "Irrigation method", method_ids, index=method_ids.index(method["id"]) if method else None,
        format_func=method_labels.__getitem__, key=f"{key}/method",
    )

    same_crop = crop_id == crop.get("id")
    estimate = record.get("et_estimate") if same_crop else None
    if not crop_id:
        record["crop"] = None
    elif not same_crop:
        record["crop"] = CROPS[crop_id].model_dump() if crop_id != "custom" else {"id": "custom", "label": ""}
        example = ET_EXAMPLES.get(crop_id)
        estimate = example.model_dump() if example else None
    if not method_id:
        record["irrigation"] = None
    elif method_id != method.get("id"):
        record["irrigation"] = METHODS[method_id].model_dump() if method_id != "custom" else {"id": "custom", "label": ""}
    record["et_estimate"] = estimate

    et, rain = st.columns(2)
    default_et = record.get("etc_in") if same_crop else (estimate["etc_in"] if estimate else None)
    record["etc_in"] = et.number_input(
        "Seasonal crop ET (in)", min_value=0.0, step=0.1, value=default_et,
        key=f"{key}/et/{crop_id}", help=ET_HELP,
    )
    if estimate:
        location = plain_text(estimate["location"])
        ref = workspace()["references"].get(estimate["reference_id"])
        source_label = "CSU Extension Table 1" if estimate["reference_id"] == "csu-seasonal-et" else "Source"
        source_link = f" {reference_link(ref, source_label)}" if ref else ""
        crop_group = " (spring grains)" if crop_id == "barley" and estimate["source_crop"] == "Spring grains" else ""
        et.caption(f"{location}{crop_group} starting estimate · {estimate['etc_in']:g} in. "
                   f"Adjust for your field.{source_link}")
    if crop_id == "corn_grain":
        et.caption("The grain-corn salinity response comes from a single cultivar on organic muck soil. "
                   "Review the coefficients in Advanced field settings for local use.")
    record["effective_rain_in"] = rain.number_input(
        "Effective rain (in, optional)", min_value=0.0, step=0.1, value=record.get("effective_rain_in", 0.0),
        key=f"{key}/rain", help=RAIN_HELP,
    )
    rain.caption("Leave at zero to budget without a rainfall credit.")

    custom_selected = "custom" in (crop_id, method_id)
    label = "Advanced field settings" if custom_selected else "Advanced field settings (optional)"
    with st.expander(label, expanded=custom_selected):
        if custom_selected:
            st.caption("Enter the parameters for any custom choices. The remaining settings are optional.")
        edit_parameters(record, key=f"{key}/advanced")

    return record
