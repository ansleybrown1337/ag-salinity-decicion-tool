# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import CREATOR, CREATOR_URL, TITLE, logo_path
from ui.field_controls import choose_field
from ui.state import initialize, workspace

st.set_page_config(page_title=TITLE, layout="wide")
initialize()

setup = st.Page("pages/farm_setup.py", title="Farm Setup", default=True)
dashboard = st.Page("pages/farm_dashboard.py", title="Farm Dashboard")
fields = st.Page("pages/field_decisions.py", title="Field Decisions")
scenarios = st.Page("pages/scenarios.py", title="Scenario Comparison")
about = st.Page("pages/about.py", title="About & Methods")

pages = [setup, dashboard]
if workspace()["reviewed"]:
    pages += [fields, scenarios]
pages.append(about)
page = st.navigation(pages, position="hidden")
if st.session_state.pop("open_dashboard", False):
    st.switch_page(dashboard)

with st.sidebar:
    for item in pages:
        st.page_link(item, width="stretch")
        if item is fields and page is fields:
            row = choose_field("Field to analyze", st.session_state.get("selected_field"), vertical=True)
            st.session_state.selected_field = row["_key"] if row else None

    st.divider()
    logo = logo_path()
    if logo:
        st.image(str(logo), width=170)
    st.header(TITLE)
    st.caption(f"Created by [{CREATOR}]({CREATOR_URL})")

page.run()
