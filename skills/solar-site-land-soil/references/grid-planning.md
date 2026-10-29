# Access, grid and planning

## Required final-report fields

Address; ARN; PIN; acreage; soil classes; soil map; slope; existing access road (Y/N/Unknown); line phases; interconnection distance; 2,000 kW calculator screening result (Y/N/Unknown); highest tested passing capacity; zoning; solar/renewable generation permitted use; Official Plan designation. Retain municipality, distributor, station/feeder, dates, route geometry, exceptions and unresolved verification. Unknown is not No or zero. Calculator Pass/Fail belongs to a specific scenario, never the overall property decision.

## Access and route

Use dated public imagery, roads, terrain, parcels and barriers to identify an existing entrance and plausible truck route. A visible path does not establish truck access, easements, ownership or entrance permits. Flag waterways, railway crossings, steep sections, third-party parcels and missing connections. Record visible road attributes only when supported.

### Street View and line phases

For the access/interconnection section, inspect publicly accessible Google Maps Street View along the confirmed parcel frontage and candidate route before leaving imagery-based phase screening uncollected. If authoritative phase records already resolve the question, Street View remains useful for visible access and hardware context. Skip unavailable or login-dependent views with the specific reason; do not require paid APIs or credentials.

- Locate the road using the confirmed parcel geometry. Retain the panorama URL/ID and WGS84 camera position, road side and relationship to the parcel. Google road-address or municipality labels can be approximate; they do not override authoritative parcel/address or jurisdiction evidence.
- Check the displayed capture month/year separately from retrieval time. Rotate to view both road sides and look along the line; move to a nearby viewpoint or zoom when needed to resolve a pole's upper crossarm, insulators and conductor positions. Check visible entrances, roadside ditches and crossing barriers without inferring legal or truck access.
- Base a phase interpretation on distinguishable insulated phase positions and their continuity along the circuit, not the number of wires alone. Neutral, communications, lower circuits and shared pole attachments can mislead. Describe the visible hardware and leave unidentified attachments unassigned. Neither voltage nor an undifferentiated three-wire count proves three phases.
- Save a contextual screenshot with Google attribution and capture date visible where practicable; retain the exact view URL and explain any obscured detail. In `line_phases`, record `estimated_phase_count` (null if inconclusive), `utility_verified_phase_count` (null unless independently confirmed), confidence, observations and limitations. A supported visual three-phase interpretation is `estimated`, not `verified`; ambiguous imagery remains explicitly inconclusive.
- Keep nearby three-phase evidence separate from the actual serving feeder, point of connection, route distance and 2 MW exporting capacity. A circuit across the road may require a crossing or upgrade. Do not assign the circuit to a named feeder from proximity or voltage alone. Less than three phases prompts upgrade review, not automatic rejection.

A black panorama or loading screen is not evidence of absent coverage. Allow the page to finish loading and inspect its state; if still stalled, reload once, then stop if unusable. Distinguish loading/rendering failure, explicit lack of imagery, authentication and host/network denial. If a later view succeeds, supersede the earlier failure and update the report, assessment and evidence consistently. Street View is an inspection of dated conditions, not utility confirmation or permission to connect.

Trace ordered WGS84 LineString vertices from the site point to the entrance and along roads to a candidate electrical connection. Identify endpoints and whether the site-to-access segment is included. Record whether the connection point is utility-confirmed. Use geodesic segment length, map precision limits and an estimated status. A nearest station is not automatically a connection point. A public map trace can replace a key-dependent routing API.

## Capacity

### Hydro One map terms: standing user authorization

For Hydro One's Generation Capacity Map, accept the standard map-viewing terms/disclaimer when required to open or reopen the public map, without asking the user again. This is explicit standing authorization from the user, including subsequent skill runs. Read and comply with the displayed terms; acceptance does not make screening results approved or reserve capacity. This covers the map-access Agree/Accept step only, not account creation, purchases, connection applications, Offers to Connect, or other contracts. If the control is blocked or requires login, preserve the specific access failure and continue independent work; do not bypass the restriction.

Identify the actual distributor first. OEB CCIM and utility maps provide context, not approved connections or reserved capacity. Hydro One's calculator applies to its own distribution system. Feeder coverage alone does not prove the nearby line serves that feeder: retain multiple candidates and cross-check names/locations. Do not add together station, feeder or short-circuit limits, or replace the required calculator result with a map's MW label.

