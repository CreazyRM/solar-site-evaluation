#!/usr/bin/env python3
"""Partial Ontario land/soil assessment; standard library, reusable backend functions."""
import argparse
import json
import math
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

GEOCODER = "https://geolocator.api.geo.ca/"
SOIL = "https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer/29"
WETLAND = "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer/15"
PROFILE = "https://geogratis.gc.ca/services/elevation/cdem/profile"
ACRE_M2 = 4046.8564224
AUTHALIC_RADIUS_M = 6371007.1809
SOIL_FIELDS = "OBJECTID,CLI_SYS,CLI1,CLI2,CLI3,PERCENT1,PERCENT2,PERCENT3,SOIL_NAME1,SOIL_NAME2,SOIL_NAME3"


class Unavailable(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def metric(status, value=None, source=None, reason=None, **details):
    result = {"status": status, "value": value, "source": source, **details}
    if reason:
        result["reason"] = reason
    return result


def request_json(url, params, timeout=15):
    """Anonymous GET only, bounded timeout retry, explicit authentication skip."""
    host = (urlparse(url).hostname or "").lower()
    if host == "geowarehouse.ca" or host.endswith(".geowarehouse.ca"):
        raise Unavailable("source_excluded_by_user_geowarehouse")
    request = Request(url + "?" + urlencode(params), headers={
        "User-Agent": "OntarioSolarLandSoilSkill/1.0 (research)", "Accept": "application/json"})
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                if any(part in urlparse(response.url).path.lower() for part in ("/login", "/signin")):
                    raise Unavailable("authentication_required")
                raw = response.read(20_000_001)
                if len(raw) > 20_000_000:
                    raise Unavailable("response_too_large")
                try:
                    data = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise Unavailable("non_json_response")
                if isinstance(data, dict) and data.get("error"):
                    code = data["error"].get("code") if isinstance(data["error"], dict) else None
                    raise Unavailable("authentication_required" if code in (401, 498, 499)
                                      else "access_denied" if code == 403 else "service_error")
                return data
        except HTTPError as exc:
            raise Unavailable("authentication_required" if exc.code == 401 else
                              "access_denied" if exc.code == 403 else f"http_{exc.code}") from exc
        except (TimeoutError, socket.timeout):
            if attempt:
                raise Unavailable("timeout")
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                if not attempt:
                    continue
                raise Unavailable("timeout") from exc
            if isinstance(exc.reason, PermissionError):
                raise Unavailable("host_network_permission_denied") from exc
            raise Unavailable("network_unavailable") from exc
    raise Unavailable("timeout")


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_geometry(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("crs"):
        name = data["crs"].get("properties", {}).get("name", "").upper()
        if name not in ("EPSG:4326", "URN:OGC:DEF:CRS:OGC:1.3:CRS84", "URN:OGC:DEF:CRS:EPSG::4326"):
            raise ValueError("Boundary must use WGS84 longitude/latitude; reproject it first.")
    if data.get("type") == "FeatureCollection":
        if len(data.get("features", [])) != 1:
            raise ValueError("Supply exactly one parcel Feature; MultiPolygon is supported.")
        data = data["features"][0]
    if data.get("type") == "Feature":
        data = data.get("geometry") or {}
    if data.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("Boundary must be a Polygon or MultiPolygon.")
    if not data.get("coordinates"):
        raise ValueError("Boundary has no coordinates.")
    for polygon in polygons(data):
        if not polygon:
            raise ValueError("Empty polygon.")
        for ring in polygon:
            if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                raise ValueError("Every ring needs at least four points and must be closed.")
            for p in ring:
                if len(p) < 2 or not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                        and math.isfinite(x) for x in p[:2]):
                    raise ValueError("Invalid coordinate.")
                if not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90):
                    raise ValueError("Expected longitude/latitude, not projected coordinates.")
            if abs(signed_planar_area(ring)) < 1e-15:
                raise ValueError("Degenerate ring; check geometry for self-intersection.")
    return {"type": data["type"], "coordinates": data["coordinates"]}


def polygons(geometry):
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]


def signed_planar_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:])) / 2


