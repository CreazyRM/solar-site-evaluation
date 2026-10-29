"""Replay saved site evidence through the reusable pipeline without networking."""
import argparse
import json
from pathlib import Path
import assess
from pipeline import run_job

def build_replay(site,out,with_pdf=False):
    site=Path(site).resolve();out=Path(out).resolve()
    def evidence(*names):
        for name in names:
            direct=site/'evidence'/name
            if direct.exists():return direct
            matches=sorted((site/'evidence').glob('previous-*/'+name))
            if matches:return matches[-1]
        raise ValueError('Required saved evidence missing: '+', '.join(names))
    def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    assessment=load(site/'assessment.json')
    parcel=load(site/'parcel.geojson')
    export=evidence('aerial-export.json')
    extent=load(export)['data']['extent']
    base=site/'aerial-base.png'
    tasks=[{'id':'validate','operation':'validate','args':{'assessment':str(site/'assessment.json')}},
        {'id':'soil','operation':'soil_summary','args':{'features':str(evidence('soil-current.json','soil.geojson.json'))}},
        {'id':'terrain','operation':'terrain','args':{'terrain':str(site/'terrain-2m.tif'),'boundary':str(evidence('parcel-utm.json')),
            'vertical_unit':'metres','source_metadata':str(evidence('terrain-export.json'))}},
        {'id':'base_map','operation':'map','args':{'base_file':str(base),'extent':extent,'parcel':parcel,'filename':'base-map.png'}},
        {'id':'soil_map','operation':'map','args':{'base_file':str(base),'extent':extent,'parcel':parcel,'filename':'soil-map.png','soil_file':str(site/'soil-map.png'),'opacity':.5}},
        {'id':'wetland_map','operation':'map','args':{'base_file':str(base),'extent':extent,'parcel':parcel,'filename':'wetlands-map.png',
            'layers':[{'features':str(evidence('wetlands-current.json','wetlands.geojson.json')),'color':[50,145,200,110]}]}},
        {'id':'report','operation':'report','depends_on':['validate'],'args':{'assessment':str(site/'assessment.json')}}]
    address=assessment.get('input',{}).get('address','Solar Site')
    note='Saved public data reused. Imagery: 2015. Source: Grey County; soil/wetlands: Ontario. Red outline: public assessment parcel. No regulatory buffers or legal access inferred.'
    cards=[{'title':'Base imagery','file':{'task':'base_map','select':['file']},'note':note},
        {'title':'Soil capability','file':{'task':'soil_map','select':['file']},'note':note+' Soil overlay: 50% opacity; mixed proportions do not locate components.'},
        {'title':'Wetlands','file':{'task':'wetland_map','select':['file']},'note':note+' Blue: mapped wetlands.'},
        {'title':'Slope percent','file':{'task':'terrain','select':['artifacts','map']},'note':'Ontario lidar-derived DTM; 2 m projected grid. Red: >15% grade. See source timestamps; acquisition date unconfirmed.'}]
    clipping=site/'evidence'/'zoning-clipped.json'
    if clipping.exists() and (site/'evidence'/'zoning-clipped-areas.json').exists():
        geometries=load(clipping)['data']['geometries'];attrs=load(site/'evidence'/'zoning-clipped-areas.json')['zone_attributes']
        layers=[{'features':{'features':[{'geometry':g,'attributes':a}]},'color':color} for g,a,color in zip(geometries,attrs,([198,68,68,110],[233,193,65,110],[80,129,178,110],[150,100,190,110],[70,160,130,110])*10)]
        tasks.append({'id':'zoning_map','operation':'map','args':{'base_file':str(base),'extent':extent,'parcel':parcel,'filename':'zoning-map.png','layers':layers}})
        cards.append({'title':'Clipped zoning intersections','file':{'task':'zoning_map','select':['file']},'note':note+' Colours distinguish returned polygons; refer to assessment zoning codes and saved by-law provisions.'})
    tasks.append({'id':'gallery','operation':'gallery','args':{'cards':cards,'title':address+' - Evidence Maps'}})
    if with_pdf:tasks.append({'id':'pdf','operation':'pdf','args':{'report_file':{'task':'report','select':['report']},'assessment_file':{'task':'report','select':['assessment']},'cards':cards}})
    config={'workers':4,'tasks':tasks,'replay_source':str(site),'note':'Offline replay; source dates preserved, no fresh source acquisition.'}
    out.mkdir(parents=True,exist_ok=True);assess.save_json(out/'replay-job.json',config)
    return config

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--pdf',action='store_true');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    config=build_replay(args.site_dir,args.out,args.pdf)
    print(json.dumps(run_job(config,args.out,offline=True,resume=args.resume)))

if __name__=='__main__':main()
