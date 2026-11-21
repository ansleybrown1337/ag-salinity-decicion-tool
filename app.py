# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import streamlit as st

from config.branding import TITLE, logo_path
from ui.state import initialize, workspace

st.set_page_config(page_title=TITLE, layout="wide")
initialize()

logo = logo_path()
if logo:
    st.sidebar.image(str(logo), width=170)
st.sidebar.header(TITLE)
st.sidebar.caption("AgriData Solutions, LLC")

setup = st.Page("pages/farm_setup.py", title="Farm Setup", default=True)
supply = st.Page("pages/water_supply.py", title="Water Supply")
dashboard = st.Page("pages/farm_dashboard.py", title="Farm Dashboard")
fields = st.Page("pages/field_decisions.py", title="Field Decisions")
scenarios = st.Page("pages/scenarios.py", title="Scenario Comparison")
about = st.Page("pages/about.py", title="About & Methods")

pages = [setup, supply]
if workspace()["reviewed"]:
    pages += [dashboard, fields, scenarios]
pages.append(about)
page = st.navigation(pages)
if st.session_state.pop("open_dashboard", False):
    st.switch_page(dashboard)
page.run()
