# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import date
from uuid import uuid4

import streamlit as st
from pydantic import ValidationError

from config.branding import ROOT, VERSION
from data.catalog import REFERENCES
from models.crop_response import target_ece
from schemas.farm import (
    DEFAULT_DESIRED_YIELD_PCT, SCHEMA_VERSION, FarmPlan, FieldPlan, OptimizationArchive, Scenario, WaterSource, load_plan,
)


def identifier():
    return uuid4().hex


def as_draft(scenario: Scenario) -> dict:
    draft = scenario.model_dump()
    for kind in ("fields", "sources"):
        draft[kind] = [{**row, "_key": identifier()} for row in draft[kind]]
    return draft


def install_plan(plan: FarmPlan):
    optimization = plan.optimization or OptimizationArchive()
    st.session_state.workspace = {
        "farm_name": plan.farm_name, "planning_year": plan.planning_year, "notes": plan.notes,
        "active_scenario_id": plan.active_scenario_id,
        "scenarios": {scenario.id: as_draft(scenario) for scenario in plan.scenarios},
        "references": {**REFERENCES, **plan.references},
        "epoch": identifier(),
        "reviewed": True,
        "optimization": {
            "starting-plan": optimization.starting_plan_id,
            "inputs": {settings.starting_plan_id: settings for settings in optimization.inputs},
            "runs": list(optimization.runs),
        },
    }
    st.session_state.pop("selected_field", None)
    assign_scenario_numbers()


def initialize():
    if "workspace" not in st.session_state:
        st.session_state.workspace = {
            "farm_name": "", "planning_year": date.today().year, "notes": "",
            "active_scenario_id": "baseline",
            "scenarios": {"baseline": {"id": "baseline", "name": "Baseline", "fields": [], "sources": []}},
            "references": dict(REFERENCES), "epoch": identifier(), "reviewed": False,
        }
    if "next_scenario_number" not in workspace():
        assign_scenario_numbers()


def workspace():
    return st.session_state.workspace


def active():
    state = workspace()
    return state["scenarios"][state["active_scenario_id"]]


def baseline_id():
    scenarios = workspace()["scenarios"]
    return "baseline" if "baseline" in scenarios else next(iter(scenarios))


def scenario_ids():
    first = baseline_id()
    return [first, *(key for key in workspace()["scenarios"] if key != first)]


def assign_scenario_numbers():
    state = workspace()
    alternatives = [state["scenarios"][key] for key in scenario_ids()[1:]]
    used = {draft["number"] for draft in state["scenarios"].values() if draft.get("number") is not None}
    number = 1
    for draft in alternatives:
        if draft.get("number") is None:
            while number in used:
                number += 1
            draft["number"] = number
            used.add(number)
    state["next_scenario_number"] = max(used, default=0) + 1


def scenario_label(scenario_id, *, include_name=False):
    if scenario_id == baseline_id():
        return "Baseline"
    draft = workspace()["scenarios"][scenario_id]
    label = f"Scenario {draft['number']}"
    return f"{label} · {draft['name']}" if include_name else label


def field_names():
    names = {}
    for scenario_id in scenario_ids():
        for field in workspace()["scenarios"][scenario_id]["fields"]:
            names.setdefault(field["id"].casefold(), field["id"])
    return names


def ui_key(name):
    return f"{workspace()['epoch']}/{active()['id']}/{name}"


def start_scenario_editor(template_id, scenario_id, *, field_id=None):
    st.session_state[ui_key("scenario-editor")] = {
        "template_id": template_id, "id": scenario_id, "key": identifier(), "field_id": field_id,
    }


def save_scenario(scenario_id, name, fields, sources, *, leaching_field_ids=None):
    state = workspace()
    scenarios = state["scenarios"]
    if any(draft["name"].casefold() == name.casefold() and key != scenario_id for key, draft in scenarios.items()):
        raise ValueError("Choose a unique scenario name.")
    if scenario_id == baseline_id():
        raise ValueError("Edit the baseline in Farm Setup.")
    number = scenarios[scenario_id]["number"] if scenario_id in scenarios else state["next_scenario_number"]
    scenario = Scenario(id=scenario_id, name=name, number=number, fields=fields, sources=sources,
                        leaching_field_ids=leaching_field_ids)
    scenarios[scenario_id] = as_draft(scenario)
    state["next_scenario_number"] = max(state["next_scenario_number"], number + 1)
    return scenario


def activate(scenario_id):
    workspace()["active_scenario_id"] = scenario_id
    workspace()["epoch"] = identifier()
    st.session_state.pop("selected_field", None)


def demo_plan():
    return load_plan((ROOT / "examples/example_farm.json").read_bytes())


