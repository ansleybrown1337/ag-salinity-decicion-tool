# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import CREATOR, CREATOR_URL, LICENSE, REPOSITORY_URL, ROOT, TITLE, VERSION
from data.catalog import CROPS, ET_EXAMPLES, METHODS, REFERENCES
from ui.shared import heading, plain_text, reference_link


def citation(reference):
    title = reference_link(reference, plain_text(reference.title))
    return f"{reference.authors} ({reference.year}). {title}. {reference.publication}."

heading("About & Methods", banner="about-methods")
st.write(
    f"{TITLE} {VERSION} helps producers, irrigation managers, Extension professionals, conservation planners, "
    "consultants, resource managers, and researchers assess annual water allocations and salinity objectives."
)
st.markdown((ROOT / "docs/methods.md").read_text(encoding="utf-8"))
with st.expander("Published defaults"):
    reference_column = st.column_config.LinkColumn(display_text="Open source")
    st.dataframe([
        {"Crop": crop.label, "Scientific name": crop.scientific_name, "Endpoint": crop.endpoint,
         "Threshold (dS/m)": crop.threshold_ds_m, "Slope (percentage points per dS/m)": crop.slope_pct_per_ds_m,
         "Reference": REFERENCES[crop.reference_id].url}
        for crop in CROPS.values()
    ], hide_index=True, column_config={"Reference": reference_column})
    st.dataframe([
        {"Irrigation method": method.label, "Published range (%)": f"{method.published_range_pct[0]:g}–"
         f"{method.published_range_pct[1]:g}", "Midpoint (%)": method.efficiency_pct,
         "Reference": REFERENCES[method.reference_id].url}
        for method in METHODS.values()
    ], hide_index=True, column_config={"Reference": reference_column})
with st.expander("Seasonal crop ET starting estimates"):
    st.dataframe([
        {"Crop": CROPS[crop_id].label, "ET (in)": example.etc_in, "Location": example.location,
         "CSU table row": example.source_crop}
        for crop_id, example in ET_EXAMPLES.items()
    ], hide_index=True)
    st.markdown(citation(REFERENCES["csu-seasonal-et"]))
st.subheader("Scientific references")
st.markdown("\n".join(f"- {citation(reference)}" for reference in REFERENCES.values()))
st.subheader("Experimental optimization")
st.write(
    "Optimization tests eligible crops against source-specific water budgets and compares estimated gross revenue "
    "with and without requiring adequate salinity leaching on selected fields. Each candidate uses its crop’s salinity threshold. "
    "Revenue uses the entered price, expected yield without salinity stress and modeled yield at current soil salinity."
)
st.markdown("[SciPy mixed-integer linear programming](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)")
st.subheader("Future development")
st.write(
    "Soil reclamation planning, weather-based ET estimates, spatial salinity analysis, dynamic water and salt "
    "balances, water blending, production costs, and uncertainty analysis are future work."
)
st.subheader("Software and license")
st.markdown(f"Created by [{CREATOR}]({CREATOR_URL})")
st.write(f"Version {VERSION} · {LICENSE}")
st.caption("OpenAI generated the banner images for Ag Salinity Manager. They illustrate agricultural settings.")
st.link_button("Project repository", REPOSITORY_URL)