def area_m2(geometry):
    """Geodesic if optional pyproj exists; otherwise explicitly approximate."""
    try:
        from pyproj import Geod
        geod = Geod(ellps="WGS84")
        def ring_area(ring):
            return abs(geod.polygon_area_perimeter([p[0] for p in ring], [p[1] for p in ring])[0])
        method = "WGS84 ellipsoidal geodesic (pyproj.Geod)"
        approximate = False
    except ImportError:
        def ring_area(ring):
            # Authalic spherical trapezoids; adequate only as a labelled screening estimate.
            value = sum(math.radians(b[0] - a[0]) * (math.sin(math.radians(a[1])) +
                        math.sin(math.radians(b[1]))) for a, b in zip(ring, ring[1:]))
            return abs(value) * AUTHALIC_RADIUS_M ** 2 / 2
        method = "WGS84 authalic-sphere approximation; not surveyed acreage"
        approximate = True
    total = 0.0
    for polygon in polygons(geometry):
        component = ring_area(polygon[0]) - sum(ring_area(r) for r in polygon[1:])
        if component <= 0:
            raise ValueError("Polygon area is non-positive; check exterior and holes.")
        total += component
    return {"square_metres": total, "acres": total / ACRE_M2,
            "method": method, "approximate": approximate,
            "limitation": "Topology is not fully validated; input must be a valid, non-overlapping parcel geometry."}


def arcgis_geometry(geometry=None, point=None):
    if geometry:
        rings = []
        for polygon in polygons(geometry):
            for index, ring in enumerate(polygon):
                clean = [p[:2] for p in ring]
                # Esri: exterior clockwise, holes counter-clockwise.
                if (signed_planar_area(clean) > 0) == (index == 0):
                    clean = list(reversed(clean))
                rings.append(clean)
        return "esriGeometryPolygon", {"rings": rings, "spatialReference": {"wkid": 4326}}
    return "esriGeometryPoint", {"x": point[0], "y": point[1], "spatialReference": {"wkid": 4326}}


def query_features(url, geometry=None, point=None, fields="*", timeout=15):
    kind, spatial = arcgis_geometry(geometry, point)
    collected = []
    for offset in range(0, 10000, 1000):
        page = request_json(url + "/query", {
            "f": "geojson", "where": "1=1", "geometry": json.dumps(spatial),
            "geometryType": kind, "inSR": 4326, "outSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", "outFields": fields,
            "returnGeometry": "true", "resultOffset": offset, "resultRecordCount": 1000,
            "orderByFields": "OBJECTID ASC"}, timeout)
        if not isinstance(page, dict) or not isinstance(page.get("features"), list):
            raise Unavailable("unexpected_service_schema")
        collected.extend(page["features"])
        if not page.get("exceededTransferLimit") and len(page["features"]) < 1000:
            return {"type": "FeatureCollection", "features": collected}
        if not page["features"]:
            raise Unavailable("incomplete_pagination")
    raise Unavailable("query_limit_exceeded")


def soil_summary(features):
    units, classes = [], set()
    for feature in features:
        properties = feature.get("properties", {})
        components = []
        for i in range(1, 4):
            raw_class = properties.get(f"CLI{i}")
            if raw_class is None or not str(raw_class).strip():
                continue
            cls = str(raw_class).strip()
            classes.add(cls)
            components.append({"class": cls, "percent_of_mapping_unit": properties.get(f"PERCENT{i}"),
                               "soil_name": properties.get(f"SOIL_NAME{i}")})
        units.append({"objectid": properties.get("OBJECTID"), "label": properties.get("CLI_SYS"),
                      "components": components})
    numeric = {c for c in classes if c in set("1234567")}
    finding = "lower_class_exception_needs_review" if numeric & set("123") else (
        "mapped_classes_in_default_range" if classes and classes <= set("4567") else "classification_needs_review")
    return {"classes": sorted(classes), "mapping_units": units, "preliminary_finding": finding,
            "class_area_percentages": None, "overall_parcel_pass": None,
            "limitation": "Intersecting classes are not clipped acreage shares; mixed-unit proportions do not locate components."}


def slope_percent(rise_m, run_m):
    if not math.isfinite(rise_m) or not math.isfinite(run_m) or run_m <= 0:
        raise ValueError("Rise/run must be finite metres; horizontal run must be positive.")
    return abs(rise_m) / run_m * 100


