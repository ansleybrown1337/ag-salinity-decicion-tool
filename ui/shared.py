# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import csv
import re
from io import StringIO
from urllib.parse import quote

import streamlit as st

from data.catalog import REFERENCES
from schemas.farm import export_plan, farm_plan_filename
from ui.state import active, ui_key, validate_scenario, workspace

def ref_help(ref_id, description):
    ref = REFERENCES[ref_id]
    return f"{description}\n\n[{ref.title} ({ref.year})]({ref.url})"


ECE_HELP = ref_help(
    "fao61-crops", "A lab measure of dissolved salts in soil, reported as the electrical conductivity of a "
    "saturated paste extract (ECe) in dS/m. Enter a result that represents the crop root zone.",
)
ECW_HELP = ref_help(
    "fao29", "A measure of dissolved salts in irrigation water, reported as electrical conductivity (ECw) "
    "in dS/m. Use a representative water test for this source.",
)
ET_HELP = ref_help(
    "csu-seasonal-et", "Seasonal crop water use, including water lost through the plant and by evaporation. "
    "Edit the starting estimate to reflect your location, crop and growing season.",
)
RAIN_HELP = ref_help(
    "csu-seasonal-et", "The part of seasonal rainfall that is available to the crop and reduces irrigation "
    "demand. Enter zero to budget without a rainfall credit.",
)
YIELD_HELP = ref_help(
    "fao61-crops", "Choose the share of potential harvest you want to maintain with respect to salinity. "
    "100% targets zero yield loss from salinity in the model. A 90% target allows 10% modeled loss. "
    "The goal sets the target soil salinity unless you enter that target manually.",
)
ESTIMATED_YIELD_HELP = ref_help(
    "fao61-crops", "Estimated harvest at the measured soil salinity, as a percentage of potential "
    "harvest without salt stress. The curve models salinity alone and holds other factors fixed.",
)
EFF_HELP = ref_help(
    "osu-efficiency", "The share of irrigation water applied at the field that is stored in the root zone "
    "to meet crop demand in the crop-only budget. At 80% efficiency, 1 inch applied supplies about "
    "0.8 inch for crop use. The rest can drain below the roots, run off or evaporate.",
)
LR_HELP = ref_help(
    "fao29", "The estimated share of infiltrated irrigation that must move below the roots to carry salts "
    "out and maintain the target soil salinity. The estimate assumes the field can drain adequately.",
)
CREDIT_HELP = ref_help(
    "fao29", "The share of water left over after crop use that you assume helps carry salts below the roots. "
    "For example, at 80% efficiency, a 25% credit counts one quarter of the remaining 20% of the "
    "crop-only application. Only water that mixes with soil water and drains below the root zone earns credit. "
    "Use 0% when you cannot estimate that share.",
)
TARGET_ECE_HELP = ref_help(
    "fao29", "The root-zone salinity used to estimate maintenance leaching. The default 100% relative yield "
    "uses the crop’s salinity threshold. A lower relative yield uses the crop’s response curve to calculate "
    "the corresponding salinity. Enter a manual target when you have a specific planning value.",
)
NET_DEFICIT_HELP = ref_help(
    "csu-seasonal-et", "Seasonal crop water use minus the rain available to meet it. This is the amount "
    "irrigation must supply to the crop before accounting for application losses and leaching.",
)
GROSS_DEMAND_HELP = (
    "Total irrigation water to apply at the field, including water for the crop, application losses "
    "and any extra water needed for maintenance leaching. One acre-foot is 12 inches of water over one acre."
)
DELIVERY_HELP = (
    "Irrigation water expected to reach the farm this planning year after upstream losses. "
    "One acre-foot (AF) is 12 inches of water over one acre."
)


def heading(title, description=None, *, banner):
    st.title(title)
    if description:
        st.write(description)
    st.html(
        f'<img src="./app/static/banners/{banner}.jpg" alt="" decoding="async" '
        'style="display:block;width:100%;height:clamp(60px, 8vw, 112px);'
        'object-fit:cover;border-radius:8px;">'
    )


