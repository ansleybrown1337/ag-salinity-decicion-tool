## Crop salinity response

Maas and Hoffman (1977) estimate relative production (%) as Y = max(0, 100 − b × max(0, ECe − a)). ECe is representative root-zone saturated paste extract conductivity (dS/m), a is the crop threshold (dS/m), and b is the yield-loss slope (percentage points per dS/m). The response is bounded to 0–100%. For a desired yield Y* in (0, 100], the greatest modeled ECe meeting it is a + (100 − Y*) / b. A user may instead enter a manual target. The software reports its implied yield and flags a conflict with the desired yield.

FAO 61, Annex 1 reproduces the Maas and Grattan (1999) compilation used for crop defaults. Corn silage uses the shoot dry weight response and sweet corn uses ear fresh weight. The grain corn screening preset uses the Annex 1 footnote for DeKalb XL-75 on organic muck soil. Review this cultivar- and site-specific response before applying it locally. These responses depend on cultivar, growth stage, soil, environment, and sampling. The model conditions on a supplied ECe and estimates the effect of salinity alone. It does not model yield loss from water deficits or predict future soil ECe.

## Maintenance leaching

FAO 29 Rev. 1, section 2.4, gives LR = ECw / (5 × ECe_target − ECw), where ECw is irrigation water conductivity and ECe_target is target average root-zone saturated paste extract conductivity (both dS/m). LR is the required fraction of effective infiltrated irrigation that drains below the root zone under the model. Freshwater with zero ECw gives LR = 0 for a positive target. A nonpositive target or denominator, or LR ≥ 1, makes the maintenance estimate infeasible. This withholds the total demand for the affected field and any enclosing total.

The relationship was developed for ordinary surface irrigation and is used here for screening sprinkler systems under similar mixing and drainage assumptions. Applicability to localized drip wetting or preferential flow is limited. FAO 29 identifies LR above approximately 25–30% as potentially impractical. The app flags values above 25% for review and leaves the numerical estimate visible. If current ECe exceeds the target, a separate reclamation assessment is needed. A calculated LR establishes neither actual field drainage nor a time to achieve the target.

## Seasonal crop deficit

Net crop deficit N = max(0, ETc − effective precipitation), in inches. ETc is seasonal crop evapotranspiration. When adding a preset crop, the app suggests a seasonal value from the Greeley, Colorado column of Colorado State University Extension Table 1 (Schneekloth & Andales, 2017). The spring-grains row is a starting estimate for barley. Use a locally appropriate value for the crop and season. Effective precipitation is the portion available to meet crop ET. The budget assumes zero change in seasonal soil-water storage and omits capillary rise, deliberate off-season leaching, and rainfall-driven drainage. FAO 56 defines ETc and provides methods for developing local estimates.

## Field application and leaching credit

Let e be the field application efficiency (fraction of crop-only applied water stored to meet crop demand) and c the fraction of crop-only inefficiency credited as effective leaching. The crop-only gross depth is G0 = N / e. Credited effective drainage in that application is D0 = c × (G0 − N). Runoff, evaporation, and bypass flow are excluded from credit. OSU Extension supplies application-efficiency ranges. Preset midpoints provide planning values, independent of c.

The assumed share of gross application that mixes with the root zone is m = e + c × (1 − e). Minimum mixed water to meet the crop deficit and LR is I = N / (1 − LR). Gross field application is G = max(G0, I / m). Extra gross water for maintenance is G − G0. Required effective drainage at the minimum mixing depth is I × LR. The modeled effective drainage for the full application is D0 + m × (G − G0). The remaining field losses are (G0 − N − D0) + (1 − m) × (G − G0). These components satisfy the seasonal field water balance.

This accounting uses the FAO 29 principle that existing leaching may meet part or all of the maintenance requirement and the FAO 61 distinction between mixing and bypass water. Scaling nonbeneficial losses to additional gross water at the same rate is a v0.1 planning assumption. The default c = 0 credits no effective drainage from crop-only inefficiency. At c = 1 the framework credits all of it, which serves as a sensitivity endpoint. The reported interval spans these assumptions with other inputs fixed. It is not a statistical interval or a field-validated bound. A zero crop deficit gives zero irrigation in this seasonal budget and does not evaluate whether rainfall controls salinity.

## Water supply and farm budget

Field demand in acre-feet (AF) equals G (in) × area (ac) / 12. Each field is assigned one source. Expected farm delivery is the usable irrigation supply expected from that source during the planning year, after upstream losses. The budget assumes the delivered volume is available for field application.

Compare the summed gross field demand assigned to each source with its expected farm delivery. The combined farm balance is total expected delivery minus total gross field demand. A positive combined balance may coexist with an individual source shortfall. Surplus at one source cannot offset another under fixed assignments. A source with an infeasible field shows known demand and an undetermined total.

The source leaching gap is the additional gross maintenance demand minus delivery remaining after crop-only demand, bounded below by zero. A crop-only deficit is reported separately. When combined demand exceeds a shared source’s delivery, coverage for individual fields depends on the irrigator’s allocation. The model leaves coverage undetermined for saline irrigation sources when crop deficit is zero because rainfall-driven drainage is outside the budget.

## Interpretation and limitations

Use the estimates to compare plans with site-specific field and water information. Drainage capacity, water table, hydraulic conductivity, soil heterogeneity, water delivery timing, and irrigation uniformity require separate evaluation. Salinity measures dissolved salts, while sodicity and associated infiltration risks require additional sodium and soil information. Seasonal volume sufficiency does not establish delivery capacity or agronomic performance.

Ag Salinity Manager provides planning estimates. Use field measurements and site-specific professional judgment to interpret them. Software is provided without warranty under the terms of the GPL.
