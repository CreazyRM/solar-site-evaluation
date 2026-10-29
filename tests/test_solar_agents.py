"""Offline behavioral tests for frozen inputs, evidence ownership and review gates."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('solar_agents', ROOT/'scripts'/'solar_agents.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'tmp')
        self.root = Path(self.temp.name)
        self.parcel = self.root/'parcel.geojson'
        flow.write(self.parcel, {'type': 'Polygon', 'coordinates': [[[-81,44],[-80.99,44],[-80.99,44.01],[-81,44]]]})
        self.run = self.root/'run'
        self.manifest = flow.initialize(self.parcel, 'Synthetic test site', 'synthetic fixture', 'Synthetic fixture only', self.run, offline=True)
        self.populate()

    def tearDown(self):
        self.temp.cleanup()

    def populate(self):
        for role in self.manifest['roles']:
            metrics = [{'indicator': indicator, 'status': 'skipped', 'value': None, 'sources': [],
                        'spatial_scope': 'Not assessed in synthetic test', 'method': 'No collection',
                        'limitations': ['Synthetic test only'], 'evidence_files': [], 'reason': 'Synthetic unavailable data'}
                       for indicator in flow.ROLES[role]]
            flow.write(self.run/role/'result.json', {'schema_version': '1.0', 'run_id': self.manifest['run_id'],
                       'agent': role, 'boundary_sha256': self.manifest['boundary_sha256'], 'generated_at': flow.now(),
                       'metrics': metrics, 'summary': 'Synthetic test only; no assessment performed.'})

    def ready(self):
        snapshot = flow.validate(self.run)
        review = {'schema_version': '1.0', 'run_id': self.manifest['run_id'], 'agent': 'evidence_reviewer',
                  'boundary_sha256': self.manifest['boundary_sha256'], 'generated_at': flow.now(), 'verdict': 'ready',
                  'reviewed_sha256': snapshot['reviewed_sha256'], 'issues': [], 'summary': 'Synthetic review fixture.'}
        flow.write(self.run/'review'/'review.json', review)

    def mutate(self, change):
        file = self.run/'land_environment'/'result.json'
        data = flow.read(file)
        change(data)
        flow.write(file, data)

    def evidence(self):
        flow.write(self.run/'land_environment'/'soil-evidence.json', {'fixture': True, 'date': '2026-10-02'})
        def change(data):
            data['metrics'][0].update(status='provided', value={'classes': [4]}, reason=None,
                sources=[{'source_url': 'synthetic fixture', 'retrieved_at': '2026-10-02T00:00:00Z', 'data_date': '2026-10-02', 'evidence_locator': 'fixture field'}],
                evidence_files=['land_environment/soil-evidence.json'])
        self.mutate(change)

    def test_reviewed_partial_assembly_preserves_nulls_and_dates(self):
        self.evidence()
        self.ready()
        output = flow.assemble(self.run)
        result = flow.read(output['assessment'])
        self.assertIsNone(result['overall_project_decision'])
        self.assertIsNone(result['metrics']['capacity_2mw']['value'])
        self.assertEqual(result['metrics']['soil']['retrieved_at'], '2026-10-02T00:00:00Z')
        self.assertTrue(result['multi_agent_audit']['offline'])

    def test_no_review_cannot_assemble(self):
        with self.assertRaises(OSError):
            flow.assemble(self.run)

    def test_boundary_change_invalidates_workers(self):
        (self.run/'inputs'/'parcel.geojson').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Frozen parcel changed'):
            flow.validate(self.run)

    def test_missing_or_unowned_indicator_is_rejected(self):
        self.mutate(lambda data: data['metrics'].pop())
        with self.assertRaisesRegex(ValueError, 'Missing or unowned'):
            flow.validate(self.run)

    def test_unavailable_is_not_false(self):
        self.mutate(lambda data: data['metrics'][0].update(value=False))
        with self.assertRaisesRegex(ValueError, 'null value'):
            flow.validate(self.run)

    def test_verified_claim_without_evidence_is_rejected(self):
        self.mutate(lambda data: data['metrics'][0].update(status='verified', value=4))
        with self.assertRaisesRegex(ValueError, 'saved evidence'):
            flow.validate(self.run)

    def test_cross_worker_evidence_is_rejected(self):
        self.evidence()
        self.mutate(lambda data: data['metrics'][0].update(evidence_files=['planning/assignment.json']))
        with self.assertRaisesRegex(ValueError, 'inside land_environment'):
            flow.validate(self.run)

    def test_changed_result_requires_new_review(self):
        self.ready()
        self.mutate(lambda data: data.update(summary='Changed after review'))
        with self.assertRaisesRegex(ValueError, 'Reviewed files changed'):
            flow.assemble(self.run)

    def test_diff_does_not_approve_changed_results(self):
        self.ready()
        baseline = self.run/'review'/'review.json'
        delta = flow.review_diff(self.run, baseline)
        self.assertEqual(delta['changed_files'], [])
        self.mutate(lambda data: data.update(summary='Changed computation summary'))
        delta = flow.review_diff(self.run, baseline)
        self.assertIn('land_environment/result.json', delta['changed_files'])
        self.assertEqual(delta['affected_indicators']['land_environment'], flow.ROLES['land_environment'])
        self.assertTrue(delta['independent_review_required'])
        with self.assertRaisesRegex(ValueError, 'Reviewed files changed'):
            flow.assemble(self.run)

    def test_coordinator_change_expands_diff_scope(self):
        self.ready()
        path=self.run/'coordinator'/'assessment.json'
        data=flow.read(path);data['input']['note']='Changed context';flow.write(path,data)
        delta=flow.review_diff(self.run,self.run/'review'/'review.json')
        self.assertTrue(all(delta['affected_indicators'][r]==flow.ROLES[r] for r in self.manifest['roles']))

    def test_rejected_baseline_cannot_reuse_checks(self):
        self.ready()
        path=self.run/'review'/'review.json'
        review=flow.read(path);review['verdict']='needs_revision';flow.write(path,review)
        delta=flow.review_diff(self.run,path)
        self.assertFalse(delta['can_reuse_unchanged_prior_checks'])
        self.assertTrue(all(delta['affected_indicators'][r]==flow.ROLES[r] for r in self.manifest['roles']))

    def test_changed_raw_evidence_requires_new_review(self):
        self.evidence()
        self.ready()
        flow.write(self.run/'land_environment'/'soil-evidence.json', {'fixture': 'changed'})
        with self.assertRaisesRegex(ValueError, 'Reviewed files changed'):
            flow.assemble(self.run)

    def test_blocking_review_prevents_assembly(self):
        self.ready()
        file = self.run/'review'/'review.json'
        review = flow.read(file)
        review['issues'] = [{'agent': 'planning', 'indicator': 'zoning', 'severity': 'blocking', 'evidence': 'Synthetic conflict', 'requested_correction': 'Resolve synthetic conflict'}]
        flow.write(file, review)
        with self.assertRaisesRegex(ValueError, 'requires revisions'):
            flow.assemble(self.run)

    def test_land_soil_mode_requires_only_one_specialist(self):
        self.run = self.root/'limited'
        self.manifest = flow.initialize(self.parcel, 'Synthetic test site', 'synthetic fixture', 'Synthetic fixture only', self.run, mode='land-soil', offline=True)
        self.populate()
        self.assertEqual(flow.validate(self.run)['roles'], ['land_environment'])

    def test_overwrite_existing_run_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new run'):
            flow.initialize(self.parcel, 'site', 'fixture', 'fixture', self.run)

if __name__ == '__main__':
    unittest.main(verbosity=2)
