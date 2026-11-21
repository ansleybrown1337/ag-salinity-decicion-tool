# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import COPYRIGHT, LICENSE, REPOSITORY_URL, ROOT, TITLE, VERSION
from data.catalog import CROPS, ET_EXAMPLES, METHODS, REFERENCES
from ui.shared import heading

heading("About & Methods")
st.write(
    f"{TITLE} {VERSION} helps producers, irrigation managers, Extension professionals, conservation planners, "
    "consultants, resource managers, and researchers assess annual water allocations and salinity objectives."
)
st.markdown((ROOT / "docs/methods.md").read_text(encoding="utf-8"))
with st.expander("Published defaults"):
    st.dataframe([
        {"Crop": crop.label, "Scientific name": crop.scientific_name, "Endpoint": crop.endpoint,
         "Threshold (dS/m)": crop.threshold_ds_m, "Slope (percentage points per dS/m)": crop.slope_pct_per_ds_m,
         "Reference": crop.reference_id}
        for crop in CROPS.values()
    ], hide_index=True)
    st.dataframe([
        {"Irrigation method": method.label, "Published range (%)": f"{method.published_range_pct[0]:g}–"
         f"{method.published_range_pct[1]:g}", "Midpoint (%)": method.efficiency_pct,
         "Reference": method.reference_id}
        for method in METHODS.values()
    ], hide_index=True)
with st.expander("Seasonal crop ET starting estimates"):
    st.dataframe([
        {"Crop": CROPS[crop_id].label, "ET (in)": example.etc_in, "Location": example.location,
         "CSU table row": example.source_crop}
        for crop_id, example in ET_EXAMPLES.items()
    ], hide_index=True)
    reference = REFERENCES["csu-seasonal-et"]
    st.markdown(f"{reference.citation} [Source]({reference.url})")
st.subheader("Scientific references")
for reference_id, reference in REFERENCES.items():
    st.markdown(f"**{reference_id}** · {reference.citation} [Source]({reference.url})")
st.subheader("Future development")
st.write(
    "Soil reclamation planning, weather-based ET estimates, spatial salinity analysis, dynamic water and salt "
    "balances, water blending, economics, optimization, and uncertainty analysis are future work."
)
st.subheader("Software and license")
st.write(f"Version {VERSION} · {COPYRIGHT} · {LICENSE}")
if REPOSITORY_URL:
    st.link_button("Project repository", REPOSITORY_URL)
