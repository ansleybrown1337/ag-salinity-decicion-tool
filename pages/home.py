# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import CONTACT_URL, CREATOR, CREATOR_URL, REPOSITORY_URL, TITLE
from ui.shared import heading
from ui.state import demo_plan, install_plan


heading(
    TITLE,
    "Plan irrigation for salt-affected fields. Use soil and water salinity measurements to estimate how "
    "much irrigation your crops need and whether each water source can deliver enough.",
    banner="farm-setup",
)

with st.container(border=True):
    st.subheader("How to use this tool")
    st.markdown(
        "1. **Farm Setup.** Add your fields, enter water sources, and assign a source to each field.\n"
        "2. **Farm Dashboard.** Review water supply and estimated yield loss for your baseline plan.\n"
        "3. **What-If Scenarios.** Save and compare alternate crop or rainfall plans.\n"
        "4. **Field Details.** Select a field in the sidebar to see what drives its results across plans.\n"
        "5. **Optimization (experimental).** Compare crop plans for gross revenue with and without a maintenance leaching requirement."
    )
    with st.container(horizontal=True):
        if st.button("Get started", type="primary"):
            st.switch_page("pages/farm_setup.py")
        if st.button("Load demonstration farm"):
            install_plan(demo_plan())
            st.switch_page("pages/farm_dashboard.py")
    st.caption(
        "Use Farm Setup to create or upload a plan. Loading the demonstration opens an example with two "
        "scenarios and replaces the current session’s plan."
    )

st.subheader("Contact and feedback")
st.markdown(f"Created by [{CREATOR}]({CREATOR_URL}) · [Contact AJ Brown]({CONTACT_URL})")
st.markdown(
    f"[View the project on GitHub]({REPOSITORY_URL}) · "
    f"[Report an issue or suggest a feature]({REPOSITORY_URL.rstrip('/')}/issues)"
)
