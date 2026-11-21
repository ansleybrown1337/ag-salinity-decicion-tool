# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import pytest

from data.catalog import CROPS, ET_EXAMPLES, REFERENCES
from models.crop_response import relative_yield, target_ece


@pytest.mark.parametrize("ece, expected", [(2, 100), (8, 100), (10, 90), (28, 0), (45, 0)])
def test_barley_response(ece, expected):
    assert relative_yield(ece, 8, 5) == expected


def test_threshold_and_slope_overrides():
    assert relative_yield(10, 9, 5) == 95
    assert relative_yield(10, 8, 6) == 88


@pytest.mark.parametrize("ece, threshold, slope", [
    (-1, 8, 5), (2, -1, 5), (2, 8, 0), (2, 8, -2),
    (None, 8, 5), (float("nan"), 8, 5), (2, 8, float("inf")), (True, 8, 5),
])
def test_invalid_response_inputs(ece, threshold, slope):
    with pytest.raises(ValueError):
        relative_yield(ece, threshold, slope)


@pytest.mark.parametrize("yield_pct, printed_target, absolute_error", [
    (100, 7.7, 1e-12), (90, 9.6, 0.05), (75, 13, 0.5), (50, 17, 0.5),
])
def test_fao29_example_4_cotton(yield_pct, printed_target, absolute_error):
    computed = target_ece(yield_pct, 7.7, 5.2)
    assert computed == pytest.approx(printed_target, abs=absolute_error)
    assert relative_yield(computed, 7.7, 5.2) == pytest.approx(yield_pct)


@pytest.mark.parametrize("desired", [0, -1, 100.1, None, float("inf")])
def test_undefined_or_invalid_inverse(desired):
    with pytest.raises(ValueError):
        target_ece(desired, 8, 5)


def test_fao61_crop_presets_and_endpoints():
    expected = {
        "barley": (8, 5, "Grain yield"),
        "wheat": (6, 7.1, "Grain yield"),
        "alfalfa": (2, 7.3, "Shoot dry weight"),
        "corn_grain": (1.9, 26, "Grain yield"),
        "corn_silage": (1.8, 7.4, "Shoot dry weight"),
        "corn_sweet": (1.7, 12, "Ear fresh weight"),
        "dry_bean": (1, 19, "Seed yield"),
        "cantaloupe": (1, 8.4, "Fruit yield"),
        "potato": (1.7, 12, "Tuber yield"),
        "onion": (1.2, 16, "Bulb yield"),
        "sorghum": (6.8, 16, "Grain yield"),
        "soybean": (5, 20, "Seed yield"),
        "sugar_beet": (7, 5.9, "Storage root yield"),
    }
    assert set(CROPS) == set(expected)
    for key, crop in CROPS.items():
        assert (crop.threshold_ds_m, crop.slope_pct_per_ds_m, crop.endpoint) == expected[key]
        assert crop.reference_id == "fao61-crops"
        assert crop.reference_id in REFERENCES


def test_csu_greeley_et_examples():
    # CSU Extension Table 1, Greeley column.
    expected = {
        "alfalfa": 37.1, "barley": 20.6, "wheat": 17.9, "corn_grain": 23.9,
        "corn_silage": 22.9, "corn_sweet": 21.9, "dry_bean": 15.7, "cantaloupe": 17.2,
        "potato": 20.2, "onion": 24.2, "sorghum": 20.9, "soybean": 18.7, "sugar_beet": 27.1,
    }
    assert set(ET_EXAMPLES) == set(CROPS)
    assert {crop: estimate.etc_in for crop, estimate in ET_EXAMPLES.items()} == expected
    assert all(estimate.location == "Greeley, Colorado" and estimate.reference_id == "csu-seasonal-et"
               for estimate in ET_EXAMPLES.values())
    assert ET_EXAMPLES["barley"].source_crop == "Spring grains"
