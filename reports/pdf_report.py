# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import CondPageBreak, Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from config.branding import (
    BROWN, COPYRIGHT, CREATOR, CREATOR_URL, DARK_GREEN, LICENSE, LIGHT_GREEN, PALE_GREEN, ROOT, TITLE, VERSION, WHITE,
    logo_path,
)
from data.catalog import REFERENCES


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


def management_report(farm_name, year, notes, scenario, result, references, *, generated=None):
    """Generate a printable PDF in memory for the selected scenario and its results."""
    generated = generated or date.today()
    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=letter, title=f"{TITLE} - {farm_name}", author=CREATOR,
        leftMargin=43, rightMargin=43, topMargin=41, bottomMargin=54,
    )
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
        ("Extra gross field water for maintenance (AF)", _number(result.complete_sum("added_leach_field_af"))),
        ("Total planned field irrigation demand (AF)", _number(result.field_demand_af)),
        ("Combined field surplus (+) / deficit (-), AF", _number(result.field_balance_af)),
        ("Known assigned-source shortfall", f"{result.source_shortfall_af:,.1f} AF"),
    ], [330, 184])
    paragraph("Management interpretation", h2)
    paragraph(result.allocation_conclusion)
    if result.field_demand_af is not None:
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
    table(["Water source ID", "Farm delivery (AF)", "Demand (AF)", "Balance (AF)", "Assessment"], [
        (row.source.id, _number(row.source.delivery_af),
         _number(row.demand_af) if row.demand_af is not None else f"{row.known_demand_af:,.1f} known",
         _number(row.balance_af), row.assessment)
        for row in result.sources
    ], [173, 68, 78, 78, 117])
    story.append(CondPageBreak(120))
    paragraph("Field salinity and irrigation results", table_heading)
    table(["Field / crop", "Area (ac)", "Current / target ECe (dS/m)", "Current / desired yield (%)",
           "LR (%)", "Gross depth (in)", "Field volume (AF)"], [
        (f"{row.field.id} / {row.field.crop.label}", _number(row.field.acres),
         f"{row.field.current_ece_ds_m:.2f} / {row.field.target_ece_ds_m:.2f}",
         f"{row.current_yield_pct:.1f} / {row.field.desired_yield_pct:g}",
         _number(row.lr * 100, 2) if row.lr is not None else "Infeasible",
         _number(row.depths.gross_in) if row.depths else "—",
         _number(row.field_af))
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
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()
