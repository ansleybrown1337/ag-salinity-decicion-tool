# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import csv
import json

from config.branding import ROOT
from schemas.farm import Crop, CropEtEstimate, Method, Reference


def _rows(filename):
    with (ROOT / "data" / filename).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


REFERENCES = {
    key: Reference.model_validate(record)
    for key, record in json.loads((ROOT / "data/references.json").read_text(encoding="utf-8")).items()
}
CROPS = {
    row["id"]: Crop(
        **{**row, "threshold_ds_m": float(row["threshold_ds_m"]),
           "slope_pct_per_ds_m": float(row["slope_pct_per_ds_m"])},
        threshold_origin="Published default",
        slope_origin="Published default",
    )
    for row in _rows("crop_tolerance.csv")
}
ET_EXAMPLES = {
    row["crop_id"]: CropEtEstimate(
        etc_in=float(row["etc_in"]), location=row["location"], source_crop=row["source_crop"],
        reference_id=row["reference_id"],
    )
    for row in _rows("crop_et_examples.csv")
}

METHODS = {}
for row in _rows("irrigation_efficiency.csv"):
    low, high = float(row["low_pct"]), float(row["high_pct"])
    METHODS[row["id"]] = Method(
        id=row["id"], label=row["label"], published_range_pct=(low, high),
        efficiency_pct=(low + high) / 2, efficiency_origin="Published default",
        reference_id=row["reference_id"],
    )
