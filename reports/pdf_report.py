# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.platypus import CondPageBreak, Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from config.branding import (
    BROWN, COPYRIGHT, CREATOR, CREATOR_URL, DARK_GREEN, LICENSE, LIGHT_GREEN, PALE_GREEN, ROOT, TITLE, VERSION, WHITE,
    logo_path,
)
from data.catalog import REFERENCES
from models.optimization import MODE, crop_shortfalls, excluded_starting_crops, reference_label
from models.water_budget import evaluate_scenario


def _number(value, places=1):
    return "Undetermined" if value is None else f"{value:,.{places}f}"


def _table(headers, rows, widths, cell, header):
    table = LongTable(
        [[Paragraph(escape(text), header) for text in headers]]
        + [[Paragraph(escape(str(value)), cell) for value in row] for row in rows],
        colWidths=widths, repeatRows=1, hAlign="LEFT", splitInRow=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK_GREEN)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(WHITE), colors.HexColor(PALE_GREEN)]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor(LIGHT_GREEN)),
    ]))
    return table


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(LIGHT_GREEN))
    canvas.line(doc.leftMargin, 39, letter[0] - doc.rightMargin, 39)
    canvas.setFillColor(colors.HexColor(DARK_GREEN))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 25, f"{COPYRIGHT}  |  {LICENSE}")
    canvas.drawRightString(letter[0] - doc.rightMargin, 25, f"Page {doc.page}")
    canvas.restoreState()


