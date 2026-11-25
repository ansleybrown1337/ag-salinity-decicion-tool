# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import COPYRIGHT_YEAR, CREATOR, CREATOR_URL, LICENSE, TITLE, logo_path
from ui.shared import plain_text
from ui.state import field_names, initialize

st.set_page_config(page_title=TITLE, layout="wide")
initialize()

home = st.Page("pages/home.py", title="Home", default=True)
setup = st.Page("pages/farm_setup.py", title="Farm Setup")
dashboard = st.Page("pages/farm_dashboard.py", title="Farm Dashboard")
scenarios = st.Page("pages/scenarios.py", title="What-If Scenarios")
fields = st.Page("pages/field_decisions.py", title="Field Details")
optimization = st.Page("pages/optimization.py", title="Optimization")
reports = st.Page("pages/reports.py", title="Download Full Report")
about = st.Page("pages/about.py", title="About & Methods")

navigation = [
    (home, "Home"),
    (setup, "1. Farm Setup"),
    (dashboard, "2. Farm Dashboard"),
    (scenarios, "3. What-If Scenarios"),
    (fields, "4. Field Details"),
    (optimization, "5. Optimization"),
    (reports, "6. Download Full Report"),
    (about, "About & Methods"),
]
page = st.navigation([item for item, _ in navigation], position="hidden")

with st.sidebar:
    for item, label in navigation:
        st.page_link(item, label=label, width="stretch")
        if item is fields and (names := field_names()):
            selected = st.session_state.get("selected_field")
            if selected not in names:
                selected = next(iter(names), None)
            st.html(
                "<style>.st-key-field-navigation { padding-left: 1.25rem; }"
                ".st-key-field-navigation button { min-height: 1.8rem; padding: .15rem .55rem; }</style>"
            )
            with st.container(key="field-navigation", gap=None):
                for field_key, field_name in names.items():
                    if st.button(
                        plain_text(field_name), key=f"sidebar-field/{field_key}",
                        type="secondary" if page is fields and selected == field_key else "tertiary",
                    ):
                        st.session_state.selected_field = field_key
                        st.switch_page(fields)

    st.divider()
    logo = logo_path()
    if logo:
        st.image(str(logo), width=170)
    st.header(TITLE)
    st.caption(f"Created by [{CREATOR}]({CREATOR_URL})")
    st.caption(f"Copyright © {COPYRIGHT_YEAR} · {LICENSE}")

page.run()
