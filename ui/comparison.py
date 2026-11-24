# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import altair as alt
import pandas as pd

from config.branding import BROWN, DARK_GREEN, LIGHT_GREEN
from models.crop_response import relative_yield
from ui.shared import target_basis

CROP_COMPONENT = "Crop-only irrigation"
LEACH_COMPONENT = "Extra irrigation for salinity leaching"
REMAINING_COMPONENT = "Water remaining (farm total)"
SUPPLY_LABEL = "Expected farm delivery"
CURRENT_SALINITY = "Current salinity"
TARGET_SALINITY = "Target salinity"
SCENARIO_COLORS = (DARK_GREEN, BROWN, "#336CA1", "#783E8A", "#886200", "#9C4251", "#26796D", "#565C73")
SCENARIO_DASHES = ([1, 0], [7, 4], [3, 3], [10, 3, 2, 3])


def farm_water_budget(name, result):
    balance = result.field_balance_af
    return {
        "Plan": name, "Crop-only (AF)": result.complete_sum("crop_only_af"),
        "Extra leaching (AF)": result.complete_sum("added_leach_field_af"),
        "Delivery (AF)": result.field_supply_af,
        "Water remaining (AF)": balance if balance is not None and balance > 1e-8 else None,
    }


def water_demand_chart(budgets, *, row_label, details=()):
    """Plot additive gross irrigation components and any supplied delivery markers."""
    categories = [row["Plan"] for row in budgets]
    components = [
        {"Plan": row["Plan"], "Component": label, "Water": value, "Order": index,
         **{detail: row[detail] for detail in details}}
        for row in budgets
        for index, (label, value) in enumerate((
            (CROP_COMPONENT, row["Crop-only (AF)"]), (LEACH_COMPONENT, row["Extra leaching (AF)"]),
            (REMAINING_COMPONENT, row.get("Water remaining (AF)")),
        ))
        if value is not None
    ]
    deliveries = [{"Plan": row["Plan"], "Water": row["Delivery (AF)"], "Supply": SUPPLY_LABEL,
                   **{detail: row[detail] for detail in details}}
                  for row in budgets if row.get("Delivery (AF)") is not None]
    y = alt.Y("Plan:N", sort=categories, title=row_label, scale=alt.Scale(domain=categories),
              axis=alt.Axis(labelLimit=225))
    x = alt.X("Water:Q", title="Irrigation water (acre-feet)")
    labels = [CROP_COMPONENT, LEACH_COMPONENT]
    colors = [LIGHT_GREEN, BROWN]
    if any(row["Component"] == REMAINING_COMPONENT for row in components):
        labels.append(REMAINING_COMPONENT)
        colors.append("#9BAFC5")
    bars = alt.Chart(pd.DataFrame(components, columns=["Plan", "Component", "Water", "Order", *details])).mark_bar(
        size=18,
    ).encode(
        y=y, x=alt.X("Water:Q", title="Irrigation water (acre-feet)", stack="zero"),
        color=alt.Color("Component:N", title=None, legend=alt.Legend(orient="top", labelLimit=260), scale=alt.Scale(
            domain=labels, range=colors,
        )),
        order=alt.Order("Order:Q", sort="ascending"),
        tooltip=["Plan:N", *(f"{detail}:N" for detail in details), "Component:N",
                 alt.Tooltip("Water:Q", title="Acre-feet", format=",.1f")],
    )
    chart = bars
    if deliveries:
        markers = alt.Chart(pd.DataFrame(deliveries)).mark_tick(
            orient="vertical", thickness=3, size=26, opacity=1,
        ).encode(
            y=y, x=x,
            color=alt.Color("Supply:N", title=None, scale=alt.Scale(domain=[SUPPLY_LABEL], range=[DARK_GREEN]),
                            legend=alt.Legend(orient="top", symbolType="M0,-1L0,1",
                                              symbolStrokeColor=DARK_GREEN, symbolStrokeWidth=3)),
            tooltip=["Plan:N", *(f"{detail}:N" for detail in details),
                     alt.Tooltip("Water:Q", title=f"{SUPPLY_LABEL} (AF)", format=",.1f")],
        )
        chart = (bars + markers).resolve_scale(color="independent")
    return chart.properties(height=alt.Step(34))