def field_model(draft):
    values = {key: value for key, value in draft.items() if key in FieldPlan.model_fields}
    crop = values.get("crop") or {}
    if not values.get("target_ece_override"):
        try:
            values["target_ece_ds_m"] = target_ece(
                values.get("desired_yield_pct", DEFAULT_DESIRED_YIELD_PCT),
                crop.get("threshold_ds_m"), crop.get("slope_pct_per_ds_m"),
            )
        except ValueError:
            # Supply a placeholder so validation can identify the invalid input.
            values["target_ece_ds_m"] = 0
    return FieldPlan.model_validate(values)


def describe_errors(error):
    if not isinstance(error, ValidationError):
        return [str(error)]
    labels = {
        "etc_in": "seasonal crop ET (in)", "effective_rain_in": "effective precipitation (in)",
        "current_ece_ds_m": "current soil ECe", "source_id": "assigned water source",
        "ecw_ds_m": "irrigation water ECw", "delivery_af": "expected farm delivery (AF)",
        "crop": "crop and coefficients", "irrigation": "irrigation method and efficiency",
        "slope_pct_per_ds_m": "yield-loss slope", "threshold_ds_m": "crop threshold",
        "farm_name": "farm name", "schema_version": "schema version",
    }
    messages = []
    for detail in error.errors(include_url=False):
        path = " › ".join(
            f"row {item + 1}" if isinstance(item, int) else labels.get(item, item.replace("_", " "))
            for item in detail["loc"]
        )
        reason = detail["msg"].removeprefix("Value error, ")
        if detail["type"] in {"missing", "string_type", "float_type", "string_too_short", "model_type"}:
            reason = "Enter a value."
        messages.append(f"{path} — {reason}" if path else reason)
    return messages


def validate_scenario(draft):
    errors = []
    fields = []
    sources = []
    for rows, parse, output, label in (
        (draft["fields"], field_model, fields, "Field"),
        (draft["sources"], source_model, sources, "Water source"),
    ):
        if not rows:
            errors.append(f"Add at least one {label.lower()}.")
        for index, row in enumerate(rows, 1):
            try:
                output.append(parse(row))
            except (ValidationError, ValueError) as error:
                errors.extend(f"{label} {index} ({row.get('id') or 'no ID'}). {msg}"
                              for msg in describe_errors(error))
    if errors:
        return None, errors
    try:
        return Scenario(id=draft["id"], name=draft["name"], number=draft.get("number"), fields=fields, sources=sources,
                        leaching_field_ids=draft.get("leaching_field_ids")), []
    except ValidationError as error:
        return None, describe_errors(error)


def validated_plan():
    state = workspace()
    scenarios = []
    messages = []
    for draft in state["scenarios"].values():
        scenario, errors = validate_scenario(draft)
        if errors:
            messages.extend(f"{draft['name']}. {error}" for error in errors)
        else:
            scenarios.append(scenario)
    if messages:
        return None, messages
    try:
        optimization = state.get("optimization", {})
        inputs = tuple(settings for key, settings in optimization.get("inputs", {}).items() if key in state["scenarios"])
        runs = tuple(optimization.get("runs", ()))
        archive = OptimizationArchive(starting_plan_id=optimization.get("starting-plan"), inputs=inputs, runs=runs)
        return FarmPlan(
            schema_version=SCHEMA_VERSION, app_version=VERSION,
            farm_name=state["farm_name"], planning_year=state["planning_year"], notes=state["notes"],
            active_scenario_id=state["active_scenario_id"], scenarios=scenarios, references=state["references"],
            optimization=archive if inputs or runs else None,
        ), []
    except ValidationError as error:
        return None, describe_errors(error)


def source_model(draft):
    return WaterSource.model_validate({key: value for key, value in draft.items() if key != "_key"})


def save_entry(rows, record, selected):
    """Add a validated entry or replace the selected row, keeping its internal key."""
    if any(row is not selected and row["id"].casefold() == record.id.casefold() for row in rows):
        raise ValueError(f"The ID {record.id!r} is already in use.")
    if selected is None:
        rows.append({**record.model_dump(), "_key": identifier()})
    else:
        rows[rows.index(selected)] = {**record.model_dump(), "_key": selected["_key"]}


def save_source(scenario, source, selected, field_keys):
    """Save a source and assign the chosen fields to it within this scenario."""
    previous_id = selected["id"] if selected else None
    save_entry(scenario["sources"], source, selected)
    keys = set(field_keys)
    for field in scenario["fields"]:
        if field["_key"] in keys:
            field["source_id"] = source.id
        elif field.get("source_id") == previous_id:
            field["source_id"] = None
