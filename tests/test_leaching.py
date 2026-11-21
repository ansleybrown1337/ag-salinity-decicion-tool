# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from models.leaching import leaching_requirement


@pytest.mark.parametrize("target, exact, published", [(2.5, 1.2 / 11.3, 0.10), (1.7, 1.2 / 7.3, 0.16)])
def test_fao29_example_3_maize(target, exact, published):
    lr = leaching_requirement(1.2, target)
    assert lr == pytest.approx(exact)
    assert lr == pytest.approx(published, abs=0.007)
    assert lr == pytest.approx(leaching_requirement(1200, target * 1000))


def test_zero_water_ec():
    assert leaching_requirement(0, 2.5) == 0


@pytest.mark.parametrize("ecw, ece, message", [
    (5, 1, "denominator"), (6, 1, "denominator"),
    (2.5, 1, "at least 100%"), (4, 1, "at least 100%"),
    (0, 0, "positive"), (1, -1, "positive"),
    (-1, 2, "Irrigation water ECw"), (None, 2, "Irrigation water ECw"),
    (1, None, "Target soil ECe"), (1, float("nan"), "Target soil ECe"),
])
def test_invalid_or_infeasible_lr(ecw, ece, message):
    with pytest.raises(ValueError, match=message):
        leaching_requirement(ecw, ece)
