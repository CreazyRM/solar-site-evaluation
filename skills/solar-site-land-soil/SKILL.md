---
name: solar-site-land-soil
description: "Evaluate Ontario ground-mount solar sites across land and size, soil and slope, access and grid distance, 2 MW connection capacity, and zoning and Official Plan. Use public alternatives to GeoWarehouse and produce sourced partial results when indicators are unavailable."
---

# Ontario Solar Site Evaluation

Keep the existing invocation name for compatibility. Default to all five process sections; honor explicit requests for selected sections or the original land/soil-only mode. Use English for instructions, report text, maps, UI and code comments. Preserve source identifiers and raw evidence verbatim.

Read [process rules](references/process.md). For the last three sections, read [access, grid and planning](references/grid-planning.md). Read [public sources and helper usage](references/data-sources.md) when collecting evidence.

## Source policy

The user has given standing authorization to accept Hydro One Generation Capacity Map's standard map-viewing terms/disclaimer (for example, an Agree or Accept control) whenever needed for this skill. Do not ask for confirmation again for that map-access step. This authorization covers public map viewing only, not connection applications, paid services, account creation or other agreements. Continue to observe the displayed terms and retain the preliminary, non-reserving nature of map results.

**GeoWarehouse access is confirmed unavailable. Exclude it rather than retrying its login or asking for credentials.** Prefer municipal/county assessment parcels and address points, provincial public layers, official utility/OEB tools and municipal planning documents. Do not guess a PIN from an ARN or relabel a historical PID as a verified PIN. Assessment parcels are not necessarily ownership parcels. Skip only unavailable title indicators and continue the other work.

Skip other login-dependent indicators without passwords, saved credentials, cookies or private tokens. A public REST directory's Login link alone does not prohibit anonymous queries. Distinguish authentication, missing data, timeout and host permission failures. Allow one retry for timeouts, then stop. Do not contact utilities or municipalities without explicit user instructions.

## Execution

1. **Land Location and Size:** Preserve and normalize the address. Assess candidate precision; do not automatically accept a coarse centroid. Discover the correct municipality's public parcel service, confirm by address/ARN and visual comparison, record identifiers separately and measure geodesic/equal-area acreage. Distinguish recorded, historical, measured and net developable acreage.
2. **Soil and Slope:** Retain all CLI classes and mixed-unit proportions. Produce boundary-marked soil and no-soil base views, with about 50% soil opacity. Inspect wetlands, lines, pipelines and railroads with coverage limits. Prefer parcel-clipped bare-earth DTM slope and record CRS, units, resolution, NoData and coverage; profiles remain samples. User screening defaults: CLI 4-7; CLI 1-3 require a supported planning exception; slope strictly above 15% is adverse for the measured area. Rural zoning alone does not establish an exception.
3. **Interconnection Distance:** Inspect existing and potential truck access, distinguish visible roads from legal access, evaluate line phases with dated imagery/official data, and trace site-to-access-to-candidate-connection vertices along roads. Do not replace the route with nearest-station straight-line distance or derive phases from voltage alone.
4. **Interconnection Electrical Capacity:** Identify the actual distributor and candidate station/feeder with public OEB/utility tools. Retain multiple candidates, units, dates and unresolved service relationships. For Hydro One, collect an actual 2,000 kW calculator result with exporting inverter-based solar. Map capacity is separate screening evidence. Use the grid reference's bounded higher-size trials and report the highest tested pass, not an invented exact maximum.
5. **Zoning and Official Plan:** Confirm municipal jurisdiction. Retain all parcel-intersecting zoning codes, overlays and exceptions. Review current by-law definitions, permitted uses and amendments, plus operative municipal/county Official Plan designations and schedules. Cite sections/pages and effective/approval status. Source examples such as Z.1 are case-specific; proposed/adopted plans under approval or appeal do not automatically replace operative plans.

## Outputs and automation

Prefer [standard task generation and metric drafts](references/standard-automation.md) for supported calculations: supply one confirmed profile to `scripts/standard_plan.py`, then read its exception list. Do not manually rebuild standard soil/wetland/zoning/area/terrain tasks or transcribe their numeric results. For this project's multi-agent runs, use `scripts/solar_agents.py review-diff` to focus independent review on changed evidence and related conclusions; it never replaces the required full-snapshot review or assembly gate. Respect assigned output ownership and preserve source dates.

For routine collection, GIS calculations and artifact generation, read [the reusable pipeline](references/reusable-pipeline.md) and dispatch a configured job through `scripts/pipeline.py`. Reuse the registered operations instead of generating per-site code. Independent tasks run in bounded parallel batches; failures are isolated and local computations can resume. Read compact summaries first. Use `scripts/replay_case.py` for an explicitly offline replay of saved case evidence. Previously used sources and coverage are in `references/source-registry.json`; discover additional municipalities as needed. Preserve Street View and planning judgement in the agent, with evidence supplied to these modules.

Generate English assessment.json, readable report.md, maps and raw evidence in a new site-specific directory. Include every requested process indicator, status, value, source, retrieval time, data date if available, spatial scope and individual skip reason. Separate factual observations from AI interpretations and cite the provisions supporting planning conclusions. End with supported findings, conflicts and missing verification. Do not assign development approval or an overall Pass/Fail from incomplete public screening.

scripts/assess.py remains the backward-compatible land/soil collector. scripts/assess_full.py extends its JSON with provenance-checked observations, traced-route length, actual calculator trials and an optional anonymous zoning-layer query. The helpers do not automatically inspect imagery, operate capacity-map UI or interpret by-laws: complete those tasks with available browsing/GIS tools. Their standard-library functions can be reused in a future web backend. Use an available Python runtime without hard-coded computer paths. For requested PDF output, use the available PDF workflow and check page/map rendering.

For an available terrain export and projected parcel, dispatch the reusable [offline slope worker](references/terrain-worker.md) instead of writing site-specific processing code. It requires NumPy/Pillow; the original helpers remain standard-library-only. The worker returns a compact summary, saves full evidence and maps, and can be imported by a future web backend. Inspect detailed arrays only when the summary reports an exception or coverage issue.

Example full invocation:

```text
Use $solar-site-land-soil to complete all five sections of the Ontario Solar Site Evaluation process for [site address]. Exclude GeoWarehouse, use public alternatives, skip login-dependent indicators, and generate the report in English.
```

Example limited invocation:

```text
Use $solar-site-land-soil to assess only Land Location and Size and Soil and Slope for [site address], using public alternatives and reporting in English.
```
