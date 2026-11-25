# Copyright (C) 2026 AgriData Solutions, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from config.branding import VERSION
from models.crop_response import target_ece

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Notes = Annotated[str, StringConstraints(max_length=2000)]
Nonnegative = Annotated[float, Field(ge=0, strict=True)]
Positive = Annotated[float, Field(gt=0, strict=True)]
Percentage = Annotated[float, Field(ge=0, le=100, strict=True)]
PositivePercentage = Annotated[float, Field(gt=0, le=100, strict=True)]
Origin = Literal["Published default", "User override", "Custom parameter"]
SCHEMA_VERSION = "2.0"
DEFAULT_DESIRED_YIELD_PCT = 100.0


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class Reference(Record):
    authors: ShortText
    title: str
    year: int
    publication: str
    url: Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=300)]
    doi: str | None = None
    supports: tuple[str, ...]

    @property
    def citation(self) -> str:
        return f"{self.authors} ({self.year}). {self.title}. {self.publication}."


class Crop(Record):
    id: ShortText
    label: ShortText
    scientific_name: str = ""
    endpoint: ShortText
    threshold_ds_m: Nonnegative
    slope_pct_per_ds_m: Positive
    threshold_origin: Origin
    slope_origin: Origin
    reference_id: ShortText | None = None

    @model_validator(mode="after")
    def check_provenance(self):
        origins = (self.threshold_origin, self.slope_origin)
        if self.id == "custom":
            if any(origin != "Custom parameter" for origin in origins):
                raise ValueError("Custom crop coefficients must be marked as custom.")
        elif not self.reference_id or "Custom parameter" in origins:
            raise ValueError("A crop preset needs a reference and default or override markers.")
        return self


class Method(Record):
    id: ShortText
    label: ShortText
    efficiency_pct: PositivePercentage
    efficiency_origin: Origin
    published_range_pct: tuple[PositivePercentage, PositivePercentage] | None = None
    reference_id: ShortText | None = None

    @model_validator(mode="after")
    def check_provenance(self):
        if self.id == "custom":
            if self.efficiency_origin != "Custom parameter" or self.published_range_pct:
                raise ValueError("A custom irrigation method needs a custom efficiency.")
        else:
            bounds = self.published_range_pct
            if not self.reference_id or not bounds or bounds[0] > bounds[1]:
                raise ValueError("An irrigation preset needs a reference and an ordered efficiency range.")
            if self.efficiency_origin == "Custom parameter":
                raise ValueError("A preset efficiency must be marked as a default or override.")
            if self.efficiency_origin == "Published default" and self.efficiency_pct != sum(bounds) / 2:
                raise ValueError("A default irrigation efficiency must equal the published range midpoint.")
        return self


class CropEtEstimate(Record):
    """A saved location-specific starting value, separate from the field's ET input."""

    etc_in: Nonnegative
    location: ShortText
    source_crop: ShortText
    reference_id: ShortText


class WaterSource(Record):
    id: ShortText
    delivery_af: Nonnegative
    ecw_ds_m: Nonnegative
    source_type: Literal["Surface water", "Canal water", "Groundwater", "Other"]
    notes: Notes = ""


class _LegacyWaterSource(Record):
    id: ShortText
    name: ShortText
    allocation_af: Nonnegative
    ecw_ds_m: Nonnegative
    source_type: Literal["Surface water", "Canal water", "Groundwater", "Other"]
    meter: Literal["Diversion", "Farm turnout", "Field"]
    conveyance_efficiency_pct: PositivePercentage | None = None
    notes: Notes = ""

    @model_validator(mode="after")
    def check_meter(self):
        if self.meter == "Field" and self.conveyance_efficiency_pct not in (None, 100):
            raise ValueError("A field measurement uses 100% delivery to the field.")
        if self.meter != "Field" and self.conveyance_efficiency_pct is None:
            raise ValueError("Enter conveyance efficiency from the selected meter to the field.")
        return self

    @property
    def delivery_fraction(self) -> float:
        return (self.conveyance_efficiency_pct or 100) / 100