def errors_panel(errors):
    if errors:
        st.error("\n".join(f"- {plain_text(message)}" for message in errors))


def plain_text(value):
    """Render farm inputs as text where Streamlit interprets Markdown."""
    return re.sub(r"([\\`*_{}\[\]()<>!|~$])", r"\\\1", str(value))


def reference_link(reference, label=None):
    url = quote(reference.url, safe=":/?&=%#@+;,_-~.")
    if label:
        return f"[{label}](<{url}>)"
    return f"{plain_text(reference.citation)} [Source](<{url}>)"


def target_basis(field):
    if field.target_ece_override:
        return "Manually entered"
    return f"Calculated at {field.desired_yield_pct:g}% relative yield"


def require_scenario(draft):
    scenario, errors = validate_scenario(draft)
    if errors:
        st.warning("Complete the field and water source entries to calculate this scenario.")
        errors_panel(errors)
        if st.button("Go to Farm Setup"):
            st.switch_page("pages/farm_setup.py")
        return None
    return scenario


def scenario_caption(draft=None):
    state = workspace()
    draft = active() if draft is None else draft
    st.caption(plain_text(f"{state['farm_name'] or 'Untitled farm'} · {state['planning_year']} · {draft['name']}"))


def volume(value, signed=False):
    if value is None:
        return "Undetermined"
    return f"{value:+,.1f} AF" if signed else f"{value:,.1f} AF"


def selected_table_row(rows, *, key, column_config=None):
    """Render a selectable saved-record table and return its original row index."""
    state = st.dataframe(
        rows, key=key, hide_index=True, width="stretch", column_config=column_config,
        on_select="rerun", selection_mode="single-row",
    )
    selected = state.selection.rows
    return selected[0] if selected and 0 <= selected[0] < len(rows) else None


def download_farm_plan(plan):
    st.download_button(
        "Download Farm Plan (.json)", export_plan(plan), farm_plan_filename(), "application/json",
        help="Includes all saved scenarios. The filename shows the model version and local date and time.",
    )


def reset_entry(revision_key):
    st.session_state[revision_key] = st.session_state.get(revision_key, 0) + 1
    st.rerun()


def field_rows(result):
    sources = {row.source.id: row for row in result.sources}
    return [
        {
            "Field ID": row.field.id, "Crop": row.field.crop.label,
            "Area (ac)": row.field.acres, "Source ID": row.source.id,
            "Current ECe (dS/m)": row.field.current_ece_ds_m,
            "Current relative yield (%)": row.current_yield_pct, "Desired yield (%)": row.field.desired_yield_pct,
            "Target ECe (dS/m)": row.field.target_ece_ds_m, "LR (%)": row.lr * 100 if row.lr is not None else None,
            "Gross field depth (in)": row.depths.gross_in if row.depths else None,
            "Gross field volume (AF)": row.field_af,
            "Assigned source assessment": sources[row.source.id].assessment,
            "Maintenance leaching": sources[row.source.id].field_leaching_status(row),
            "Salinity and model notes": " ".join(row.warnings),
        }
        for row in result.fields
    ]


def source_rows(result):
    return [
        {
            "Source ID": row.source.id, "Expected farm delivery (AF)": row.source.delivery_af,
            "Assigned fields": ", ".join(item.field.id for item in row.fields),
            "Crop-only irrigation (AF)": row.crop_only_af, "Extra leaching needed (AF)": row.extra_leaching_af,
            "Leaching gap (AF)": row.leaching_gap_af, "Leaching coverage": row.leaching_status,
            "Demand (AF)": row.demand_af, "Known demand (AF)": row.known_demand_af,
            "Balance (AF)": row.balance_af, "Assessment": row.assessment,
        }
        for row in result.sources
    ]


def results_csv(rows):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    # Treat spreadsheet formula prefixes in imported or entered names as text.
    for row in rows:
        writer.writerow({
            key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                  else value)
            for key, value in row.items()
        })
    return output.getvalue().encode("utf-8-sig")
