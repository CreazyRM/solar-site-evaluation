"""Offline checks of route, evidence and utility screening invariants."""
import copy
import unittest
from unittest.mock import patch
import assess
import assess_full as full

def trial(size, result, feeder="F1"):
    return {"project_kw": size, "result": result, "station": "Synthetic DS", "feeder": feeder,
            "distributor": "Synthetic utility", "project_type": "exporting", "technology": "inverter_based_solar",
            "source": "synthetic_fixture", "retrieved_at": "2026-10-09T00:00:00Z", "evidence_locator": "offline_test"}

class FullTests(unittest.TestCase):
    def test_road_trace_not_chord(self):
        coords = [[-81,45],[-81,45.01],[-80.99,45.01]]
        distance = full.route_summary({"type":"LineString","coordinates":coords})["distance_m"]
        self.assertGreater(distance, assess.distance_m(coords[0],coords[-1]))
        self.assertTrue(1800 < distance < 2000)
        for bad in [[[0,0],[0,0]], [[181,0],[0,0]], [[0,0],[float('nan'),0]]]:
            with self.assertRaises(ValueError):
                full.route_summary({"type":"LineString","coordinates":bad})

    def test_capacity_is_bounded_not_exact(self):
        summary = full.capacity_summary([trial(2000,"pass"),trial(3000,"pass"),trial(4000,"fail")])
        self.assertEqual(summary["target_result"], "pass")
        self.assertEqual(summary["highest_tested_pass_kw"], 3000)
        self.assertEqual(summary["next_tested_fail_kw"], 4000)
        self.assertIsNone(summary["exact_maximum_kw"])
        self.assertFalse(summary["capacity_reserved"])
        self.assertIsNone(full.capacity_summary([trial(3000,"pass")])["target_result"])

    def test_scenario_and_conflict(self):
        with self.assertRaises(ValueError):
            full.capacity_summary([trial(2000,"pass"),trial(3000,"fail","F2")])
        with self.assertRaises(ValueError):
            full.capacity_summary([trial(2000,"pass"),trial(2000,"fail")])
        self.assertTrue(full.capacity_summary([trial(2000,"fail"),trial(3000,"pass")])["non_monotonic_results"])

    def test_provenance_and_skip(self):
        with self.assertRaises(ValueError):
            full.validate_observation({"status":"verified","value":True,"source":"somewhere"})
        with self.assertRaises(ValueError):
            full.validate_observation({"status":"skipped","value":0,"reason":"no_data"})

    def test_preserve_original_and_unknown_target(self):
        base={"metrics":{"soil":{"status":"provided","value":{"classes":["2"]},"source":"user_file"}}}
        original=copy.deepcopy(base)
        result=full.extend(base, capacity_tests=[trial(3000,"pass")])
        self.assertEqual(base,original)
        self.assertEqual(result["metrics"]["soil"],base["metrics"]["soil"])
        self.assertEqual(result["metrics"]["capacity_2000_kw"]["status"],"skipped")
        self.assertEqual(result["metrics"]["station"]["value"],"Synthetic DS")
        self.assertIsNone(result["overall_project_decision"])
        skipped=full.extend(base,route={"status":"skipped","value":None,"reason":"route_unavailable"})
        self.assertIsNone(skipped["metrics"]["interconnection_distance"]["value"])

    def test_geowarehouse_excluded_without_network(self):
        with patch.object(assess, "urlopen") as network:
            with self.assertRaises(assess.Unavailable) as error:
                assess.request_json("https://collaboration.geowarehouse.ca/", {})
            self.assertEqual(error.exception.reason,"source_excluded_by_user_geowarehouse")
            network.assert_not_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)