def management_report(farm_name, year, notes, scenario, result, references, *, generated=None, optimization_runs=()):
    """Generate a printable PDF in memory for the selected scenario and its results."""
    generated = generated or date.today()
    output = BytesIO()
    doc = _document(output, f"{TITLE} - {farm_name}")
    green = colors.HexColor(DARK_GREEN)
    brown = colors.HexColor(BROWN)
    title = ParagraphStyle("ReportTitle", fontName="Helvetica-Bold", fontSize=27, leading=33,
                           textColor=green, spaceAfter=6)
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_LEFT,
                          textColor=green, spaceAfter=8, allowWidows=0, allowOrphans=0)
    h1 = ParagraphStyle("Heading", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=21,
                        spaceBefore=14, spaceAfter=7, keepWithNext=True)
    h2 = ParagraphStyle("Subheading", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14,
                        textColor=brown, spaceBefore=10, spaceAfter=4, keepWithNext=True)
    table_heading = ParagraphStyle("TableHeading", parent=h1, keepWithNext=False)
    method_text = ParagraphStyle("MethodText", parent=body, fontSize=9.5, leading=12.5, spaceAfter=7)
    bibliography = ParagraphStyle("Bibliography", parent=body, fontSize=9, leading=11.5, spaceAfter=6)
    cell = ParagraphStyle("Cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    header = ParagraphStyle("Header", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    story = []

    def paragraph(text, style=body):
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), style))

    def table(headers, rows, widths):
        story.append(_table(headers, rows, widths, cell, header))
        story.append(Spacer(1, 10))

    logo = logo_path()
    if logo:
        image = Image(str(logo), width=140, height=52, kind="proportional", hAlign="LEFT")
        story.extend([image, Spacer(1, 12)])
    paragraph(TITLE, title)
    story.append(Paragraph(
        f"Management report  |  Version {VERSION}  |  Created by "
        f"<link href={quoteattr(CREATOR_URL)} color={quoteattr(BROWN)}>{escape(CREATOR)}</link>", body,
    ))
    paragraph(farm_name, h1)
    paragraph(f"{year} planning year  |  Scenario: {scenario.name}  |  Generated {generated.isoformat()}")
    table(["Farm summary", "Planning result"], [
        ("Total acreage / number of fields", f"{result.acres:,.1f} ac / {len(result.fields)}"),
        ("Expected farm delivery", f"{result.field_supply_af:,.1f} AF"),
        ("Net crop water deficit", f"{result.net_crop_af:,.1f} AF"),
        ("Extra field water budgeted for salinity leaching (AF)", _number(result.planned_extra_leaching_af)),
        ("Total planned field irrigation demand (AF)", _number(result.planned_demand_af)),
        ("Combined field surplus (+) / deficit (-), AF", _number(result.planned_balance_af)),
        ("Known assigned-source shortfall", f"{result.planned_shortfall_af:,.1f} AF"),
    ], [330, 184])
    paragraph("Management interpretation", h2)
    if scenario.leaching_field_ids is None:
        paragraph(result.allocation_conclusion)
    else:
        selected = ", ".join(scenario.leaching_field_ids) or "None"
        paragraph(f"Fields budgeted for leaching: {selected}.")
        if result.planned_shortfall_af > 0:
            paragraph("At least one water source falls short of its planned irrigation demand.")
        elif result.planned_demand_af is None:
            paragraph("Some planned leaching requirements could not be estimated.")
        else:
            paragraph("Expected delivery covers the planned irrigation budget at each assigned source.")
    if scenario.leaching_field_ids is None and result.field_demand_af is not None:
        lower = result.complete_sum("all_credit_field_af")
        upper = result.complete_sum("zero_credit_field_af")
        paragraph(f"Field demand sensitivity to effective leaching credit ranges from {lower:,.1f} AF at full "
                  f"credit to {upper:,.1f} AF at zero credit. Each assigned source is assessed independently.")
    if result.salinity_concerns:
        above_target = sum(row.field.current_ece_ds_m > row.field.target_ece_ds_m for row in result.fields)
        no_estimate = sum(row.field_af is None for row in result.fields)
        paragraph(f"{result.salinity_concerns} fields carry salinity or model notes. "
                  f"{above_target} exceed target ECe and {no_estimate} lack a feasible maintenance budget. "
                  "See the field records for details.")
    paragraph("Maintenance estimates assume effective drainage. Current salinity above target may require "
              "reclamation. Confirm site conditions and delivery constraints before making management decisions.")

    story.append(PageBreak())
    paragraph("Water budget by source", table_heading)
    table(["Water source ID", "Farm delivery (AF)", "Planned (AF)", "Balance (AF)", "Leaching capacity"], [
        (row.source.id, _number(row.source.delivery_af),
         _number(row.planned_demand_af),
         _number(row.source.delivery_af - row.planned_demand_af) if row.planned_demand_af is not None else "Undetermined",
         row.leaching_status)
        for row in result.sources
    ], [173, 68, 78, 78, 117])
    story.append(CondPageBreak(120))
    paragraph("Field salinity and irrigation results", table_heading)
    sources = {row.source.id: row for row in result.sources}
    table(["Field / crop", "Area (ac)", "Current / target ECe (dS/m)", "Current / desired yield (%)",
           "LR (%)", "Gross depth with leaching (in)", "Planned field volume (AF)"], [
        (f"{row.field.id} / {row.field.crop.label}", _number(row.field.acres),
         f"{row.field.current_ece_ds_m:.2f} / {row.field.target_ece_ds_m:.2f}",
         f"{row.current_yield_pct:.1f} / {row.field.desired_yield_pct:g}",
         _number(row.lr * 100, 2) if row.lr is not None else "Infeasible",
         _number(row.depths.gross_in) if row.depths else "—",
         _number(sources[row.source.id].planned_field_af(row)))
        for row in result.fields
    ], [153, 42, 74, 77, 47, 53, 68])

    paragraph("Input record and field notes", h1)
    paragraph("Field and water entries are user-provided unless marked as a published default or calculated. "
              "Input precision is retained below. Results tables are rounded for readability.")
    if notes:
        paragraph(f"Farm notes: {notes}")
    for source in scenario.sources:
        paragraph(source.id, h2)
        paragraph(f"{source.source_type} | Expected farm delivery {source.delivery_af} AF | "
                  f"ECw {source.ecw_ds_m} dS/m.")
        if source.notes:
            paragraph(source.notes)
    for row in result.fields:
        field, crop, irrigation = row.field, row.field.crop, row.field.irrigation
        paragraph(field.id, h2)
        paragraph(f"{crop.label} | {crop.endpoint} | {field.acres} ac | Source ID {field.source_id} | "
                  f"Current ECe {field.current_ece_ds_m} dS/m | Desired yield {field.desired_yield_pct}% | "
                  f"Target ECe {field.target_ece_ds_m} dS/m "
                  f"({'User override' if field.target_ece_override else 'Calculated'}) | "
                  f"Calculated yield at target {row.yield_at_target_pct:.2f}%.")
        paragraph(f"Threshold {crop.threshold_ds_m} dS/m ({crop.threshold_origin}) | "
                  f"Slope {crop.slope_pct_per_ds_m} percentage points per dS/m ({crop.slope_origin})"
                  f"{f' | Crop reference {crop.reference_id}' if crop.reference_id else ''}.")
        paragraph(f"{irrigation.label} | Efficiency {irrigation.efficiency_pct}% ({irrigation.efficiency_origin})"
                  f"{f' | Efficiency reference {irrigation.reference_id}' if irrigation.reference_id else ''} | "
                  f"ETc {field.etc_in} in | Effective rain {field.effective_rain_in} in | "
                  f"Effective leaching credit {field.leaching_credit_pct}%.")
        if field.et_estimate:
            estimate = field.et_estimate
            origin = "Used as entered" if field.etc_in == estimate.etc_in else "Adjusted for this field"
            paragraph(f"ET starting estimate {estimate.etc_in} in | {estimate.location} | {estimate.source_crop} | "
                      f"{estimate.reference_id} | {origin}.")
        if row.depths:
            depths = row.depths
            paragraph(f"Calculated depths (in): crop deficit {depths.net_crop_in:.2f}, crop-only gross "
                      f"{depths.crop_only_gross_in:.2f}, credited existing drainage {depths.credited_existing_in:.2f}, "
                      f"required effective drainage {depths.theoretical_leach_in:.2f}, extra gross maintenance "
                      f"{depths.additional_gross_in:.2f}, modeled effective drainage {depths.effective_drainage_in:.2f}.")
        for warning in row.warnings:
            paragraph(warning)
        if field.notes:
            paragraph(f"Field notes: {field.notes}")

    story.append(PageBreak())
    paragraph("Scientific methods", h1)
    methods = (ROOT / "docs/methods.md").read_text(encoding="utf-8")
    for block in methods.strip().split("\n\n"):
        if block.startswith("## "):
            paragraph(block.removeprefix("## "), h2)
        else:
            paragraph(block.replace("≥", ">=").replace("−", "-").replace("–", "-"), method_text)
    paragraph("Scientific references", h1)
    for key, reference in {**REFERENCES, **references}.items():
        safe_url = quoteattr(reference.url)
        citation = escape(f"{key} | {reference.citation}")
        story.append(Paragraph(f"{citation}<br/><link href={safe_url} color={quoteattr(BROWN)}>"
                               f"{escape(reference.url)}</link>", bibliography))
    for number, run in enumerate(optimization_runs, 1):
        story.append(PageBreak())
        story.extend(_optimization_story(run, title=f"Optimization comparison - Run {number}"))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def _document(output, title):
    return SimpleDocTemplate(output, pagesize=letter, title=title, author=CREATOR,
                             leftMargin=43, rightMargin=43, topMargin=41, bottomMargin=54)