For Hydro One, select the actual station/feeder, 2,000 kW, exporting and inverter-based solar. Preserve inputs/results as screenshots or public responses, timestamp and failure reasons. A pass is preliminary and does not reserve capacity. If the tool cannot render, requires login, or the feeder is unconfirmed, skip the affected test and retain map evidence separately. Do not invent a private API or claim that reading the webpage executes its calculator.

After an actual 2,000 kW pass, increase size in declared increments within the tool's allowed range, with at most 12 additional trials. Stop at the first failure or chosen ceiling; refine the bracket within the same total trial budget if useful, to a stated resolution (default 100 kW). Do not cross into micro-generation sizes when searching a 2 MW project: criteria can differ and outcomes need not be globally monotonic. A smaller failure followed by a larger pass is a conflict: stop assuming monotonicity and retain the evidence. Observe service rate limits and never bypass restrictions.

Report highest tested pass, next tested fail, bracket width, tested ceiling and all trials. With no upper failure, the highest pass is a lower bound within the tested range. Exact maximum remains unknown; no capacity is reserved. Separate source data date from retrieval time.

## Zoning and Official Plan

Identify jurisdiction using official municipal boundaries. Discover the municipality's public zoning GIS or PDF schedules and operative by-law. Query the whole parcel and retain split zones, overlays, holding symbols and exception codes. Point-only zoning is provisional. Match codes to definitions, permitted uses, renewable energy/general provisions, special exceptions and amendments. Search solar, photovoltaic, ground-mounted, renewable energy generation, energy facility and accessory use. Rooftop/accessory permission is not automatically permission for a 2 MW ground-mounted facility.

Review applicable county/local Official Plans: land-use designations, agricultural/natural heritage overlays, energy policies and OPA. Record document/by-law number, consolidation date, schedule, section/page, amendment and approval/effective status. Check official notices for new plans, approvals and appeals. A proposed/adopted plan under approval or appeal is not automatically operative. Map/text conflicts need review. The process's Zone 1/Z.1 wording is a case example, not an Ontario-wide rule.

Outcomes: permitted with cited conditions; prohibited with cited provision; potentially permitted subject to a specified approval/exception; or unknown. Use needs_review for ambiguity, unconfirmed amendments and conflicting zones. AI can retrieve and compare provisions but cannot manufacture permission. CLI alone is not a legal planning designation. When interpreting agricultural restrictions, check current official Ontario policy separately from the user's preliminary CLI rule.

## Helper and observation schema

```text
python scripts/assess_full.py --base LAND_SOIL_DIR/assessment.json --observations observations.json --out FULL_REPORT_DIR
python scripts/assess_full.py --base LAND_SOIL_DIR/assessment.json --zoning-layer PUBLIC_ARCGIS_LAYER_URL --out FULL_REPORT_DIR
```

Without observations the helper creates an explicit missing-data checklist, not an assessment of those missing indicators. The optional zoning query saves raw intersecting polygons; legal interpretation remains separate. Discover the correct layer for each municipality rather than applying Grey County services across Ontario.

The observation file accepts three top-level keys: observations, route and capacity_tests. Observation keys: municipality, access_road, line_phases, interconnection_distance, distributor, station, feeder, hosting_capacity, capacity_2000_kw, maximum_tested_capacity, zoning, solar_permitted_use, official_plan, planning_exceptions.

Collected metrics require status (verified/provided/estimated/needs_review), non-null value, source, retrieved_at and evidence_locator (screenshot or document section/page). Optional data_date and scope preserve uncertainty. Skipped metrics require status=skipped, value=null and an individual reason. User assertions stay provided until checked. Example shape only; never submit placeholders as evidence:

```json
{"observations":{"access_road":{"status":"estimated","value":{"existing_access_road":null,"truck_access_feasible":null,"legal_access_confirmed":false},"source":"SOURCE_URL_OR_FILE","retrieved_at":"ISO_TIMESTAMP","evidence_locator":"SCREENSHOT_OR_DOCUMENT_SECTION","data_date":null}}}
```

route uses that metric shape with value containing a WGS84 LineString. Geometry validation does not prove road following; the helper leaves endpoint/legal checks unresolved. Record known endpoint facts separately.

Each actual calculator test requires distributor, station, feeder, project_type=exporting, technology=inverter_based_solar, positive project_kw, result=pass/fail, source, retrieved_at and evidence_locator. Do not combine different station/feeders. Only an exact 2,000 kW trial populates the target result. Exact maximum is always null and capacity_reserved is false. Preserve raw trials and any non-monotonic conflict.

Run scripts/self_test_full.py and the original scripts/self_test.py after changes. The helpers use the standard library and can be imported by a future web backend, but source discovery, public UI operation and planning interpretation still require the agent/tools.