def distance_m(a, b):
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    x = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * AUTHALIC_RADIUS_M * math.asin(math.sqrt(min(1, max(0, x))))


def profile_summary(points):
    samples = []
    missing = 0
    for a, b in zip(points, points[1:]):
        if a.get("altitude") is None or b.get("altitude") is None:
            missing += 1
            continue
        start, end = a["geometry"]["coordinates"], b["geometry"]["coordinates"]
        run = distance_m(start, end)
        if run <= 0:
            continue
        samples.append({"start": start, "end": end, "rise_m": b["altitude"] - a["altitude"],
                        "run_m": run, "slope_percent": slope_percent(b["altitude"] - a["altitude"], run)})
    if not samples:
        raise Unavailable("no_elevation_samples")
    maximum = max(s["slope_percent"] for s in samples)
    return {"method": "CDEM consecutive profile samples", "maximum_sampled_percent": maximum,
            "sample_exceeds_15_percent": maximum > 15, "segments": samples,
            "missing_segments": missing, "overall_parcel_pass": None,
            "limitation": "Coarse sampled profile; not a parcel slope map or bare-earth certification."}


def map_bbox(geometry=None, point=None):
    coords = [p for polygon in polygons(geometry) for ring in polygon for p in ring] if geometry else [point]
    xs, ys = [p[0] for p in coords], [p[1] for p in coords]
    dx, dy = max((max(xs) - min(xs)) * .15, .001), max((max(ys) - min(ys)) * .15, .001)
    return [min(xs) - dx, min(ys) - dy, max(xs) + dx, max(ys) + dy]


def export_soil_map(out, geometry=None, point=None, timeout=15):
    bbox = map_bbox(geometry, point)
    endpoint = SOIL.rsplit("/", 1)[0] + "/export"
    image_info = request_json(endpoint, {"f": "json", "bbox": ",".join(map(str, bbox)),
        "bboxSR": 4326, "imageSR": 4326, "size": "1200,900", "format": "png32",
        "transparent": "false", "layers": "show:29"}, timeout)
    href = image_info.get("href")
    if not href or urlparse(href).scheme != "https" or urlparse(href).hostname != urlparse(SOIL).hostname:
        raise Unavailable("unsupported_image_response")
    try:
        with urlopen(Request(href, headers={"User-Agent": "OntarioSolarLandSoilSkill/1.0"}), timeout=timeout) as response:
            image = response.read(20_000_001)
            if len(image) > 20_000_000 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
                raise Unavailable("invalid_map_image")
        (out / "soil-map.png").write_bytes(image)
        save_json(out / "evidence" / "soil-map-metadata.json", {"bbox_requested_wgs84": bbox,
            "export_response": image_info, "scope": "context image; parcel/point overlay not included",
            "retrieved_at": utc_now()})
        return {"path": "soil-map.png", "boundary_overlay": False,
                "limitation": "Raw soil layer context only; add labelled parcel/point and basemap before using as a parcel screenshot."}
    except HTTPError as exc:
        raise Unavailable("authentication_required" if exc.code == 401 else "access_denied" if exc.code == 403 else f"http_{exc.code}") from exc
    except (URLError, TimeoutError, socket.timeout):
        raise Unavailable("map_download_unavailable")


