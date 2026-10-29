#!/usr/bin/env python3
"""Offline behavioral checks; synthetic geometry and mocked anonymous services."""
import argparse
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import assess


class AssessmentTests(unittest.TestCase):
    def test_source_contour_example(self):
        self.assertAlmostEqual(assess.slope_percent(7, 127.04), 5.5100755668, places=8)

    def test_slope_cutoff_and_units(self):
        self.assertEqual(assess.slope_percent(-15, 100), 15)
        self.assertFalse(assess.slope_percent(15, 100) > 15)
        self.assertTrue(assess.slope_percent(15.01, 100) > 15)
        for rise, run in ((1, 0), (1, -1), (math.nan, 10), (1, math.inf)):
            with self.assertRaises(ValueError):
                assess.slope_percent(rise, run)

    def test_area_hole_and_winding(self):
        exterior = [[-81, 45], [-80.99, 45], [-80.99, 45.01], [-81, 45.01], [-81, 45]]
        hole = [[-80.998, 45.002], [-80.996, 45.002], [-80.996, 45.004], [-80.998, 45.004], [-80.998, 45.002]]
        area = assess.area_m2({"type": "Polygon", "coordinates": [exterior]})["square_metres"]
        holed = assess.area_m2({"type": "Polygon", "coordinates": [exterior, hole]})
        self.assertTrue(830000 < area < 900000)
        self.assertTrue(0.95 < holed["square_metres"] / area < 0.97)
        reverse = assess.area_m2({"type": "Polygon", "coordinates": [list(reversed(exterior))]})
        self.assertAlmostEqual(area, reverse["square_metres"], places=5)

    def test_arcgis_ring_orientation(self):
        exterior = [[-81, 45], [-80.99, 45], [-80.99, 45.01], [-81, 45.01], [-81, 45]]
        hole = [[-80.998, 45.002], [-80.996, 45.002], [-80.996, 45.004], [-80.998, 45.004], [-80.998, 45.002]]
        _, value = assess.arcgis_geometry({"type": "Polygon", "coordinates": [exterior, hole]})
        self.assertLess(assess.signed_planar_area(value["rings"][0]), 0)
        self.assertGreater(assess.signed_planar_area(value["rings"][1]), 0)

    def test_soil_composition_and_exceptions(self):
        result = assess.soil_summary([{"properties": {"CLI1": "7", "PERCENT1": 70, "CLI2": "1", "PERCENT2": 30}}])
        self.assertEqual(result["classes"], ["1", "7"])
        self.assertEqual(result["mapping_units"][0]["components"][1]["percent_of_mapping_unit"], 30)
        self.assertEqual(result["preliminary_finding"], "lower_class_exception_needs_review")
        self.assertIsNone(result["class_area_percentages"])
        self.assertIsNone(result["overall_parcel_pass"])
        organic = assess.soil_summary([{"properties": {"CLI1": "O"}}])
        self.assertEqual(organic["preliminary_finding"], "classification_needs_review")

    def test_elevation_nodata_is_not_flat(self):
        points = [{"altitude": None, "geometry": {"coordinates": [-81, 45]}},
                  {"altitude": 100, "geometry": {"coordinates": [-81, 45.001]}}]
        with self.assertRaises(assess.Unavailable):
            assess.profile_summary(points)

    def test_http_login_is_skipped(self):
        with patch.object(assess, "urlopen", side_effect=HTTPError("https://example.org", 401, "Unauthorized", {}, None)):
            with self.assertRaises(assess.Unavailable) as context:
                assess.request_json("https://example.org", {})
        self.assertEqual(context.exception.reason, "authentication_required")

    def test_failed_service_does_not_block_contour_or_wetlands(self):
        def query(url, *unused_args, **unused_kwargs):
            if url == assess.SOIL:
                raise assess.Unavailable("authentication_required")
            return {"type": "FeatureCollection", "features": []}
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(out=directory, boundary=None, boundary_status="provided", boundary_source=None,
                address=None, lon=-81, lat=45, location_status="estimated", pin="001234567", arn=None,
                rise_m=7, run_m=127.04, profile_start=None, profile_end=None, offline=False, timeout=1)
            with patch.object(assess, "query_features", side_effect=query), patch.object(
                    assess, "export_soil_map", side_effect=assess.Unavailable("authentication_required")):
                report = assess.assess(args)
            self.assertEqual(report["metrics"]["soil"]["status"], "skipped")
            self.assertEqual(report["metrics"]["soil"]["reason"], "authentication_required")
            self.assertEqual(report["metrics"]["slope_sample"]["status"], "estimated")
            self.assertEqual(report["metrics"]["pin"]["value"], "001234567")
            self.assertEqual(report["metrics"]["wetlands"]["value"]["mapped_intersections"], 0)
            self.assertFalse(report["metrics"]["wetlands"]["value"]["absence_confirmed"])
            self.assertTrue((Path(directory) / "report.md").exists())
            loaded = json.loads((Path(directory) / "assessment.json").read_text(encoding="utf-8"))
            self.assertIsNone(loaded["overall_project_decision"])

    def test_boundary_requires_closed_wgs84_ring(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "parcel.geojson"
            assess.save_json(path, {"type": "Polygon", "coordinates": [[[500000, 4500000], [501000, 4500000], [501000, 4501000], [500000, 4500000]]]})
            with self.assertRaises(ValueError):
                assess.load_geometry(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
