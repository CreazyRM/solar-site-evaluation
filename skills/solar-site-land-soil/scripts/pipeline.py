"""Execute reusable solar jobs with dependencies, isolated failures and checkpoints.

Agent submits a JSON job and receives a compact summary. Detailed results remain
in files. No runtime-generated code or arbitrary shell commands are accepted.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import assess
from evidence_io import EvidenceClient
import gis_tasks

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def refs(value):
    if isinstance(value,dict):
        if 'task' in value:return {value['task']}
        return set().union(*(refs(v) for v in value.values())) if value else set()
    if isinstance(value,list):return set().union(*(refs(v) for v in value)) if value else set()
    return set()

def resolve(value,states):
    if isinstance(value,dict):
        if 'task' in value:
            result=read(states[value['task']]['result_file'])
            for key in value.get('select',[]):result=result[key]
            return result
        return {k:resolve(v,states) for k,v in value.items()}
    if isinstance(value,list):return [resolve(v,states) for v in value]
    return value

def json_input(value):return read(value) if isinstance(value,str) else value

def operation(name,args,context):
    client=context['client'];out=context['out']
    if name=='saved_input':
        return read(args['file'])
    if name=='json':
        record,_=client.json(**args);return record
    if name=='download':
        record,path=client.download(destination=out/args.pop('filename'),**args)
        return {'file':path,'provenance':record}
    if name=='parcel_lookup':return gis_tasks.parcel_lookup(client,**args)
    if name=='query':
        if 'parcel' in args:args['parcel']=json_input(args['parcel'])
        return gis_tasks.query(client,**args)
    if name in ('geodesic_area','project','clip_areas'):
        args['parcel']=json_input(args['parcel'])
        if 'features' in args:args['features']=json_input(args['features'])
        fn={'geodesic_area':gis_tasks.area,'project':gis_tasks.project,'clip_areas':gis_tasks.clip_areas}[name]
        return fn(client,**args)
    if name=='image_export':
        return gis_tasks.export_image(client,destination=out/args.pop('filename'),**args)
    if name=='terrain_export':
        import math
        projected=json_input(args['projected']);data=projected.get('data',projected)
        geometry=data['geometries'][0];points=[p for r in geometry['rings'] for p in r]
        resolution=args.get('resolution_m',2);padding=args.get('padding_m',10)
        if resolution<=0 or padding<resolution:raise ValueError('Terrain export needs positive resolution and at least a one-pixel halo.')
        xmin=math.floor(min(p[0] for p in points)/resolution)*resolution-padding
        xmax=math.ceil(max(p[0] for p in points)/resolution)*resolution+padding
        ymin=math.floor(min(p[1] for p in points)/resolution)*resolution-padding
        ymax=math.ceil(max(p[1] for p in points)/resolution)*resolution+padding
        width=math.ceil((xmax-xmin)/resolution);height=math.ceil((ymax-ymin)/resolution)
        if width*height>4_000_000:raise ValueError('Terrain export exceeds pixel budget; obtain tiled data rather than silently coarsening.')
        epsg=projected.get('request',{}).get('outSR') or geometry.get('spatialReference',{}).get('wkid')
        if not epsg:raise ValueError('Projected boundary CRS missing.')
        params={'f':'json','bbox':f'{xmin},{ymin},{xmin+width*resolution},{ymin+height*resolution}',
            'bboxSR':epsg,'imageSR':epsg,'size':f'{width},{height}','format':'tiff','pixelType':'F32',
            'interpolation':'RSP_NearestNeighbor','renderingRule':json.dumps({'rasterFunction':'None'}),'adjustAspectRatio':'false'}
        return gis_tasks.export_image(client,args['url'],params,out/args.get('filename','terrain.tif'))
    if name=='osm':return gis_tasks.osm_query(client,**args)
    if name=='soil_summary':
        data=gis_tasks.unwrap(json_input(args['features']))
        features=[{'properties':f.get('properties',f.get('attributes',{}))} for f in data['features']]
        return assess.soil_summary(features)
    if name=='pdf_text':
        from pypdf import PdfReader
        reader=PdfReader(args['file']);keywords=[s.lower() for s in args.get('keywords',[])]
        pages=[]
        for index,page in enumerate(reader.pages):
            text=page.extract_text() or ''
            if not keywords or any(word in text.lower() for word in keywords):pages.append({'page':index+1,'text':text})
        return {'source_file':str(Path(args['file']).resolve()),'pages':pages,'note':'Text extraction is retrieval support, not legal interpretation; scanned pages may need OCR.'}
    if name=='assessment_update':
        import copy
        report=copy.deepcopy(json_input(args['base']))
        report['metrics'].update(args.get('metrics',{}))
        report['artifact_generated_at']=assess.utc_now()
        report['reuse_note']='Saved source evidence reused; no data freshness claim.' if client.offline else 'See individual source timestamps.'
        return report
    if name=='route':
        from assess_full import route_summary
        return route_summary(json_input(args['route']))
    if name=='capacity':
        from assess_full import capacity_summary
        return capacity_summary(json_input(args['tests']))
    if name=='terrain':
        from terrain_slope import run_job
        args['out']=out/args.pop('subdirectory','terrain')
        return run_job(**args)
    if name=='map':
        from site_maps import draw_map
        args['parcel']=gis_tasks.geometry(json_input(args['parcel']))
        args['extent']=json_input(args['extent'])
        if 'layers' in args:
            for layer in args['layers']:layer['features']=gis_tasks.unwrap(json_input(layer['features']))['features']
        return {'file':draw_map(output=out/args.pop('filename'),**args)}
    if name=='gallery':
        from site_maps import gallery
        return {'file':gallery(args['cards'],out/args.get('filename','site-maps.html'),args['title'])}
    if name=='extend':
        from assess_full import extend
        return extend(json_input(args['base']),**args.get('additions',{}))
    if name=='report':
        from site_outputs import write_report
        return write_report(json_input(args['assessment']),out/args.get('subdirectory','report'))
    if name=='validate':
        from site_outputs import validate_report
        result=validate_report(json_input(args['assessment']))
        if not result['valid']:raise ValueError('; '.join(result['errors']))
        return result
    if name=='pdf':
        from site_outputs import export_pdfs
        return export_pdfs(args['report_file'],args['assessment_file'],args.get('cards',[]),out/args.get('subdirectory','pdf'))
    raise ValueError('Unknown registered operation: '+name)

NETWORK={'json','download','parcel_lookup','query','geodesic_area','project','clip_areas','image_export','terrain_export','osm'}

def fingerprint(value):
    """Include referenced input file contents so changed files invalidate resumes."""
    if isinstance(value,str):
        try:
            path=Path(value)
            if len(value)<500 and path.is_file():return {'path':value,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        except OSError:pass
    if isinstance(value,dict):return {k:fingerprint(v) for k,v in value.items()}
    if isinstance(value,list):return [fingerprint(v) for v in value]
    return value

def run_job(config,out,offline=False,resume=False):
    started=time.perf_counter();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    tasks=config['tasks'];ids=[t['id'] for t in tasks]
    import re
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r'[a-zA-Z0-9_-]+',i) for i in ids):raise ValueError('Unique safe task IDs required.')
    for task in tasks:
        dependencies=set(task.get('depends_on',[]))|refs(task.get('args',{}))
        if dependencies-set(ids) or task['id'] in dependencies:raise ValueError('Unknown or self-referencing dependency.')
    checkpoint=out/'checkpoint.json';previous=read(checkpoint) if resume and checkpoint.exists() else {}
    states={};remaining=list(tasks)
    client=EvidenceClient(config.get('cache_dir',out/'cache'),offline,config.get('timeout',15))
    context={'client':client,'out':out}
    code_hash=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')) if not p.name.startswith('self_test'))).hexdigest()
    def execute(task):
        taskid=task['id']
        try:
            args=resolve(task.get('args',{}),states)
            digest=hashlib.sha256(json.dumps([code_hash,task['operation'],fingerprint(args)],sort_keys=True).encode()).hexdigest()
            for key in ('filename','subdirectory'):
                if key in args and not (out/args[key]).resolve().is_relative_to(out):raise ValueError('Output paths must stay in the job directory.')
        except (ValueError,OSError,KeyError,TypeError) as exc:
            return {'status':'skipped','reason':'Invalid task input: '+str(exc)}
        old=previous.get(taskid,{})
        if resume and task['operation'] not in NETWORK and old.get('status')=='completed' and old.get('fingerprint')==digest and Path(old['result_file']).exists():
            artifacts=old.get('artifacts',[])
            if all(Path(p).exists() for p in artifacts):return {**old,'resumed':True}
        try:
            result=operation(task['operation'],dict(args),context)
            path=out/'results'/(taskid+'.json');assess.save_json(path,result)
            artifacts=[]
            def paths(value):
                if isinstance(value,str) and len(value)<500:
                    try:
                        if Path(value).is_file():artifacts.append(value)
                    except OSError:pass
                elif isinstance(value,dict):
                    for v in value.values():paths(v)
                elif isinstance(value,list):
                    for v in value:paths(v)
            paths(result)
            return {'status':'completed','result_file':str(path),'fingerprint':digest,'artifacts':artifacts,'resumed':False}
        except (assess.Unavailable,ValueError,OSError,KeyError,TypeError,ImportError) as exc:
            return {'status':'skipped','reason':getattr(exc,'reason',str(exc)),'fingerprint':digest}
    while remaining:
        ready=[t for t in remaining if (set(t.get('depends_on',[]))|refs(t.get('args',{})))<=set(states)]
        if not ready:raise ValueError('Cyclic task dependencies.')
        runnable=[]
        for task in ready:
            deps=set(task.get('depends_on',[]))|refs(task.get('args',{}))
            if any(states[d]['status']!='completed' for d in deps):states[task['id']]={'status':'skipped','reason':'dependency_unavailable'}
            else:runnable.append(task)
        with ThreadPoolExecutor(max_workers=min(4,max(1,int(config.get('workers',4))))) as pool:
            results=list(pool.map(execute,runnable))
        for task,result in zip(runnable,results):states[task['id']]=result
        remaining=[t for t in remaining if t not in ready]
        assess.save_json(checkpoint,states)
    summary={'status':'completed' if all(s['status']=='completed' for s in states.values()) else 'partial',
        'duration_seconds':round(time.perf_counter()-started,3),'offline':offline,
        'tasks':{k:{x:v[x] for x in ('status','reason','result_file','resumed') if x in v} for k,v in states.items()},'checkpoint':str(checkpoint)}
    assess.save_json(out/'task-summary.json',summary)
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--offline',action='store_true');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    try:result=run_job(read(args.config),args.out,args.offline,args.resume)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'needs_review','reason':str(exc)}));raise SystemExit(2)
    print(json.dumps(result,allow_nan=False))

if __name__=='__main__':main()