class FieldPlan(Record):
    id: ShortText
    acres: Positive
    crop: Crop
    current_ece_ds_m: Nonnegative
    irrigation: Method
    source_id: ShortText | None = None
    desired_yield_pct: PositivePercentage = DEFAULT_DESIRED_YIELD_PCT
    target_ece_ds_m: Nonnegative
    target_ece_override: bool = False
    etc_in: Nonnegative
    et_estimate: CropEtEstimate | None = None
    effective_rain_in: Nonnegative
    leaching_credit_pct: Percentage = 0
    notes: Notes = ""

    @model_validator(mode="after")
    def check_target(self):
        if self.target_ece_override:
            if self.target_ece_ds_m <= 0:
                raise ValueError("A manual target ECe must be greater than zero.")
        elif self.target_ece_ds_m != target_ece(
            self.desired_yield_pct, self.crop.threshold_ds_m, self.crop.slope_pct_per_ds_m
        ):
            raise ValueError("Derived target ECe must agree with crop coefficients and desired yield.")
        return self


class _LegacyFieldPlan(FieldPlan):
    name: ShortText
    source_id: ShortText
    desired_yield_pct: PositivePercentage = 90


class Scenario(Record):
    id: ShortText
    name: ShortText
    number: Annotated[int, Field(ge=1, strict=True)] | None = Field(default=None, exclude_if=lambda value: value is None)
    leaching_field_ids: tuple[ShortText, ...] | None = Field(default=None, exclude_if=lambda value: value is None)
    fields: Annotated[tuple[FieldPlan, ...], Field(min_length=1)]
    sources: Annotated[tuple[WaterSource, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def check_assignments(self):
        for records, label in ((self.fields, "field"), (self.sources, "water source")):
            ids = [record.id.casefold() for record in records]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Each {label} ID must be unique, ignoring letter case.")
        source_ids = {source.id for source in self.sources}
        if self.leaching_field_ids is not None:
            selected = set(self.leaching_field_ids)
            if len(selected) != len(self.leaching_field_ids) or not selected.issubset({field.id for field in self.fields}):
                raise ValueError("Leaching selections must identify unique fields in the scenario.")
        for field in self.fields:
            if field.source_id not in source_ids:
                raise ValueError(f"Assign {field.id} to an existing water source in Farm Setup.")
        return self


CropKey = tuple[str] | tuple[str, str, str]


def crop_key(crop: Crop) -> CropKey:
    if crop.id == "custom":
        return (crop.id, crop.label.casefold(), crop.endpoint.casefold())
    return (crop.id,)


class OptimizationQuote(Record):
    crop: Crop
    unit: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    expected_yield: Nonnegative | None = None
    price: Nonnegative | None = None
    alternative_et_in: Nonnegative | None = None


class OptimizationSettings(Record):
    starting_plan_id: ShortText
    eligible: dict[ShortText, tuple[CropKey, ...]]
    leaching_field_ids: tuple[ShortText, ...]
    quotes: tuple[OptimizationQuote, ...]

    @model_validator(mode="after")
    def check_choices(self):
        if len(self.quotes_by_crop) != len(self.quotes):
            raise ValueError("Each crop must have one set of price and yield inputs.")
        if len(set(self.leaching_field_ids)) != len(self.leaching_field_ids):
            raise ValueError("Each leaching field must be selected only once.")
        return self

    @property
    def quotes_by_crop(self):
        return {crop_key(quote.crop): quote for quote in self.quotes}


class OptimizationOutcome(Record):
    requires_leaching: bool
    plan: Scenario | None = None
    gross_revenue: Nonnegative | None = None
    diagnostics: tuple[str, ...] = ()

    @model_validator(mode="after")
    def check_result(self):
        if (self.plan is None) != (self.gross_revenue is None):
            raise ValueError("An optimization result needs both its plan and gross revenue.")
        return self


class OptimizationRun(Record):
    id: ShortText
    completed_at: AwareDatetime
    model_version: ShortText
    settings: OptimizationSettings
    starting_plan: Scenario
    starting_revenue: Nonnegative
    baseline: Scenario | None = None
    baseline_revenue: Nonnegative | None = None
    outcomes: Annotated[tuple[OptimizationOutcome, ...], Field(min_length=1, max_length=2)]

    @model_validator(mode="after")
    def check_comparison(self):
        if (self.baseline is None) != (self.baseline_revenue is None):
            raise ValueError("A baseline comparison needs both its plan and gross revenue.")
        if self.settings.starting_plan_id != self.starting_plan.id:
            raise ValueError("Optimization inputs must identify the starting plan.")
        modes = tuple(outcome.requires_leaching for outcome in self.outcomes)
        expected = (False, True) if self.settings.leaching_field_ids else (False,)
        if modes != expected:
            raise ValueError("Optimization results must match the selected leaching modes.")
        field_ids = {field.id for field in self.starting_plan.fields}
        if field_ids != self.settings.eligible.keys() or not set(self.settings.leaching_field_ids) <= field_ids:
            raise ValueError("Optimization field selections must match the starting plan.")
        used_crops = {key for keys in self.settings.eligible.values() for key in keys}
        plans = [self.starting_plan, *(outcome.plan for outcome in self.outcomes if outcome.plan)]
        if self.baseline:
            plans.append(self.baseline)
        used_crops.update(crop_key(field.crop) for plan in plans for field in plan.fields)
        quotes = self.settings.quotes_by_crop
        if any(key not in quotes or quotes[key].expected_yield is None or quotes[key].price is None or not quotes[key].unit
               for key in used_crops):
            raise ValueError("A completed run must include price, yield, and sale units for every crop it used.")
        for outcome in self.outcomes:
            required = self.settings.leaching_field_ids if outcome.requires_leaching else ()
            if outcome.plan and (outcome.plan.leaching_field_ids != required
                                 or {field.id for field in outcome.plan.fields} != field_ids):
                raise ValueError("Optimized field and leaching selections must match the completed run.")
        return self


class OptimizationArchive(Record):
    starting_plan_id: ShortText | None = None
    inputs: tuple[OptimizationSettings, ...] = ()
    runs: tuple[OptimizationRun, ...] = ()

    @model_validator(mode="after")
    def check_ids(self):
        if len({settings.starting_plan_id for settings in self.inputs}) != len(self.inputs):
            raise ValueError("Optimization inputs must be unique per starting plan.")
        if len({run.id for run in self.runs}) != len(self.runs):
            raise ValueError("Optimization run IDs must be unique.")
        return self


class FarmPlan(Record):
    schema_version: Literal["2.0"]
    app_version: ShortText
    farm_name: ShortText
    planning_year: Annotated[int, Field(ge=1900, le=9999, strict=True)]
    notes: Notes = ""
    active_scenario_id: ShortText
    scenarios: Annotated[tuple[Scenario, ...], Field(min_length=1)]
    references: dict[str, Reference]
    optimization: OptimizationArchive | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_plan(cls, values):
        if not isinstance(values, dict) or values.get("schema_version") != "1.0":
            return values
        scenarios = values.get("scenarios")
        if not isinstance(scenarios, (list, tuple)):
            raise ValueError("The earlier farm plan is missing its scenarios.")
        return {**values, "schema_version": SCHEMA_VERSION,
                "scenarios": [_migrate_scenario(scenario) for scenario in scenarios]}

    @model_validator(mode="after")
    def check_scenarios(self):
        ids = {scenario.id for scenario in self.scenarios}
        names = {scenario.name.casefold() for scenario in self.scenarios}
        if len(ids) != len(self.scenarios) or len(names) != len(self.scenarios):
            raise ValueError("Scenario IDs and names must be unique.")
        numbers = [scenario.number for scenario in self.scenarios if scenario.number is not None]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Scenario numbers must be unique.")
        if self.active_scenario_id not in ids:
            raise ValueError("The active scenario ID must identify a saved scenario.")
        for scenario in self.scenarios:
            for field in scenario.fields:
                et_reference = field.et_estimate.reference_id if field.et_estimate else None
                for reference_id in (field.crop.reference_id, field.irrigation.reference_id, et_reference):
                    if reference_id and reference_id not in self.references:
                        raise ValueError(f"Missing saved reference {reference_id!r} for {field.id}.")
        return self

    @property
    def active_scenario(self) -> Scenario:
        return next(s for s in self.scenarios if s.id == self.active_scenario_id)


def load_plan(payload: str | bytes) -> FarmPlan:
    """Validate and load a versioned plan. Pydantic reports the invalid field path."""
    return FarmPlan.model_validate_json(payload)


def _descriptive_ids(records):
    """Prefer unique legacy display names, falling back to original IDs."""
    ids = [record.get("name") for record in records]
    if all(isinstance(value, str) and value.strip() for value in ids):
        if len({value.strip().casefold() for value in ids}) == len(ids):
            return [value.strip() for value in ids]
    return [record.get("id") for record in records]


def _migrate_scenario(scenario):
    if not isinstance(scenario, dict):
        raise ValueError("An earlier scenario must be a JSON object.")
    raw_sources, raw_fields = scenario.get("sources"), scenario.get("fields")
    for rows in (raw_sources, raw_fields):
        if not isinstance(rows, (list, tuple)) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("An earlier scenario must contain field and source records.")

    legacy_sources = [_LegacyWaterSource.model_validate(row) for row in raw_sources]
    legacy_fields = [_LegacyFieldPlan.model_validate(row) for row in raw_fields]
    if len({source.id.casefold() for source in legacy_sources}) != len(legacy_sources):
        raise ValueError("Each legacy water source ID must be unique, ignoring letter case.")
    if len({field.id.casefold() for field in legacy_fields}) != len(legacy_fields):
        raise ValueError("Each legacy field ID must be unique, ignoring letter case.")
    source_ids = dict(zip((source.id for source in legacy_sources), _descriptive_ids(raw_sources)))
    sources = [
        {
            "id": source_ids[source.id], "delivery_af": source.allocation_af * source.delivery_fraction,
            "ecw_ds_m": source.ecw_ds_m, "source_type": source.source_type, "notes": source.notes,
        }
        for source in legacy_sources
    ]
    fields = []
    for original, identifier in zip(legacy_fields, _descriptive_ids(raw_fields)):
        field = original.model_dump(exclude={"name"})
        field.update(id=identifier, source_id=source_ids.get(original.source_id))
        crop = field["crop"]
        if crop["id"] == "corn_forage":
            field["crop"] = {**crop, "id": "corn_silage", "label": "Corn, silage"}
        fields.append(field)
    return {**scenario, "fields": fields, "sources": sources}


def export_plan(plan: FarmPlan) -> bytes:
    """Serialize inputs and provenance, recording the application version of this export."""
    return (plan.model_copy(update={"app_version": VERSION}).model_dump_json(indent=2) + "\n").encode("utf-8")


def farm_plan_filename(timestamp: datetime | None = None) -> str:
    """Name an export with the version and a filename-safe local timestamp."""
    timestamp = timestamp if timestamp is not None else datetime.now().astimezone()
    return f"ag-salinity-farm-plan_v{VERSION}_{timestamp:%Y-%m-%d_%H%M%S%z}.json"


def report_filename(report: str, timestamp: datetime | None = None) -> str:
    timestamp = timestamp if timestamp is not None else datetime.now().astimezone()
    return f"ag-salinity-{report}_v{VERSION}_{timestamp:%Y-%m-%d_%H%M%S%z}.pdf"
