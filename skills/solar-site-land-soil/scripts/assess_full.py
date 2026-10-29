"""Merge sourced site observations and compute route/capacity screening evidence.

No credentials or private utility endpoints. Importable standard-library functions
are independent of the Codex UI and can be reused in a future web backend.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import assess

FIELDS = {
    "municipality": "Municipality",
    "access_road": "Existing access road and truck access",
    "line_phases": "Phases on the candidate connection line",
    "interconnection_distance": "Road-following interconnection distance",
    "distributor": "Local electricity distributor",
    "station": "Station name",
    "feeder": "Feeder name",
    "hosting_capacity": "Mapped DER hosting capacity",
    "capacity_2000_kw": "Calculator result for 2,000 kW",
    "maximum_tested_capacity": "Highest tested passing capacity",
    "zoning": "Parcel zoning and exception codes",
    "solar_permitted_use": "Ground-mounted solar permitted use",
    "official_plan": "Official Plan land-use designation",
    "planning_exceptions": "Applicable amendments and exception provisions",
}
STATUSES = {"verified", "provided", "estimated", "needs_review", "skipped"}

def validate_observation(item):
    """Require evidence provenance; skipped values must remain null."""
    if item.get("status") not in STATUSES:
        raise ValueError("Observation has an unsupported status.")
    if item["status"] == "skipped":
        if item.get("value") is not None or not item.get("reason"):
            raise ValueError("A skipped observation needs a reason and a null value.")
    elif item.get("value") is None or not all(item.get(k) for k in ("source", "retrieved_at", "evidence_locator")):
        raise ValueError("Collected observations need value, source, retrieved_at and evidence_locator.")
    return copy.deepcopy(item)

def route_summary(route):
    """Measure an explicitly traced WGS84 route, not a straight-line substitute."""
    coords = route.get("coordinates", [])
    if route.get("type") != "LineString" or len(coords) < 2:
        raise ValueError("Route must be a WGS84 LineString with at least two vertices.")
    for point in coords:
        if len(point) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in point):
            raise ValueError("Route vertices need two finite numeric coordinates.")
        if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            raise ValueError("Route longitude/latitude is out of range.")
    distance = sum(assess.distance_m(a, b) for a, b in zip(coords, coords[1:]))
    if distance <= 0:
        raise ValueError("Route must have positive length.")
    return {"distance_m": distance, "method": "Sum of spherical geodesic segments on supplied road-following vertices",
            "coordinates": coords, "includes_site_to_access_segment": None,
            "connection_point_confirmed": False, "legal_access_confirmed": False}

def capacity_summary(tests, target_kw=2000):
    """Retain bounded calculator observations without inventing an exact maximum."""
    required = ("station", "feeder", "distributor", "source", "retrieved_at", "evidence_locator", "project_type", "technology")
    if not tests:
        raise ValueError("Capacity tests cannot be empty.")
    first = tests[0]
    observed = {}
    for test in tests:
        if not all(test.get(k) for k in required):
            raise ValueError("Capacity tests require station, feeder, scenario and evidence provenance.")
        if test["project_type"] != "exporting" or test["technology"] != "inverter_based_solar":
            raise ValueError("Capacity tests must use exporting inverter-based solar.")
        if any(test[k] != first[k] for k in ("station", "feeder", "distributor", "project_type", "technology")):
            raise ValueError("Different feeders or scenarios must not be combined.")
        size = test.get("project_kw")
        if isinstance(size, bool) or not isinstance(size, (float, int)) or not math.isfinite(size) or size <= 0:
            raise ValueError("Project capacity must be a positive finite kW value.")
        if test.get("result") not in ("pass", "fail"):
            raise ValueError("Only actual calculator pass/fail observations belong in capacity_tests.")
        if size in observed and observed[size] != test["result"]:
            raise ValueError("Conflicting results at the same size require separate review.")
        observed[size] = test["result"]
    passes = [kw for kw, result in observed.items() if result == "pass"]
    fails = [kw for kw, result in observed.items() if result == "fail"]
    highest = max(passes) if passes else None
    inconsistent = bool(passes and fails and min(fails) < highest)
    return {"target_kw": target_kw, "target_result": observed.get(target_kw),
            "highest_tested_pass_kw": highest,
            "next_tested_fail_kw": min((x for x in fails if highest is not None and x > highest), default=None),
            "tested_upper_limit_kw": max(observed), "exact_maximum_kw": None,
            "non_monotonic_results": inconsistent, "capacity_reserved": False,
            "tests": copy.deepcopy(tests)}

def extend(base, observations=None, route=None, capacity_tests=None):
    report = copy.deepcopy(base)
    report["schema_version"] = "2.0"
    report["generated_at"] = assess.utc_now()
    report["scope"] = ["land_location_and_size", "soil_and_slope", "interconnection_distance", "interconnection_electrical_capacity", "zoning_and_official_plan"]
    report["overall_project_decision"] = None
    fields = report.setdefault("metrics", {})
    for key in FIELDS:
        fields[key] = assess.metric("skipped", reason="not_collected_from_accessible_source")
    for key, value in (observations or {}).items():
        if key not in FIELDS:
            raise ValueError("Unknown extension observation: " + key)
        fields[key] = validate_observation(value)
    if route:
        provenance = validate_observation(route)
        if provenance["status"] == "skipped":
            fields["interconnection_distance"] = provenance
        else:
            value = route_summary(route["value"])
            fields["interconnection_distance"] = {**provenance, "status": "estimated", "value": value}
    if capacity_tests:
        summary = capacity_summary(capacity_tests)
        provenance = {key: capacity_tests[0][key] for key in ("source", "retrieved_at", "evidence_locator")}
        for key in ("distributor", "station", "feeder"):
            previous = fields[key]
            if isinstance(previous.get("value"), str) and previous["value"] != capacity_tests[0][key]:
                raise ValueError("Capacity tests conflict with the collected " + key + ".")
            if previous["status"] == "skipped":
                fields[key] = assess.metric("needs_review", capacity_tests[0][key], **provenance,
                    scope="Calculator scenario; parcel service relationship still needs confirmation")
        fields["maximum_tested_capacity"] = assess.metric("needs_review", summary, **provenance)
        if summary["target_result"] is not None:
            target_test = next(t for t in capacity_tests if t["project_kw"] == 2000)
            fields["capacity_2000_kw"] = assess.metric("needs_review", {"result": summary["target_result"], "project_kw": 2000,
                "station": target_test["station"], "feeder": target_test["feeder"], "capacity_reserved": False},
                **{key: target_test[key] for key in ("source", "retrieved_at", "evidence_locator")})
        else:
            fields["capacity_2000_kw"] = assess.metric("skipped", reason="no_exact_2000_kw_calculator_test")
    report["source_exclusions"] = [{"source": "GeoWarehouse", "reason": "access_unavailable_confirmed_by_user"}]
    return report

def render_full(report):
    lines = ["# Ontario Solar Site Evaluation", "", "Public-source screening across all five evaluation sections. No overall development approval is assigned.", "",
             "Generated at: " + report["generated_at"], "", "## Required indicators", "", "| Indicator | Status | Reason or scope |", "|---|---|---|"]
    for key, item in report["metrics"].items():
        detail = str(item.get("reason") or item.get("scope") or "See sourced evidence below").replace("|", "\\|")
        lines.append(f"| {FIELDS.get(key, key.replace('_', ' ').title())} | {item['status']} | {detail} |")
    for key, item in report["metrics"].items():
        lines.extend(["", "## " + FIELDS.get(key, key.replace('_', ' ').title()), ""])
        if item.get("value") is not None:
            lines.extend(["```json", json.dumps(item["value"], ensure_ascii=False, indent=2), "```"])
        else:
            lines.append("Skipped: " + item.get("reason", "not_collected"))
        for label in ("source", "retrieved_at", "data_date", "evidence_locator"):
            if item.get(label):
                lines.append(label.replace('_', ' ').title() + ": " + str(item[label]))
    lines.extend(["", "## Interpretation", "", "GeoWarehouse is excluded. Missing public PIN/title information remains unknown. Calculator results are preliminary and do not reserve capacity. Zoning and Official Plan findings require cited provisions and current amendments; an unidentified exception is not permission. Route distance does not establish legal access or a utility-approved connection point.", ""])
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Existing land/soil assessment.json")
    parser.add_argument("--observations", help="JSON object containing observations, route and capacity_tests")
    parser.add_argument("--zoning-layer", help="Anonymous authoritative ArcGIS polygon layer URL")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    base = json.loads(Path(args.base).read_text(encoding="utf-8-sig"))
    additions = json.loads(Path(args.observations).read_text(encoding="utf-8-sig")) if args.observations else {}
    result = extend(base, **additions)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.zoning_layer:
        boundary = base.get("metrics", {}).get("boundary", {}).get("value")
        if boundary and boundary.get("type") == "Feature":
            boundary = boundary["geometry"]
        if not boundary or boundary.get("type") not in ("Polygon", "MultiPolygon"):
            result["metrics"]["zoning"] = assess.metric("skipped", reason="parcel_geometry_unavailable")
        else:
            try:
                data = assess.query_features(args.zoning_layer, geometry=boundary)
                timestamp = assess.utc_now()
                assess.save_json(out/"evidence"/"zoning.geojson.json", {"source": args.zoning_layer, "retrieved_at": timestamp, "data": data})
                result["metrics"]["zoning"] = assess.metric("needs_review", data, args.zoning_layer,
                    retrieved_at=timestamp, evidence_locator="evidence/zoning.geojson.json", scope="Intersecting polygons; match codes to operative by-law text")
            except assess.Unavailable as exc:
                result["metrics"]["zoning"] = assess.metric("skipped", source=args.zoning_layer, reason=exc.reason)
    assess.save_json(out/"assessment.json", result)
    (out/"report.md").write_text(render_full(result), encoding="utf-8")
    print(json.dumps({"status": "full_scope_partial_report_created", "output_directory": str(out.resolve())}))

if __name__ == "__main__":
    main()
