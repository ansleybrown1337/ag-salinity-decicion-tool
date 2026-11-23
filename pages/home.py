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
        "1. **Add your fields.** Enter the area, crop, soil salinity, and irrigation method for each field.\n"
        "2. **Add water sources and assign fields.** Enter each source’s expected delivery and salinity, "
        "then select the fields it irrigates.\n"
        "3. **Review your farm plan.** Select **Review and Calculate Farm Plan** to check for water shortfalls. "
        "Then explore crop or irrigation changes for one field or compare plans for the whole farm."
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
