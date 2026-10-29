"""Offline profile, automatic metric and failure-isolation checks."""
import tempfile
import unittest
from pathlib import Path
import assess
from standard_plan import prepare, execute, sha

class StandardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.boundary=self.root/'parcel.json'
        assess.save_json(self.boundary,{'type':'Polygon','coordinates':[[[-81,44],[-80.99,44],[-80.99,44.01],[-81,44]]]})
        self.profile={'address':'Synthetic fixture','jurisdiction':'Synthetic','boundary_file':str(self.boundary),
            'boundary_source':'synthetic','boundary_sha256':sha(self.boundary),'confirmation_note':'Synthetic test only',
            'offline':True,'indicators':['soil','wetlands','zoning']}
    def tearDown(self):self.temp.cleanup()
    def test_changed_boundary_rejected_before_tasks(self):
        self.boundary.write_text('{}')
        with self.assertRaisesRegex(ValueError,'fingerprint'):prepare(self.profile)
    def test_saved_soil_automatically_fills_and_preserves_date(self):
        soil=self.root/'soil.json'
        assess.save_json(soil,{'source':'synthetic','retrieved_at':'2026-10-02T00:00:00Z',
            'data':{'features':[{'properties':{'CLI1':'4','PERCENT1':100}}]}})
        self.profile['saved']={'soil':str(soil)}
        result=execute(self.profile,self.root/'out')
        import json
        metrics=json.loads(Path(result['draft']).read_text())['metrics']
        self.assertEqual(metrics['soil']['value']['classes'],['4'])
        self.assertEqual(metrics['soil']['retrieved_at'],'2026-10-02T00:00:00Z')
        self.assertEqual(metrics['zoning']['status'],'skipped')
    def test_offline_source_miss_is_skipped_not_live_query(self):
        from unittest.mock import patch
        self.profile['sources']={'soil':'https://example.org/layer'}
        with patch('evidence_io.urlopen') as network:
            result=execute(self.profile,self.root/'out');network.assert_not_called()
        self.assertTrue(any(e['indicator']=='soil' for e in result['exceptions']))
    def test_missing_provenance_is_exception(self):
        soil=self.root/'soil.json';assess.save_json(soil,{'features':[]})
        self.profile['saved']={'soil':str(soil)}
        result=execute(self.profile,self.root/'out')
        self.assertTrue(any('timestamp' in e['reason'] for e in result['exceptions']))

    def test_manifest_offline_cannot_be_disabled_by_profile(self):
        from unittest.mock import patch
        manifest=self.root/'manifest.json'
        assess.save_json(manifest,{'boundary_sha256':self.profile['boundary_sha256'],'offline':True})
        self.profile.update(manifest_file=str(manifest),offline=False,sources={'soil':'https://example.org/layer'})
        with patch('evidence_io.urlopen') as network:
            result=execute(self.profile,self.root/'out');network.assert_not_called()
        self.assertTrue(result['offline'])

if __name__=='__main__':unittest.main(verbosity=2)
