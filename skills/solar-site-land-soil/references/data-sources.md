# Anonymous sources and helper usage

## Sources

Public endpoints were checked/documented on 2026-10-02. Confirm service metadata when invoked; availability, coverage and permissions can change.

- NRCan Geolocator: `https://geolocator.api.geo.ca/?q=ADDRESS&lang=en&keys=locate`. Returns candidates with `name`, `province`, `lat`, `lng`, `category`, `tag`. The helper uses the NRCan `locate` source only and does not automatically select an address candidate. `INTERPOLATED_POSITION` is provisional, not a confirmed parcel. Source: https://prod-ressources-naturelles.azure.cloud.nrcan-rncan.gc.ca/carte-outils-publications/imagerie-satellitaire-donnees-elevation-photos-aeriennes/service-geolocalisation
- Google Maps and Street View: use public map views for parcel comparison and dated street-level inspection of access, poles and line hardware. Follow the Street View workflow in [access, grid and planning](grid-planning.md#street-view-and-line-phases). A direct panorama link can use `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=LAT,LON`; use a road position derived from the confirmed parcel, then verify the actual panorama location and capture date. Preserve attribution and distinguish approximate Google address labels from the confirmed property. No configured paid API or login is required by this skill. Observe licensing restrictions; do not scrape protected imagery.
- Soil capability layer: `https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer/29`. Query supports JSON and GeoJSON, WGS84 `inSR=4326`, spatial intersection, `CLI*`, `PERCENT*`, `CLI_SYS`, `SOIL_NAME*`. Fetch all pages; truncated results are incomplete.
- Soil map: the same service's `MapServer/export`, with `layers=show:29`. Export images are context views. Keep query bbox and layer metadata, and show a separate vector boundary/point overlay when possible. Do not falsely call an unmarked image a confirmed parcel screenshot.
- AgMaps guide: https://www.ontario.ca/page/how-use-agmaps
- AgMaps assessment parcel configuration: https://www.lioapplications.lrc.gov.on.ca/Geocortex/Essentials/essentials414/REST/sites/AgMaps/map/mapservices/30/layers/0 . Public visibility is not a guarantee of anonymous geometry/query authorization. Never supply a login token.
- Ontario Wetlands: https://open.canada.ca/data/en/dataset/d8805d53-40d6-4e13-bbc0-93677c0c9c7f . Current linked service: `https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer/15`. The helper checks intersection only, not an unspecified nearby buffer. Read metadata to establish coverage and currency.
- NRCan elevation profile: `https://geogratis.gc.ca/services/elevation/cdem/profile?path=LINESTRING(LON LAT,LON LAT)&steps=20`. JSON altitude values are metres; `null` means no data. Source: https://natural-resources.canada.ca/science-data/data-analysis/geospatial-data-tools-services/elevation-api . CDEM may represent ground or reflective surfaces; label it as coarse sampled evidence, not a high-resolution bare-earth assessment.
- Prefer suitable-resolution HRDEM **DTM** for full-area terrain evaluation: https://natural-resources.canada.ca/maps-tools-publications/satellite-elevation-air-photos/national-elevation-data-strategy . Discover/download public coverage from NRCan; use available GDAL/raster tools. Do not require installing GIS packages just to return a partial report. If absent, explicitly skip full-area slope and report any available samples separately.
- Transmission/pipelines/railways: inspect available official layers and base/topographic maps. OSM `power=line`, `power=minor_line`, `man_made=pipeline`, `railway=*` may supplement official evidence via an allowed Overpass service; missing OSM features do not establish absence. No default bulk scraping or public Nominatim calls.

## Public alternatives and full-process sources

Discovery checked October 9, 2026. Availability and operative document status must be checked again during each site run. Public access is not an open-source software license or unrestricted imagery license. GeoWarehouse is excluded by the user, including attempts to confirm its login.

- Public municipal/county parcel directories: search the municipality's official GIS/open-data website. For Grey County, https://gis.grey.ca/server/rest/services/Public/Service_ParcelLabels/MapServer/0 provides assessment geometry, ARN, address and recorded area. Layer 4 contains address points. Exact address/ARN matching and visual confirmation are needed. Do not assume these fields include a verified ownership PIN. Existing public source: https://gis.grey.ca/server/rest/services/Public . Other municipalities need their own services.
- Grey County geodesic calculation and projection: https://gis.grey.ca/server/rest/services/Utilities/Geometry/GeometryServer/areasAndLengths and /project. Read units and service metadata. Separate measured geodesic acreage from recorded acreage.
- Grey County dated imagery: https://gis.grey.ca/server/rest/services/Public/AirPhotos2015/ImageServer . Label 2015 explicitly; it cannot establish present road or pole conditions.
- Ontario public bare-earth terrain: https://ws.geoservices.lrc.gov.on.ca/arcgis5/rest/services/Elevation/Ontario_DTM_LidarDerived/ImageServer . Check parcel coverage, underlying tile acquisition date and elevation units/vertical CRS. Export unrendered elevation in an appropriate projected CRS. A service pixel size is not automatically the processing resolution. Catalog timeout does not make a successfully exported raster unusable, but survey date stays unknown.
- OEB Centralized Capacity Information Map (current discovery page): https://www.oeb.ca/ontarios-energy-sector/centralized-capacity-information-map . Use the official Launch link for the current map; identify distributor, candidate station/feeder and DER-layer units. Do not assume a stable undocumented API or use load capacity as generation capacity.
- Hydro One Generation Capacity Map: https://www.hydroone.com/business-services/generators/generation-capacity-map . Use inverter-based exporting layer for this scenario. Public map polygons can have multiple feeders; inspect all relevant candidates rather than only the initial popup.
- Hydro One Station Capacity Calculator: https://www.hydroone.com/businessservices_/generators_/Pages/stationcapacitycalculator.aspx . Public web UI is the preferred actual test, not an assumed API. Capture actual inputs/results. Station/feeder details might remain unavailable publicly; do not request a project number or contact utility staff automatically.
- Grey County Georgian Bluffs zoning example: https://gis.grey.ca/server/rest/services/Public/Service_GreyCountyZoning/MapServer/1 . Discover fields and current layer metadata; query complete parcel geometry and retain all zones/exceptions. Municipality-specific, not a province-wide zoning source.
- Official Georgian Bluffs by-law discovery: https://www.georgianbluffs.ca/build-and-invest/land-use-planning/zoning-by-law/ . Follow official links to current text and maps. Official notices: https://www.georgianbluffs.ca/build-and-invest/land-use-planning/public-notices/ . Notices reference a 2026 Official Plan; an older indexed 2014 PDF must not be assumed current without approval/appeal checking.
- County planning context: https://www.grey.ca/government/land-use-planning/land-use-planning-frequently-asked-questions . Follow current official links to county/local Official Plans. For other municipalities, use their official planning pages and public municipal-boundary datasets to establish jurisdiction.
- Provincial municipal jurisdiction: https://data.ontario.ca/en/dataset/municipal-boundaries and https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open03/MapServer/14 . Query lower/single-tier boundaries against the site geometry; verify current layer metadata. Source discovery: https://open.canada.ca/data/en/dataset/bab4e8d8-f0e6-498f-a336-4ac2f43d166d .
- Provincial planning context: https://www.ontario.ca/page/provincial-planning-statement-2024 and https://www.ontario.ca/page/prime-agricultural-areas . Verify the current applicable policy/version when needed. A local designation/exception does not itself resolve all provincial restrictions.

Full-process helper usage is documented in grid-planning.md. Existing land/soil helper usage follows below.

## Land and soil helper

`scripts/assess.py` uses Python 3 standard library only. Its functions can later be imported into a web backend. Resolve the script path relative to this skill directory. Use an available Python runtime; do not hard-code the developer's computer paths.

All helper-generated report headings, labels, status descriptions, messages, and invocation examples use English. Keep raw source evidence and supplied addresses unchanged.

```text
python scripts/assess.py --address "1037 Purple Valley Rd, Wiarton, ON" --out OUTPUT_DIR
python scripts/assess.py --address "..." --lon -81.10 --lat 44.87 --out OUTPUT_DIR
python scripts/assess.py --boundary parcel.geojson --boundary-status provided --out OUTPUT_DIR
python scripts/assess.py --rise-m 7 --run-m 127.04 --offline --out OUTPUT_DIR
python scripts/assess.py --profile-start -81.10 44.87 --profile-end -81.10 44.872 --out OUTPUT_DIR
```

These coordinates illustrate argument syntax and are not an authoritative boundary or assessed case. Do not treat examples as measurement evidence.

- `--address` alone returns candidates and skips point-dependent queries until a point is selected. Re-run with explicit `--lon` and `--lat` after evaluating a candidate. `--location-status estimated` is default; retain interpolation tags in the final report.
- GeoJSON must be WGS84 longitude/latitude, one Polygon or MultiPolygon (raw geometry, one Feature or a one-feature FeatureCollection). It is an input, not a claim of authoritative parcel geometry. Default boundary status is `provided`; use `verified` only after source-based confirmation.
- Area uses optional `pyproj.Geod` if installed; otherwise an explicitly labelled authalic-sphere approximation. No implicit package installation.
- A polygon query returns intersecting soil units and their composition. It does not compute clipped class area percentages. Add those only with an appropriate GIS calculation and keep composition uncertainty.
- Both `--profile-start` and `--profile-end` are required for public sampled terrain. Choose sample paths within the parcel when confirmed and preserve their endpoints. This is never a full-site slope map.
- `--rise-m` and `--run-m` support a documented contour measurement. Both are required; run must be positive, and units must be metres.
- `--offline` performs supplied geometry/contour calculations and explicitly skips public services. It is also useful for bounded validation.
- `--timeout` defaults to 15 seconds per request, with at most one retry only for timeouts. Each service fails independently; raw evidence is preserved when received. Sandboxed network failures require the host's normal permission handling; they are not authentication failures.
- Outputs: `assessment.json`, `report.md`, available `evidence/*.json`, and `soil-map.png` with metadata when export succeeds. Add manual observations to the report with sources; helper-only output is an initial partial assessment.
