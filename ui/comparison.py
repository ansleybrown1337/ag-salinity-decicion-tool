# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import altair as alt
import pandas as pd

from config.branding import BROWN, DARK_GREEN, LIGHT_GREEN
from models.crop_response import relative_yield

CROP_COMPONENT = "Crop-only irrigation"
LEACH_COMPONENT = "Extra irrigation for leaching"
SUPPLY_LABEL = "Expected farm delivery"
CURRENT_SALINITY = "Current salinity"
TARGET_SALINITY = "Target salinity"


def water_demand_chart(budgets, *, row_label):
    """Plot additive gross irrigation components and any supplied delivery markers."""
    categories = [row["Plan"] for row in budgets]
    components = [
        {"Plan": row["Plan"], "Component": label, "Water": value, "Order": index}
        for row in budgets
        for index, (label, value) in enumerate((
            (CROP_COMPONENT, row["Crop-only (AF)"]), (LEACH_COMPONENT, row["Extra leaching (AF)"]),
        ))
        if value is not None
    ]
    deliveries = [{"Plan": row["Plan"], "Water": row["Delivery (AF)"], "Supply": SUPPLY_LABEL}
                  for row in budgets if row.get("Delivery (AF)") is not None]
    y = alt.Y("Plan:N", sort=categories, title=row_label, scale=alt.Scale(domain=categories),
              axis=alt.Axis(labelLimit=225))
    x = alt.X("Water:Q", title="Irrigation water (acre-feet)")
    bars = alt.Chart(pd.DataFrame(components, columns=["Plan", "Component", "Water", "Order"])).mark_bar(
        size=18,
    ).encode(
        y=y, x=alt.X("Water:Q", title="Irrigation water (acre-feet)", stack="zero"),
        color=alt.Color("Component:N", title=None, legend=alt.Legend(orient="top"), scale=alt.Scale(
            domain=[CROP_COMPONENT, LEACH_COMPONENT], range=[LIGHT_GREEN, BROWN],
        )),
        order=alt.Order("Order:Q", sort="ascending"),
        tooltip=["Plan:N", "Component:N", alt.Tooltip("Water:Q", title="Acre-feet", format=",.1f")],
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
            tooltip=["Plan:N", alt.Tooltip("Water:Q", title=f"{SUPPLY_LABEL} (AF)", format=",.1f")],
        )
        chart = (bars + markers).resolve_scale(color="independent")
    return chart.properties(height=alt.Step(34))


def yield_response_chart(options):
    """Plot model response, current soil ECe and each option's maintenance target."""
    end = 1.3 * max(max(field.current_ece_ds_m, field.target_ece_ds_m, field.crop.threshold_ds_m, 1)
                    for _, field, _ in options)
    curves = []
    markers = []
    names = [label for label, _, _ in options]
    for label, field, result in options:
        threshold = field.crop.threshold_ds_m
        slope = field.crop.slope_pct_per_ds_m
        points = sorted({0, field.current_ece_ds_m, field.target_ece_ds_m, threshold,
                         min(end, threshold + 100 / slope), end})
        curves.extend({
            "Plan": label, "ECe": point, "Yield": relative_yield(point, threshold, slope),
        } for point in points)
        markers.extend([
            {"Plan": label, "ECe": field.current_ece_ds_m, "Yield": result.current_yield_pct, "Point": CURRENT_SALINITY},
            {"Plan": label, "ECe": field.target_ece_ds_m, "Yield": result.yield_at_target_pct, "Point": TARGET_SALINITY},
        ])
    x = alt.X("ECe:Q", title="Root-zone salinity, ECe (dS/m)")
    y = alt.Y("Yield:Q", title="Relative yield (%)", scale=alt.Scale(domain=[0, 105]))
    color = alt.Color("Plan:N", title=None, legend=alt.Legend(orient="top"), scale=alt.Scale(
        domain=names, range=[DARK_GREEN, BROWN][:len(names)],
    ))
    position = [alt.Tooltip("ECe:Q", title="Salinity (dS/m)", format=".2f"),
                alt.Tooltip("Yield:Q", title="Relative yield (%)", format=".1f")]
    lines = alt.Chart(pd.DataFrame(curves)).mark_line(strokeWidth=3).encode(
        x=x, y=y, color=color, strokeDash=alt.StrokeDash(
            "Plan:N", title=None, scale=alt.Scale(domain=names, range=[[1, 0], [7, 4]][:len(names)]),
        ), tooltip=["Plan:N", *position],
    )
    points = alt.Chart(pd.DataFrame(markers)).mark_point(size=105, strokeWidth=2.5).encode(
        x=x, y=y, color=color, shape=alt.Shape(
            "Point:N", title=None, legend=alt.Legend(orient="top"),
            scale=alt.Scale(domain=[CURRENT_SALINITY, TARGET_SALINITY], range=["circle", "diamond"]),
        ), tooltip=["Plan:N", "Point:N", *position],
    )
    return (lines + points).properties(height=285)