def field_yield_chart(fields):
    rows = [
        {
            "Field": result.field.id, "Crop": result.field.crop.label, "ECe": result.field.current_ece_ds_m,
            "Estimated yield (%)": result.current_yield_pct, "Yield lost (%)": 100 - result.current_yield_pct,
            "Component": label, "Percent": percent, "Order": index,
        }
        for result in fields
        for index, (label, percent) in enumerate((
            ("Estimated yield retained", result.current_yield_pct),
            ("Estimated yield lost to salinity", 100 - result.current_yield_pct),
        ))
    ]
    return alt.Chart(pd.DataFrame(rows)).mark_bar(size=18).encode(
        y=alt.Y("Field:N", sort=[result.field.id for result in fields], title=None),
        x=alt.X("Percent:Q", stack="zero", title="Relative to potential yield (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Component:N", title=None, scale=alt.Scale(
            domain=["Estimated yield retained", "Estimated yield lost to salinity"], range=[LIGHT_GREEN, BROWN],
        ), legend=alt.Legend(orient="top", labelLimit=250)),
        order=alt.Order("Order:Q", sort="ascending"),
        tooltip=[
            "Field:N", "Crop:N", alt.Tooltip("ECe:Q", title="Current soil salinity (dS/m)", format=".2f"),
            alt.Tooltip("Estimated yield (%):Q", format=".1f"), alt.Tooltip("Yield lost (%):Q", format=".1f"),
        ],
    ).properties(height=alt.Step(34))


def yield_response_chart(options, *, scenario_positions):
    """Plot model response, current soil ECe and each option's maintenance target."""
    end = 1.3 * max(
        max(item.field.current_ece_ds_m, item.field.target_ece_ds_m, item.field.crop.threshold_ds_m, 1)
        for _, _, item in options
    )
    curves = []
    markers = []
    names = [label for label, _, _ in options]
    for label, name, result in options:
        field = result.field
        threshold = field.crop.threshold_ds_m
        slope = field.crop.slope_pct_per_ds_m
        points = sorted({0, field.current_ece_ds_m, field.target_ece_ds_m, threshold,
                         min(end, threshold + 100 / slope), end})
        plan = {"Plan": label, "Scenario name": name, "Crop": field.crop.label}
        curves.extend({**plan, "ECe": point, "Yield": relative_yield(point, threshold, slope)} for point in points)
        markers.extend([
            {**plan, "ECe": field.current_ece_ds_m, "Yield": result.current_yield_pct,
             "Point": CURRENT_SALINITY, "Target basis": target_basis(field)},
            {**plan, "ECe": field.target_ece_ds_m, "Yield": result.yield_at_target_pct,
             "Point": TARGET_SALINITY, "Target basis": target_basis(field)},
        ])
    x = alt.X("ECe:Q", title="Root-zone salinity, ECe (dS/m)")
    y = alt.Y("Yield:Q", title="Relative yield (%)", scale=alt.Scale(domain=[0, 105]))
    color = alt.Color("Plan:N", title=None, legend=alt.Legend(orient="top", labelLimit=260), scale=alt.Scale(
        domain=names, range=[SCENARIO_COLORS[index % len(SCENARIO_COLORS)] for index in scenario_positions],
    ))
    position = [alt.Tooltip("ECe:Q", title="Salinity (dS/m)", format=".2f"),
                alt.Tooltip("Yield:Q", title="Relative yield (%)", format=".1f")]
    lines = alt.Chart(pd.DataFrame(curves)).mark_line(strokeWidth=3).encode(
        x=x, y=y, color=color, strokeDash=alt.StrokeDash(
            "Plan:N", title=None, scale=alt.Scale(
                domain=names, range=[SCENARIO_DASHES[index % len(SCENARIO_DASHES)] for index in scenario_positions],
            ),
        ), tooltip=["Plan:N", "Scenario name:N", "Crop:N", *position],
    )
    points = alt.Chart(pd.DataFrame(markers)).mark_point(size=105, strokeWidth=2.5).encode(
        x=x, y=y, color=color, shape=alt.Shape(
            "Point:N", title=None, legend=alt.Legend(orient="top"),
            scale=alt.Scale(domain=[CURRENT_SALINITY, TARGET_SALINITY], range=["circle", "diamond"]),
        ), tooltip=["Plan:N", "Scenario name:N", "Crop:N", "Point:N", *position, "Target basis:N"],
    )
    return (lines + points).properties(height=285)
