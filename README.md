# Ag Salinity Manager

**Version 0.1.1** · Created by [AJ Brown, PhD](https://sites.google.com/view/ansleyjbrown)

Ag Salinity Manager helps producers, irrigation managers, Extension professionals, conservation planners, consultants, and researchers assess whether expected irrigation deliveries can support a proposed cropping plan and a maintenance salinity objective. It combines field area, crop water use, soil and irrigation water salinity, and field application efficiency. It reports conditional planning estimates and identifies where assigned water supplies or current soil salinity warrant further assessment.

## Features

- Add fields and irrigation sources through guided forms. Assign fields to each source and compare its expected farm delivery with its assigned demand.
- Select crop tolerance and irrigation efficiency presets or supply custom parameters. Seasonal ET starting estimates are editable and drawn from the Greeley, Colorado column of CSU Extension Table 1.
- Estimate relative crop production at current and target ECe, maintenance leaching, irrigation depth, field volumes, and annual farm balances.
- Compare independently editable scenarios using crop plans, estimated demands, water availability, and salinity concerns.
- Save and reload all scenarios as JSON, download a printable management PDF for the active scenario, or export its field results as CSV.
- Use the application locally after installation. Farm entries are held in the Streamlit session and are downloaded only on request.

## Install and run

Use Python **3.12**. The milestone was verified on Windows with Python 3.12.14. The commands below also specify the expected workflow for macOS and Linux.

Clone the repository from its GitHub **Code** menu using the actual clone URL. For an existing checkout, start at its root. The repository’s publication URL is pending owner confirmation.

```text
git clone <repository-clone-url>
cd <cloned-directory>
```

### Windows Anaconda Prompt

Run these commands from the repository directory containing `app.py`.

**Launch with the repository’s existing `.venv`**

If `.venv\Scripts\python.exe` is already present and the app dependencies are installed, run this single line. It also works from the `(base)` prompt.

```bat
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

**First-time setup with Conda**

If you need a new environment, run each line separately, pressing **Enter** after each one.

```bat
conda create --name saltplanner python=3.12 pip -y
conda activate saltplanner
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

**Launch again with Conda**

Use these commands after creating the `saltplanner` environment above.

```bat
conda activate saltplanner
python -m streamlit run app.py --server.address 127.0.0.1
```

Browse to [the local app](http://127.0.0.1:8501) and press **Ctrl+C** in Anaconda Prompt when you’re done. If `requirements.txt` or `constraints.txt` changes, rerun the install command with the Python executable for the environment you use to launch the app.

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

If using a standalone Python installation, replace `py -3.12` with the path to its Python 3.12 executable. If PowerShell blocks activation, run the install and launch commands with `.\.venv\Scripts\python.exe` in place of `python`.

**macOS and Linux**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

Open [Ag Salinity Manager on localhost](http://127.0.0.1:8501). Run Streamlit from the repository root to load the theme and local server settings. The commands above restrict the listener to loopback for local use. Streamlit Community Cloud manages the listener for hosted deployments. First-time dependency installation typically needs internet access. Calculations and reports run inside the app, and the project configuration disables Streamlit usage telemetry.

## Farm planning guide

On **Home**, select **Get started** to open **Farm Setup**. Upload an existing plan at the top of Farm Setup or follow the steps below to create one. The home page also links to AJ Brown’s contact page and the GitHub issue tracker.

1. **Farm Setup.** Enter the farm name and year. Add each field’s acreage, current soil salinity (ECe), crop, and irrigation method. Adjust default crop water use and enter effective precipitation as needed. Add each water source’s salinity (ECw) and expected delivery in acre-feet (AF), then assign the fields it irrigates. Select **Review and Calculate Farm Plan**. Saved field names appear in the sidebar as you work. Select a saved row to edit or delete it. Removing a water source clears its field assignments.
2. **Farm Dashboard.** Review the baseline water budget and any shortfall at an assigned source. The salinity section shows estimated yield retained and lost for each field at its current soil salinity. Open source and field tables when you need the underlying details.
3. **What-If Scenarios.** Select **Add new scenario** to copy the baseline. Change crops, seasonal crop ET, or expected effective precipitation, then save and compare the result. Each alternative has a persistent scenario number and a custom name. Select an alternative’s row to edit or delete it, or choose **Open in Farm Setup** for broader changes.
4. **Field Details.** Pick a field in the sidebar and select saved plans to compare their salinity-response curves and seasonal irrigation. Charts use scenario numbers, and the field table lists the crop, threshold, and leaching target with its basis for each plan. Plans match by field ID, ignoring case. Use **Edit this field in a scenario** to open the same scenario editor focused on that field.
5. **Optimization (experimental).** Pick a starting plan and eligible crops, then check the fields where adequate salinity leaching is required. Enter a sale unit, expected yield per acre without salinity stress, price in dollars per unit, and seasonal crop ET for replacements. The app estimates yield at current soil salinity and uses each candidate crop’s threshold as its leaching target. Compare gross revenue and planned irrigation, download a comparison PDF, or save a feasible result as a what-if scenario.
6. **Download Full Report.** Download the management report for a saved plan and append any completed optimization comparisons. The farm JSON also saves eligible crop lists, prices, yields, leaching selections, and run history, so you can upload it to resume work.

The dashboard’s **Can each source cover leaching?** section shows crop-only demand, extra irrigation needed for leaching, and the leaching gap after reserving water for estimated crop demand. A shortfall at a shared source calls for a field allocation decision. Field Details includes the required effective drainage below the root zone. These checks describe a seasonal maintenance budget. Forecasting seasonal soil salinity change requires a separate salt balance.

Optimized plans store their selected leaching fields in the optional scenario property `leaching_field_ids`. A missing property uses the full leaching budget used by existing farm plans. An empty list budgets crop irrigation only. The comparison chart uses each plan’s saved leaching selections.

Expand **Advanced field settings** in Farm Setup for crop coefficient and efficiency overrides, custom crops or methods, desired yield, a manual maintenance ECe target, and the effective leaching credit. New fields start with a 100% desired relative yield and zero leaching credit. Hover the question-mark icons for definitions and source links.

Download **Farm Plan (.json)** to resume planning with all scenarios in a new session. The filename includes the model version, local date and time, and UTC offset. The dashboard exports the baseline **Management Report (PDF)** and **Field Results (.csv)**. Loading a plan replaces the session’s current inputs.

## Demonstration farm

On **Home**, select **Load demonstration farm** to open the example results in **Farm Dashboard**. You can also upload [examples/example_farm.json](examples/example_farm.json) in **Farm Setup**. This hypothetical farm uses three fields and two independent water sources across 149 acres. Expected farm deliveries are 351 AF from Bench Canal and 70 AF from East Well.

| Scenario | Field demand (AF) | Field-deliverable supply (AF) | Combined field balance (AF) | East Well balance (AF) |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 374.2 | 421.0 | +46.8 | −23.8 |
| Barley on East Bench | 344.3 | 421.0 | +76.7 | +6.1 |

The baseline exceeds the well’s expected delivery despite a combined farm surplus. In the alternative, changing 36 acres from silage corn to grain barley lowers the entered net crop deficit from 23 to 18 inches on that field and increases the derived 90% target ECe from 3.15 to 10.0 dS/m. The lower crop deficit and theoretical LR reduce the well’s demand by 29.8 AF. Creek Flat’s measured ECe still exceeds its alfalfa maintenance target in both scenarios. These numbers reproduce the scenario comparison using illustrative inputs.

## Scientific methodology

[Scientific methods and limitations](docs/methods.md) provide the complete equations, units, assumptions, and interpretation used in **About & Methods** and the PDF. Source keys below match the registry. All calculations run independently of Streamlit.

| Calculation | Implementation and units | Source |
| --- | --- | --- |
| Crop response | `Y = max(0, 100 − b × max(0, ECe − a))`. `a` and `ECe` are in dS/m. `b` is percentage points per dS/m. `Y` is the percentage of potential for the crop’s documented production endpoint. For `0 < Y* ≤ 100`, target `ECe = a + (100 − Y*) / b`. | maas-hoffman, fao61-crops |
| Maintenance leaching | `LR = ECw / (5 × ECe_target − ECw)`, with both EC values in dS/m. LR is a fraction of effective infiltrated irrigation. Invalid or infeasible leaching estimates remain visibly unresolved. | fao29, fao61-balance |
| Crop water deficit | `N = max(0, ETc − effective rain)` in inches. Soil-water storage change and capillary rise are omitted. Edit the starting ETc for local conditions. | fao56, csu-seasonal-et |
| Gross irrigation | `G0 = N / e` and `G = max(G0, N / [(1 − LR) × (e + c × (1 − e))])` in inches. `e` is crop-only field application efficiency and `c` is the assumed effective leaching share of crop-only inefficiency. `G − G0` is extra gross maintenance water. | osu-efficiency for `e` presets; v0.1 mass balance informed by fao29 and fao61-balance |
| Field volume and farm balance | `Field AF = G × acres / 12`. Each source balance equals its expected farm delivery minus its assigned gross field demand. The combined farm balance sums expected deliveries and gross field demands. | Unit conversion and volume accounting |

CSU Extension Table 1 provides a 23.9-inch grain corn and 22.9-inch silage corn ET example for Greeley. The barley example uses the spring-grains row. The crop tolerance catalog evaluates separately sourced production endpoints. Silage corn uses shoot dry weight. Grain corn uses the FAO 61 Annex 1 footnote for DeKalb XL-75 on organic muck soil and warrants local review. [CSU Extension Table 1](https://extension.colostate.edu/resource/seasonal-water-needs-and-opportunities-for-limited-irrigation-for-colorado-crops/) · [FAO 61 Annex 1](https://www.fao.org/4/y4263e/y4263e0e.htm)

Effective leaching credit applies to water that mixes with root-zone soil water and drains below the root zone. Runoff, evaporation, and preferential bypass receive no credit. Additional water is assumed to experience the same nonbeneficial loss fraction as the baseline. The model reports sensitivity from zero to full credit with other inputs fixed. Review the site-specific basis for any nonzero credit and the feasibility of high LR before interpreting the budget.

### Published benchmarks

- **FAO 29, Example 3.** At ECw 1.2 dS/m and target ECe 2.5 or 1.7 dS/m, equation (9) gives 0.10619 or 0.16438. FAO displays approximately 0.10 and 0.16. The exact 2.5 dS/m result requires 895.0 mm of mixed water at 800 mm ET, compared with FAO’s 890 mm using its approximate LR. Crop-only applied depth is 1,230.8 mm at 65% efficiency. With full effective leaching credit, the example requires zero extra gross irrigation in the app, consistent with FAO’s conditional interpretation. At zero credit, v0.1 budgets additional water under its documented loss partition. The benchmark uses FAO’s stated maize ECe rather than the app’s forage corn preset. [FAO 29, section 2.4](https://www.fao.org/4/T0234e/T0234E03.htm)
- **FAO 29, Example 4.** The inverse cotton response reproduces the table at the printed precision for 100%, 90%, 75%, and 50% yield. The app excludes 0% as a desired yield input because bounding the response at zero leaves no unique maximum ECe. [FAO 29, section 2.4](https://www.fao.org/4/T0234e/T0234E03.htm)

### Scientific references

The [machine-readable reference registry](data/references.json) supplies the citation records used in the app and PDF and checked against this list.

- Maas, E. V., & Hoffman, G. J. (1977). Crop salt tolerance: Current assessment. Journal of the Irrigation and Drainage Division, 103(2), 115–134. [Publisher](https://doi.org/10.1061/JRCEA4.0001137)
- Tanji, K. K., & Kielen, N. C. (2002). Agricultural drainage water management in arid and semi-arid areas. FAO Irrigation and Drainage Paper 61, Annex 1, Table A1.1. [Crop tolerance data](https://www.fao.org/4/y4263e/y4263e0e.htm)
- Maas, E. V., & Grattan, S. R. (1999). Crop yields as affected by salinity. In R. W. Skaggs & J. van Schilfgaarde (Eds.), Agricultural drainage, Agronomy Monograph 38, pp. 55–108. [Original compilation](https://doi.org/10.2134/agronmonogr38.c3)
- Ayers, R. S., & Westcot, D. W. (1985). Water quality for agriculture. FAO Irrigation and Drainage Paper 29 Rev. 1, section 2.4. [Water quality and leaching](https://www.fao.org/4/T0234e/T0234E03.htm)
- Tanji, K. K., & Kielen, N. C. (2002). Agricultural drainage water management in arid and semi-arid areas. FAO Irrigation and Drainage Paper 61, Annex 4. [Water and salt balance](https://www.fao.org/4/Y4263E/y4263e0h.htm)
- Zamora Re, M. I., Peplin, T. M., & Tomasek, A. (2026). Irrigation water scheduling. Oregon State University Extension, EM 9717, Management Technical Guide 8. [Irrigation efficiency ranges](https://extension.oregonstate.edu/catalog/em-9717-irrigation-water-scheduling)
- Schneekloth, J., & Andales, A. (2017). Seasonal water needs and opportunities for limited irrigation for Colorado crops. Colorado State University Extension, Table 1, Greeley column. [Seasonal ET starting estimates](https://extension.colostate.edu/resource/seasonal-water-needs-and-opportunities-for-limited-irrigation-for-colorado-crops/)
- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop evapotranspiration: Guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56. [Crop evapotranspiration](https://www.fao.org/4/x0490e/x0490e00.htm)

## Configuration specification

The JSON contract is defined in [schemas/farm.py](schemas/farm.py). Version `2.0` contains farm metadata, an active scenario ID, complete independent scenarios, and a reference registry snapshot. Each scenario contains `fields` and `sources`. Saved alternatives can also carry a `number`. Older plans without numbers receive them in saved order when opened. Each field stores area, salinity, source ID, crop and irrigation objects, desired yield, resolved target ECe and its override flag, ET, effective rain, leaching credit, and notes. When a starting ET estimate was used, `et_estimate` preserves its value, location, crop row, and reference. Each source records `delivery_af`, ECw, type, and notes. Fields and sources each use one identifier. Fields refer to sources by exact ID.

Version `1.0` exports load automatically. The importer uses unique legacy names as identifiers where possible and maps the field assignments to the corresponding source IDs. It converts old allocations to their field-delivered volumes using the saved delivery assumptions once. Saved ET values and crop coefficients carry forward.

The `crop` object preserves both coefficients, the production endpoint, separate origin markers, and a reference ID for presets. The `irrigation` object preserves the resolved efficiency, its origin, the published range if applicable, and its reference ID. A derived `target_ece_ds_m` agrees with the saved crop model and desired yield. User overrides and custom parameters are stored explicitly. Reports are recalculated from the stored inputs upon restore.

This excerpt illustrates the structure. The linked example is a complete importable file.

```json
{
  "schema_version": "2.0",
  "app_version": "0.1.1",
  "farm_name": "Demo Farm",
  "planning_year": 2026,
  "notes": "",
  "active_scenario_id": "baseline",
  "scenarios": [
    {"id": "baseline", "name": "Baseline", "fields": [], "sources": []}
  ],
  "references": {}
}
```

Under **Upload an existing farm plan** at the top of **Farm Setup**, select **Upload** to open a saved JSON file. Invalid files retain the current session and display validation messages. Download the JSON before closing the session. Keep files containing actual farm data out of version control.

## Repository structure

| Path | Purpose |
| --- | --- |
| `app.py`, `pages/`, `ui/` | Streamlit navigation, editing, session state, and presentation |
| `models/` | Crop response, maintenance leaching, irrigation demand, and farm budgeting |
| `schemas/` | Validated configuration and independent scenario records |
| `data/`, `docs/` | Published presets, scientific references, methods, and dependency review |
| `reports/` | In-memory ReportLab management PDF |
| `examples/`, `tests/` | Demonstration plan and automated checks |
| `config/`, `.streamlit/`, `assets/` | Branding configuration, local app settings, and optional logo |
| `static/banners/` | Locally served page banners with [image credits and prompts](docs/banner-images.md) |

## Development and testing

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

- To add a crop or irrigation preset, add a row to the appropriate [data table](data/) with source units and, for crops, the exact production endpoint. Include the reference in the registry and test the published value. Keep crop tolerance separate from ET.
- To add a reference, use a stable ID and verify authors, year, publication, DOI if available, and landing page. Regenerate the README bibliography from `data.catalog.REFERENCES` using `reference.citation` and `reference.url`. The tests check for citation drift.
- For scientific changes, update the methods and add an authoritative reference, a worked benchmark or derivation, and tests for the expected behavior, edge cases, and units.
- To validate a JSON file programmatically, call `schemas.farm.load_plan(Path(path).read_bytes())`. The test suite covers schema validation, provenance, and round trips.
- Run `python -m pytest tests/test_reports.py` to check PDFs. After layout changes, render the demonstration and a multipage farm with Poppler and review page breaks, headers, and references.

### Optional branding

Place an authorized PNG or JPEG at `assets/logo.png` or set `AG_SALINITY_LOGO` to a local absolute or repository-relative path. The app and PDF use the configured image when present. Set `AG_SALINITY_REPOSITORY_URL` to override the default GitHub repository for the app’s repository and issue links.

## Known limitations

- The leaching estimate assumes an approximate steady state and adequate drainage. Existing salinity above target requires a separate reclamation assessment. Field-specific wetting patterns, bypass flow, and soil hydraulic limitations affect the applicability of the model.
- A field-average ECe can mask spatial variability and sensitive growth stages. Crop coefficients are empirical estimates for specific endpoints. The model does not simulate yield loss caused by shortage of irrigation water.
- Sodium-related soil structural or infiltration risks require separate water and soil evaluation. EC alone describes salinity.
- Seasonal ET and effective precipitation are local inputs. Rain-driven leaching, capillary rise, and dynamic soil water and salinity are outside the budget.
- Annual source allocations omit delivery timing, peak capacity, outages, and interannual risk. v0.1 assigns one source to each field. Supply blending and field-specific allocation constraints are future work.

## Roadmap

1. Add a separate soil reclamation planner with soil depth, initial salinity, and method-specific estimates.
2. Add weather-based ET and crop-coefficient workflows following FAO 56.
3. Add spatial data and calibrate apparent conductivity to measured ECe where supported.
4. Extend water and salt balances to include water blending, seasonal changes, and shallow water tables.
5. Evaluate economics and crop or water allocation optimization.
6. Quantify uncertainty in crop tolerance, climate inputs, and spatial salinity.

## Copyright and license

Copyright (C) 2026 AgriData Solutions, LLC, **proposed holder pending owner confirmation**. Original software is offered under `GPL-2.0-or-later` and provided without warranty. The [LICENSE](LICENSE) file contains the unmodified GNU GPL version 2 text. For Apache-2.0 dependencies, the FSF identifies GPL version 3 as the compatible GPL version for covered combinations. See the [dependency license review](docs/dependency-licenses.md) for packaging questions and notices to preserve.

The software license covers the original code. AgriData Solutions marks and logos are subject to separate rights. Scientific coefficients and relationships are attributed to their sources. The project does not redistribute source publications or claim ownership of their data.

## Contributing

Report issues and propose improvements in the repository’s issue tracker once configured. See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducibility, test, scientific citation, and pull request expectations.

## Software citation

Brown, A. J. (2026). *Ag Salinity Manager* (Version 0.1.1) [Computer software].

See [CITATION.cff](CITATION.cff). Confirm the organization citation and add the repository URL before publication. A DOI has not been assigned.
