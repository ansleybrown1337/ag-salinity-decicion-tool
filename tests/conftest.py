# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from config.branding import ROOT
from schemas.farm import load_plan


@pytest.fixture
def demo():
    return load_plan((ROOT / "examples/example_farm.json").read_bytes())
