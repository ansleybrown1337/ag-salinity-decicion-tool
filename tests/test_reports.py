# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import date, datetime, timezone
from io import BytesIO

from PIL import Image
from pypdf import PdfReader

from config.branding import BROWN, COPYRIGHT, CREATOR, CREATOR_URL, DARK_GREEN, LICENSE, LIGHT_GREEN
from data.catalog import ET_EXAMPLES
from models.water_budget import evaluate_scenario
from reports.pdf_report import management_report, optimization_report
from schemas.farm import OptimizationOutcome, OptimizationQuote, OptimizationRun, OptimizationSettings, Scenario, crop_key


def render(demo, scenario):
    report = management_report(
        demo.farm_name, demo.planning_year, demo.notes, scenario,
        evaluate_scenario(scenario), demo.references, generated=date(2026, 11, 20),
    )
    assert report.startswith(b"%PDF")
    return PdfReader(BytesIO(report))


def test_report_inputs_outputs_references_and_footer(demo):
    pdf = render(demo, demo.active_scenario)
    assert pdf.metadata.author == CREATOR
    text = " ".join(" ".join(page.extract_text().split()) for page in pdf.pages)
    for content in (
        demo.farm_name, "2026-11-20", "Baseline", "374.2", "23.8 AF", "ETc 27.0 in", "Expected farm delivery",
        "Efficiency 85.0% (User override)", "Target ECe", "Shoot dry weight",
        "10.1061/JRCEA4.0001137", "fao61-balance", f"Created by {CREATOR}", COPYRIGHT, LICENSE,
    ):
        assert content in text
    for index, page in enumerate(pdf.pages, 1):
        assert f"Page {index}" in page.extract_text()
        assert COPYRIGHT in page.extract_text()
    annotations = [ref.get_object() for page in pdf.pages for ref in page.get("/Annots", [])]
    urls = {item.get("/A", {}).get("/URI") for item in annotations}
    assert {CREATOR_URL, demo.references["fao29"].url} <= urls


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


def test_optimization_pdf_is_standalone_and_full_report_appends_only_completed_runs(demo):
    baseline, alternative = demo.scenarios
    chosen = alternative.model_copy(update={"leaching_field_ids": ()})
    crops = [field.crop for field in baseline.fields]
    run = OptimizationRun(
        id="demo-run", model_version=demo.app_version, completed_at=datetime(2026, 11, 24, tzinfo=timezone.utc),
        settings=OptimizationSettings(
            starting_plan_id=baseline.id, leaching_field_ids=(),
            eligible={field.id: (crop_key(field.crop),) for field in alternative.fields},
            quotes=[OptimizationQuote(crop=crop, unit="test unit", expected_yield=100.0, price=10.0) for crop in crops],
        ),
        starting_plan=baseline, starting_revenue=228_650,
        outcomes=[OptimizationOutcome(requires_leaching=False, plan=chosen, gross_revenue=91_155)],
    )

    def extract(pdf):
        return " ".join(" ".join(page.extract_text().split()) for page in pdf.pages)

    standalone = extract(PdfReader(BytesIO(optimization_report(demo.farm_name, demo.planning_year, run))))
    for phrase in ("Optimization comparison", "full-irrigation benchmark", "East Well (11.2 AF)",
                   "Starting crops excluded", "$228,650", "$91,155", "Eligible crops", "test unit"):
        assert phrase in standalone
    assert "Scientific methods" not in standalone
    assert "Optimization comparison" not in extract(render(demo, baseline))
    full = management_report(demo.farm_name, demo.planning_year, demo.notes, baseline, evaluate_scenario(baseline),
                             demo.references, optimization_runs=(run, run))
    combined = extract(PdfReader(BytesIO(full)))
    assert "Scientific methods" in combined
    assert "Optimization comparison - Run 1" in combined and "Optimization comparison - Run 2" in combined
