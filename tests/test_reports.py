# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import date
from io import BytesIO

from PIL import Image
from pypdf import PdfReader

from config.branding import BROWN, COPYRIGHT, DARK_GREEN, LICENSE, LIGHT_GREEN
from data.catalog import ET_EXAMPLES
from models.water_budget import evaluate_scenario
from reports.pdf_report import management_report
from schemas.farm import Scenario


def render(demo, scenario):
    report = management_report(
        demo.farm_name, demo.planning_year, demo.notes, scenario,
        evaluate_scenario(scenario), demo.references, generated=date(2026, 11, 20),
    )
    assert report.startswith(b"%PDF")
    return PdfReader(BytesIO(report))


def test_report_inputs_outputs_references_and_footer(demo):
    pdf = render(demo, demo.active_scenario)
    text = " ".join(" ".join(page.extract_text().split()) for page in pdf.pages)
    for content in (
        demo.farm_name, "2026-11-20", "Baseline", "374.2", "23.8 AF", "ETc 27.0 in", "Expected farm delivery",
        "Efficiency 85.0% (User override)", "Target ECe", "Shoot dry weight",
        "10.1061/JRCEA4.0001137", "fao61-balance", COPYRIGHT, LICENSE,
    ):
        assert content in text
    for index, page in enumerate(pdf.pages, 1):
        assert f"Page {index}" in page.extract_text()
        assert COPYRIGHT in page.extract_text()
    annotations = [ref.get_object() for page in pdf.pages for ref in page.get("/Annots", [])]
    assert any(str(item.get("/A", {}).get("/URI", "")) == demo.references["fao29"].url for item in annotations)


def test_36_field_report_repeats_headers_and_uses_brand_palette(demo):
    template = demo.active_scenario
    scenario = Scenario(id="large", name="Large farm", sources=template.sources,
                        fields=[template.fields[i % 3].model_copy(
                            update={"id": f"Bench field {i:02}"}) for i in range(36)])
    pdf = render(demo, scenario)
    pages = [page.extract_text() for page in pdf.pages]
    assert sum("Field / crop" in text for text in pages) >= 2
    assert all(any(f"Bench field {i:02}" in text for text in pages) for i in range(36))
    color_commands = [operands for page in pdf.pages for operands, operator in page.get_contents().operations
                      if operator in {b"rg", b"RG"}]
    for color in (DARK_GREEN, BROWN, LIGHT_GREEN):
        rgb = tuple(int(color[start:start + 2], 16) / 255 for start in (1, 3, 5))
        assert any(all(abs(float(value) - channel) < 1e-5 for value, channel in zip(used, rgb))
                   for used in color_commands)


def test_optional_logo_is_embedded(demo, tmp_path, monkeypatch):
    path = tmp_path / "test-image.png"
    Image.new("RGB", (80, 40), "#0D3439").save(path)
    monkeypatch.setenv("AG_SALINITY_LOGO", str(path))
    pdf = render(demo, demo.active_scenario)
    assert len(pdf.pages[0].images) == 1


def test_report_records_location_specific_et_and_override(demo):
    scenario = demo.active_scenario
    field = scenario.fields[-1].model_copy(update={"et_estimate": ET_EXAMPLES["corn_silage"]})
    scenario = scenario.model_copy(update={"fields": (*scenario.fields[:-1], field)})
    text = "\n".join(page.extract_text() for page in render(demo, scenario).pages)
    assert "ET starting estimate 22.9 in | Greeley, Colorado" in text
    assert "Adjusted for this field" in text
