# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from data.catalog import METHODS, REFERENCES
from models.irrigation import acre_feet, irrigation_depths, net_crop_depth
from models.leaching import leaching_requirement


@pytest.mark.parametrize("rain, expected", [(0, 22), (4, 18), (22, 0), (24, 0)])
def test_net_crop_deficit(rain, expected):
    assert net_crop_depth(22, rain) == expected


def test_custom_efficiency_and_volume():
    result = irrigation_depths(18, 0.75, 0, 0)
    assert result.gross_in == 24
    assert result.additional_gross_in == 0
    assert result.nonbeneficial_loss_in == 6
    assert acre_feet(result.gross_in, 12) == 24


@pytest.mark.parametrize("credit", [0, 0.25, 0.5, 1])
def test_balance_and_required_drainage(credit):
    result = irrigation_depths(18, 0.75, 0.35, credit)
    assert result.gross_in == pytest.approx(18 + result.effective_drainage_in + result.nonbeneficial_loss_in)
    assert result.gross_in == pytest.approx(result.crop_only_gross_in + result.additional_gross_in)
    assert result.effective_drainage_in / (18 + result.effective_drainage_in) == pytest.approx(0.35)


def test_fao29_example_3_full_credit_satisfies_leaching():
    lr = leaching_requirement(1.2, 2.5)
    net_in = 800 / 25.4
    result = irrigation_depths(net_in, 0.65, lr, 1)
    no_credit = irrigation_depths(net_in, 0.65, lr, 0)
    assert result.gross_in * 25.4 == pytest.approx(1230, abs=1)
    assert net_in / (1 - lr) * 25.4 == pytest.approx(890, abs=6)
    assert result.additional_gross_in == 0
    assert no_credit.gross_in > result.gross_in
    assert result.credited_existing_in > result.theoretical_leach_in


def test_zero_crop_deficit_and_positive_lr():
    result = irrigation_depths(0, 0.7, 0.14, 0.5)
    assert result.gross_in == result.theoretical_leach_in == 0


@pytest.mark.parametrize("inputs", [(-1, .7, 0, 0), (10, 0, 0, 0), (10, 1.1, 0, 0),
                                    (10, .7, 1, 0), (10, .7, -0.1, 0), (10, .7, 0, 1.1)])
def test_bad_depth_inputs(inputs):
    with pytest.raises(ValueError):
        irrigation_depths(*inputs)


def test_bad_depth_and_volume():
    for function, args in ((net_crop_depth, (12, -2)), (acre_feet, (12, 0))):
        with pytest.raises(ValueError):
            function(*args)


def test_osu_ranges():
    published = {"drip": (85, 95), "pivot": (75, 90), "furrow": (60, 80),
                 "level_border": (60, 80), "wild_flood": (25, 40)}
    assert set(METHODS) == set(published)
    for key, bounds in published.items():
        method = METHODS[key]
        assert method.published_range_pct == bounds
        assert method.efficiency_pct == sum(bounds) / 2
        assert method.reference_id in REFERENCES
