"""Offline checks of cache, pagination, dependencies, maps and evidence retention."""
import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import assess
from evidence_io import EvidenceClient
import gis_tasks
from pipeline import run_job
from site_maps import draw_map
from site_outputs import write_report

class Response:
    headers={'Content-Type':'application/json'}
    def __init__(self,value):self.raw=json.dumps(value).encode()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def geturl(self):return 'https://example.org/public'
    def read(self,*args):return self.raw

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_cache_reuses_original_timestamp_and_offline_no_network(self):
        client=EvidenceClient(self.root/'cache')
        with patch('evidence_io.urlopen',return_value=Response({'value':2})) as network:
            first,_=client.json('https://example.org/public',{'q':'a'})
            cached,data=client.json('https://example.org/public',{'q':'a'},ttl=60)
            self.assertEqual(network.call_count,1)
            self.assertTrue(cached['cache_hit'])
            self.assertEqual(first['retrieved_at'],cached['retrieved_at'])
            offline=EvidenceClient(self.root/'cache',offline=True)
            reused,_=offline.json('https://example.org/public',{'q':'a'})
            self.assertTrue(reused['reused_offline'])
            with self.assertRaises(assess.Unavailable):offline.json('https://example.org/missing')
            self.assertEqual(network.call_count,1)

    def test_zero_ttl_refresh_and_excluded_source(self):
        client=EvidenceClient(self.root/'cache')
        with patch('evidence_io.urlopen',return_value=Response({'value':2})) as network:
            client.json('https://example.org/public');client.json('https://example.org/public')
            self.assertEqual(network.call_count,2)
            with self.assertRaises(assess.Unavailable):client.json('https://collaboration.geowarehouse.ca/')
            self.assertEqual(network.call_count,2)

    def test_pagination_repeated_page_is_not_silent_success(self):
        class Client:
            def json(self,*args,**kwargs):return {},{'features':[{'properties':{'OBJECTID':1}}],'exceededTransferLimit':True}
        with self.assertRaises(assess.Unavailable):gis_tasks.query(Client(),'https://example.org/layer')

    def test_clip_retains_zero_area_touch(self):
        class Client:
            def json(self,url,params,**kwargs):
                data={'geometries':[{'rings':[]},{'rings':[]}]} if url.endswith('/intersect') else {'areas':[100,0]}
                return {'source':url,'request':params,'retrieved_at':'synthetic'},data
        parcel={'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,0]]]}
        features={'features':[{'geometry':{'rings':[]},'attributes':{'zone':'A'}},{'geometry':{'rings':[]},'attributes':{'zone':'B'}}]}
        result=gis_tasks.clip_areas(Client(),'https://example.org/geometry',parcel,features)
        self.assertEqual(result['total_square_metres'],100)
        self.assertTrue(result['intersections'][1]['boundary_touch_only'])
        self.assertEqual(result['intersections'][1]['attributes']['zone'],'B')

    def test_failure_isolated_and_dependent_skipped(self):
        base={'overall_project_decision':None,'metrics':{'pin':{'status':'skipped','value':None,'reason':'no_public_identifier'}}}
        tasks=[{'id':'broken','operation':'unsupported','args':{}},
            {'id':'dependent','operation':'validate','depends_on':['broken'],'args':{'assessment':base}},
            {'id':'independent','operation':'validate','args':{'assessment':base}}]
        result=run_job({'tasks':tasks},self.root/'out',offline=True)
        self.assertEqual(result['tasks']['independent']['status'],'completed')
        self.assertEqual(result['tasks']['dependent']['reason'],'dependency_unavailable')

    def test_resume_invalidates_changed_file(self):
        source=self.root/'soil.json'
        source.write_text(json.dumps({'features':[{'properties':{'CLI1':'4','PERCENT1':100}}]}))
        config={'tasks':[{'id':'soil','operation':'soil_summary','args':{'features':str(source)}}]}
        run_job(config,self.root/'out',offline=True)
        reused=run_job(config,self.root/'out',offline=True,resume=True)
        self.assertTrue(reused['tasks']['soil']['resumed'])
        source.write_text(json.dumps({'features':[{'properties':{'CLI1':'5','PERCENT1':100}}]}))
        changed=run_job(config,self.root/'out',offline=True,resume=True)
        self.assertFalse(changed['tasks']['soil']['resumed'])

    def test_hole_is_not_painted_as_layer(self):
        base=self.root/'base.png';Image.new('RGB',(100,100),'white').save(base)
        polygon=lambda rings:{'type':'Polygon','coordinates':rings}
        ring=lambda a,b:[[a,a],[b,a],[b,b],[a,b],[a,a]]
        draw_map(base,{'xmin':0,'ymin':0,'xmax':10,'ymax':10},polygon([ring(0,10)]),self.root/'map.png',
                 layers=[{'features':[{'geometry':polygon([ring(2,8),ring(4,6)])}],'color':[0,0,255,255]}])
        with Image.open(self.root/'map.png') as image:
            self.assertEqual(image.getpixel((50,50)),(255,255,255))
            self.assertEqual(image.getpixel((30,50)),(0,0,255))

    def test_report_preserves_values_and_dates(self):
        base={'generated_at':'2026-10-02T00:00:00Z','overall_project_decision':None,'metrics':{'area':{'status':'verified','value':64.9,'source':'synthetic','retrieved_at':'2026-10-02T00:00:00Z'}}}
        result=write_report(base,self.root/'out')
        self.assertEqual(json.loads(Path(result['assessment']).read_text()),base)

if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--work-dir')
    args,remaining=parser.parse_known_args()
    if args.work_dir:
        Path(args.work_dir).mkdir(parents=True,exist_ok=True);tempfile.tempdir=args.work_dir
    unittest.main(argv=['self_test_pipeline.py',*remaining],verbosity=2)