def optimization_report(farm_name, year, run, *, generated=None):
    generated = generated or date.today()
    output = BytesIO()
    title = "Optimization comparison"
    doc = _document(output, f"{TITLE} - {title} - {farm_name}")
    story = _optimization_story(run, title=title, subtitle=f"{farm_name or 'Farm'} | {year} planning year | "
                                                          f"Generated {generated.isoformat()}")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def _optimization_story(run, *, title, subtitle=None):
    dark = colors.HexColor(DARK_GREEN)
    green = colors.HexColor(LIGHT_GREEN)
    brown = colors.HexColor(BROWN)
    body = ParagraphStyle("OptimizationBody", fontName="Helvetica", fontSize=10, leading=14,
                          textColor=dark, spaceAfter=8)
    heading = ParagraphStyle("OptimizationHeading", parent=body, fontName="Helvetica-Bold",
                             fontSize=14, leading=18, spaceBefore=10, keepWithNext=True)
    main = ParagraphStyle("OptimizationTitle", parent=heading, fontSize=24, leading=29, spaceBefore=0)
    cell = ParagraphStyle("OptimizationCell", parent=body, fontSize=8, leading=10.5, spaceAfter=0)
    header = ParagraphStyle("OptimizationHeader", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    story = []

    def paragraph(text, style=body):
        story.append(Paragraph(escape(text), style))

    def table(headers, rows, widths):
        story.append(_table(headers, rows, widths, cell, header))
        story.append(Spacer(1, 7))

    paragraph(title, main)
    if subtitle:
        paragraph(subtitle)
    paragraph(f"Starting plan: {run.starting_plan.name} | Model v{run.model_version} | "
              f"Run completed {run.completed_at:%Y-%m-%d %H:%M:%S %z}")
    selected = ", ".join(run.settings.leaching_field_ids) or "None"
    paragraph(f"Fields requiring salinity leaching: {selected}. Gross revenue is before production costs. "
              "The model estimates yield at the entered soil salinity and applies water limits separately to each source.")

    comparisons = []
    references = [("Starting plan", run.starting_plan, run.starting_revenue)]
    if run.baseline:
        references.insert(0, ("Baseline", run.baseline, run.baseline_revenue))
    for label, scenario, revenue in references:
        result = evaluate_scenario(scenario)
        if shortfalls := crop_shortfalls(result):
            limits = ", ".join(f"{source} ({gap:,.1f} AF)" for source, gap in shortfalls.items())
            paragraph(f"{label} is a full-irrigation benchmark. Crop water demand exceeds delivery at {limits}.")
        comparisons.append((reference_label(label, result), scenario, result, revenue, bool(shortfalls)))
    if excluded := excluded_starting_crops(run):
        paragraph("Starting crops excluded from the search: "
                  + ", ".join(f"{field} ({crop})" for field, crop in excluded.items()) + ".")
    for outcome in run.outcomes:
        label = MODE[outcome.requires_leaching]
        if outcome.plan:
            comparisons.append((label, outcome.plan, evaluate_scenario(outcome.plan), outcome.gross_revenue, False))
        else:
            paragraph(f"{label}: " + " ".join(outcome.diagnostics))

    paragraph("Estimated gross revenue", heading)
    chart = Drawing(510, 28 * len(comparisons) + 6)
    scale = max(1.0, *(revenue for _, _, _, revenue, _ in comparisons))
    for index, (label, _, _, revenue, benchmark) in enumerate(comparisons):
        y = 28 * (len(comparisons) - index - 1) + 10
        chart.add(String(0, y + 3, label, fontName="Helvetica", fontSize=8, fillColor=dark))
        chart.add(Line(194, y + 6, 395, y + 6, strokeColor=colors.HexColor(PALE_GREEN)))
        chart.add(Rect(194, y, 201 * (revenue / scale), 12, fillColor=brown if benchmark else green, strokeColor=None))
        chart.add(String(506, y + 2, f"${revenue:,.0f}", textAnchor="end", fontName="Helvetica-Bold",
                         fontSize=9, fillColor=dark))
    story.append(chart)

    paragraph("Irrigation by source (acre-feet)", heading)
    table(["Plan", "Source", "Delivery", "Crop water", "Extra leaching budgeted", "Planned total"], [
        (label, source.source.id, _number(source.source.delivery_af), _number(source.crop_only_af),
         _number(source.planned_demand_af - source.crop_only_af) if source.planned_demand_af is not None else "Undetermined",
         _number(source.planned_demand_af))
        for label, _, result, _, _ in comparisons for source in result.sources
    ], [135, 88, 60, 67, 83, 81])

    paragraph("Crop choices and yield at current soil salinity", heading)
    table(["Field", "Plan", "Crop", "Current ECe (dS/m)", "Estimated yield (%)", "Leaching coverage"], [
        (field.field.id, label, field.field.crop.label, _number(field.field.current_ece_ds_m, 2),
         _number(field.current_yield_pct), source.field_leaching_status(field))
        for label, _, result, _, _ in comparisons for source in result.sources for field in source.fields
    ], [76, 120, 94, 62, 62, 100])

    paragraph("Optimization inputs", heading)
    quote_labels = {key: quote.crop.label for key, quote in run.settings.quotes_by_crop.items()}
    table(["Field", "Eligible crops", "Leaching required"], [
        (field, ", ".join(quote_labels.get(key, key[0]) for key in keys), "Yes" if field in run.settings.leaching_field_ids else "No")
        for field, keys in run.settings.eligible.items()
    ], [105, 315, 94])
    table(["Crop", "Sale unit", "Yield per acre without salinity loss", "Price per unit ($)", "Replacement crop ET (in)"], [
        (quote.crop.label, quote.unit, _number(quote.expected_yield, 3), _number(quote.price, 2),
         _number(quote.alternative_et_in, 2) if quote.alternative_et_in is not None else "Uses saved field ET")
        for quote in sorted(run.settings.quotes, key=lambda row: row.crop.label.casefold())
    ], [137, 82, 104, 81, 110])
    paragraph("Replacement crop ET applies when the selected crop differs from the starting crop. The leaching "
              "calculation uses each candidate crop's salinity threshold and assumes effective drainage.")
    return story