def render_report(report):
    labels = {"address_candidates": "Address candidates", "location": "Assessment location", "boundary": "Parcel boundary",
        "pin": "PIN", "arn": "ARN", "area": "Parcel area", "soil": "Agricultural soil capability",
        "soil_map": "Soil map", "base_map": "Base or topographic map", "slope_sample": "Sampled slope",
        "slope_full_area": "Full-parcel slope", "wetlands": "Wetlands",
        "transmission": "Transmission corridors", "pipelines": "Gas pipelines", "railroads": "Railroads"}
    statuses = {"verified": "Verified", "provided": "User-provided", "estimated": "Estimated or sampled",
                "needs_review": "Needs review", "skipped": "Skipped"}
    lines = ["# Land Location and Size and Soil and Slope Assessment", "",
             "This report covers only the first two sections of the evaluation process and does not determine overall project eligibility.", "",
             f"Generated at: {report['generated_at']}", "", "| Indicator | Status | Reason or scope |", "|---|---|---|"]
    for key, item in report["metrics"].items():
        detail = (item.get("reason") or item.get("scope", "")).replace("_", " ")
        lines.append(f"| {labels.get(key, key)} | {statuses[item['status']]} | {detail} |")
    for key, item in report["metrics"].items():
        if item["value"] is not None:
            lines.extend(["", "## " + labels.get(key, key), "", "```json",
                          json.dumps(item["value"], ensure_ascii=False, indent=2), "```"])
        if item.get("source"):
            lines.extend(["", f"Source: {item['source']}"])
    lines.extend(["", "## Next steps", "",
                  "Confirm the candidate address against the actual parcel. Skipped indicators are neither passed nor failed; point-level soil and sampled slope evidence do not characterize the entire parcel.",
                  "Keep login-dependent sources skipped without requesting credentials. Update this report when publicly accessible boundary, map, or terrain data becomes available.", ""])
    return "\n".join(lines)


