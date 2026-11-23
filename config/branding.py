# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Ag Salinity Manager"
CREATOR = "AJ Brown, PhD"
CREATOR_URL = "https://sites.google.com/view/ansleyjbrown"
CONTACT_URL = f"{CREATOR_URL}/contact"
VERSION = "0.1.1"
COPYRIGHT_YEAR = 2026
COPYRIGHT = f"Copyright (C) {COPYRIGHT_YEAR} AgriData Solutions, LLC"
LICENSE = "GPL-2.0-or-later"
DARK_GREEN = "#0D3439"
LIGHT_GREEN = "#579A8D"
BROWN = "#6F4D25"
WHITE = "#FFFFFF"
PALE_GREEN = "#F0F6F4"
REPOSITORY_URL = os.getenv("AG_SALINITY_REPOSITORY_URL") or "https://github.com/ansleybrown1337/ag-salinity-decicion-tool"


def logo_path() -> Path | None:
    """Return an optional, locally configured raster logo used by both renderers."""
    path = Path(os.getenv("AG_SALINITY_LOGO", "assets/logo.png"))
    path = ROOT / path
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"} and path.is_file():
        return path
    return None