def assess(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    geometry = load_geometry(args.boundary) if args.boundary else None
    point = [args.lon, args.lat] if args.lon is not None else None
    fields = {key: metric("skipped", reason="not_collected") for key in (
        "address_candidates", "location", "boundary", "pin", "arn", "area", "soil", "soil_map",
        "base_map", "slope_sample", "slope_full_area", "wetlands", "transmission", "pipelines", "railroads")}
    report = {"schema_version": "1.0", "generated_at": utc_now(), "scope": ["land_location_and_size", "soil_and_slope"],
              "input": {"address": args.address, "boundary_file": str(Path(args.boundary).resolve()) if args.boundary else None},
              "overall_project_decision": None, "metrics": fields}
    for key in ("pin", "arn"):
        value = getattr(args, key)
        fields[key] = metric("provided", value, "user_input") if value else metric("skipped", reason="not_supplied_or_publicly_verified")
    fields["boundary"] = metric(args.boundary_status, geometry, args.boundary_source or "user_uploaded_geojson") if geometry else metric("skipped", reason="no_confirmed_public_boundary")
    if geometry:
        measured = area_m2(geometry)
        fields["area"] = metric("estimated" if measured["approximate"] else args.boundary_status,
                                measured, args.boundary_source or "user_uploaded_geojson", scope="supplied polygon")
    else:
        fields["area"] = metric("skipped", reason="boundary_unavailable")
    if point:
        fields["location"] = metric(args.location_status, {"longitude": point[0], "latitude": point[1]}, "explicit_input", scope="point, not parcel")

    def collect(key, source, filename, fn, transform=lambda x: x, status="verified", scope=""):
        if args.offline:
            fields[key] = metric("skipped", source=source, reason="offline_requested")
            return
        try:
            data = fn()
            if filename:
                save_json(out / "evidence" / filename, {"retrieved_at": utc_now(), "source": source, "data": data})
            fields[key] = metric(status, transform(data), source, retrieved_at=utc_now(), scope=scope)
        except Unavailable as exc:
            fields[key] = metric("skipped", source=source, reason=exc.reason)
        except (ValueError, KeyError, TypeError):
            fields[key] = metric("skipped", source=source, reason="unexpected_service_schema")

    if args.address:
        collect("address_candidates", GEOCODER, "address-candidates.json",
                lambda: request_json(GEOCODER, {"q": args.address, "lang": "en", "keys": "locate"}, args.timeout),
                status="needs_review", scope="candidates only; no automatic selection")
    if geometry or point:
        scope = "intersecting parcel mapping units" if geometry else "provisional point only"
        collect("soil", SOIL, "soil.geojson.json",
                lambda: query_features(SOIL, geometry, point, SOIL_FIELDS, args.timeout),
                lambda d: soil_summary(d["features"]),
                status="verified" if geometry and args.boundary_status == "verified" else "estimated", scope=scope)
        soil = fields["soil"]
        if soil["value"] and (not soil["value"]["classes"] or soil["value"]["preliminary_finding"] != "mapped_classes_in_default_range"):
            soil["status"] = "needs_review"
        collect("wetlands", WETLAND, "wetlands.geojson.json",
                lambda: query_features(WETLAND, geometry, point, timeout=args.timeout),
                lambda d: {"mapped_intersections": len(d["features"]), "absence_confirmed": False,
                           "nearby_buffer_checked": False, "coverage_and_date_review_required": True},
                status="needs_review", scope="parcel intersection" if geometry else "point intersection only")
        collect("soil_map", SOIL.rsplit("/", 1)[0] + "/export", None,
                lambda: export_soil_map(out, geometry, point, args.timeout),
                status="estimated", scope="soil-only context image")
    else:
        for key in ("soil", "soil_map", "wetlands"):
            fields[key] = metric("skipped", reason="no_selected_location_or_boundary")
    if args.rise_m is not None:
        grade = slope_percent(args.rise_m, args.run_m)
        fields["slope_sample"] = metric("estimated", {"method": "provided contour rise/run", "rise_m": args.rise_m,
            "run_m": args.run_m, "slope_percent": grade, "sample_exceeds_15_percent": grade > 15,
            "overall_parcel_pass": None}, "user_measurement", scope="one measured segment only")
    elif args.profile_start:
        start, end = args.profile_start, args.profile_end
        path = f"LINESTRING({start[0]} {start[1]}, {end[0]} {end[1]})"
        collect("slope_sample", PROFILE, "elevation-profile.json",
                lambda: request_json(PROFILE, {"path": path, "steps": 20}, args.timeout),
                profile_summary, status="estimated", scope="explicit sampled path only")
    else:
        fields["slope_sample"] = metric("skipped", reason="no_documented_contour_measurement_or_profile")
    fields["slope_full_area"] = metric("skipped", reason="suitable_parcel_clipped_dtm_not_processed")
    for key in ("base_map", "transmission", "pipelines", "railroads"):
        fields[key] = metric("skipped", reason="public_map_review_not_yet_performed")
    save_json(out / "assessment.json", report)
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    return report


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--address")
    parser.add_argument("--boundary")
    parser.add_argument("--boundary-source")
    parser.add_argument("--boundary-status", choices=["provided", "estimated", "verified"], default="provided")
    parser.add_argument("--location-status", choices=["provided", "estimated", "verified"], default="estimated")
    parser.add_argument("--lon", type=float)
    parser.add_argument("--lat", type=float)
    parser.add_argument("--pin")
    parser.add_argument("--arn")
    parser.add_argument("--rise-m", type=float)
    parser.add_argument("--run-m", type=float)
    parser.add_argument("--profile-start", nargs=2, type=float, metavar=("LON", "LAT"))
    parser.add_argument("--profile-end", nargs=2, type=float, metavar=("LON", "LAT"))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    for a, b in ((args.lon, args.lat), (args.rise_m, args.run_m), (args.profile_start, args.profile_end)):
        if (a is None) != (b is None):
            parser.error("Paired coordinate, rise/run, and profile arguments must be supplied together.")
    points = ([args.lon, args.lat],) if args.lon is not None else ()
    points += tuple(p for p in (args.profile_start, args.profile_end) if p)
    for lon, lat in points:
        if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            parser.error("Invalid longitude/latitude.")
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.timeout > 60:
        parser.error("Timeout must be between 0 and 60 seconds.")
    if args.rise_m is not None:
        try:
            slope_percent(args.rise_m, args.run_m)
        except ValueError as exc:
            parser.error(str(exc))
    if not any((args.address, args.boundary, args.lon is not None, args.rise_m is not None, args.profile_start)):
        parser.error("Provide an address, boundary, point, contour measurement, or profile.")
    return args


if __name__ == "__main__":
    try:
        result = assess(parse_args())
        print(json.dumps({"status": "partial_assessment_created", "output_directory": str(Path(sys.argv[sys.argv.index('--out') + 1]).resolve())
                         if '--out' in sys.argv else None,
                         "skipped": {k: v["reason"] for k, v in result["metrics"].items() if v["status"] == "skipped"}}, ensure_ascii=True))
    except (ValueError, OSError) as exc:
        print(f"Input/output error: {exc}", file=sys.stderr)
        sys.exit(2)
