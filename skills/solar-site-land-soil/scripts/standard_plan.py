"""Generate standard jobs and populate deterministic metrics from confirmed inputs.

No source discovery or AI judgement is implied. The caller confirms the parcel and
applicable public services once; failed tasks become explicit skipped metrics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import assess
from pipeline import run_job, read
from gis_tasks import geometry

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare(profile):
    required=('address','jurisdiction','boundary_file','boundary_source','boundary_sha256','confirmation_note')
    if not all(profile.get(k) for k in required):raise ValueError('Confirmed address, jurisdiction, boundary provenance and fingerprint are required.')
    boundary=Path(profile['boundary_file']).resolve()
    if sha(boundary)!=profile['boundary_sha256']:raise ValueError('Confirmed boundary fingerprint changed.')
    assess.load_geometry(boundary)
    selected=profile.get('indicators',['area','soil','wetlands','zoning','slope_full_area'])
    if set(selected)-{'area','soil','wetlands','zoning','slope_full_area'}:raise ValueError('Unsupported deterministic indicator.')
    sources=profile.get('sources',{});saved=profile.get('saved',{})
    tasks=[];bindings={};unavailable={}
    def add(taskid,operation,args,indicator=None):
        tasks.append({'id':taskid,'operation':operation,'args':args})
        if indicator:bindings[indicator]=taskid
    for key in selected:
        if key in saved and key!='slope_full_area':
            # Saved records must retain source and retrieval time, not new timestamps.
            add(key,'saved_input',{'file':saved[key]},key)
        elif key=='area' and sources.get('geometry_server'):
            add(key,'geodesic_area',{'server':sources['geometry_server'],'parcel':str(boundary)},key)
        elif key in ('soil','wetlands','zoning') and sources.get(key):
            add(key,'query',{'url':sources[key],'parcel':str(boundary)},key)
        elif key=='slope_full_area' and profile.get('terrain'):
            add('slope','terrain',dict(profile['terrain']),key)
        else:unavailable[key]='No configured public source or saved evidence; agent source discovery required.'
    return {'workers':4,'tasks':tasks},bindings,unavailable

def convert(indicator,result):
    """Produce metrics only from saved provenance and actual numeric outputs."""
    if indicator=='slope_full_area':
        manifest=read(result['artifacts']['statistics']);stats=manifest['statistics']
        if not manifest.get('source') or not manifest.get('source_retrieved_at'):
            raise ValueError('Terrain source and original retrieval time are required.')
        return {'status':'estimated' if stats['coverage_percent']==100 else 'needs_review','value':stats,
            'source':manifest.get('source'),'retrieved_at':manifest.get('source_retrieved_at'),
            'data_date':manifest.get('acquisition_date'),'scope':'Parcel raster cell centres; see valid-kernel coverage',
            'limitations':manifest['limitations'],'evidence_locator':result['artifacts']['statistics']}
    wrapper=result
    data=result.get('data',result)
    if indicator=='area':
        value=result.get('summary')
        if not value or not isinstance(value.get('square_metres'),(float,int)):raise ValueError('Measured area summary missing.')
        status='estimated' if value.get('approximate') else 'verified'
    else:
        features=data['features']
        if indicator=='soil':
            value=assess.soil_summary([{'properties':f.get('properties',f.get('attributes',{}))} for f in features])
            status='needs_review' if value['preliminary_finding']!='mapped_classes_in_default_range' else 'verified'
        elif indicator=='wetlands':
            value={'mapped_intersections':len(features),'absence_confirmed':False,'regulatory_buffers_assessed':False}
            status='needs_review'
        else:
            value={'intersections':[f.get('properties',f.get('attributes',{})) for f in features],
                   'permission_determined':False,'scope':'Intersecting zoning polygons; operative by-law interpretation required'}
            status='needs_review'
        if result.get('query_provenance'):
            wrapper=result['query_provenance'][0]
    source=wrapper.get('source');timestamp=wrapper.get('retrieved_at')
    if not source or not timestamp:raise ValueError('Source URL/file and original retrieval timestamp are required.')
    return {'status':status,'value':value,'source':source,'retrieved_at':timestamp,'data_date':wrapper.get('data_date'),
            'scope':'Confirmed parcel intersection' if indicator!='area' else 'Measured polygon, not ownership survey or developable area'}

def execute(profile,out,resume=False):
    profile=dict(profile)
    if profile.get('manifest_file'):
        manifest=read(profile['manifest_file'])
        if manifest['boundary_sha256']!=profile['boundary_sha256']:raise ValueError('Profile and run manifest refer to different boundaries.')
        if manifest.get('offline'):profile['offline']=True
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    # Planning validates the frozen input before any collection can start.
    config,bindings,unavailable=prepare(profile)
    assess.save_json(out/'generated-job.json',config)
    summary=run_job(config,out/'work',offline=bool(profile.get('offline',False)),resume=resume)
    if sha(profile['boundary_file'])!=profile['boundary_sha256']:raise ValueError('Boundary changed during execution.')
    metrics={k:assess.metric('skipped',reason=v) for k,v in unavailable.items()}
    exceptions=[]
    for indicator,taskid in bindings.items():
        state=summary['tasks'][taskid]
        if state['status']!='completed':metrics[indicator]=assess.metric('skipped',reason=state.get('reason','task_unavailable'))
        else:
            try:
                metric=convert(indicator,read(state['result_file']))
                metric.setdefault('evidence_locator',state['result_file'])
                metric['calculation_provenance']={'boundary_sha256':profile['boundary_sha256'],
                    'result_sha256':sha(state['result_file']),'worker_sha256':sha(Path(__file__)),
                    'profile_sha256':hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest(),
                    'offline':bool(profile.get('offline',False))}
                metrics[indicator]=metric
            except (ValueError,KeyError,TypeError,OSError) as exc:metrics[indicator]=assess.metric('skipped',reason=str(exc))
        if metrics[indicator]['status'] in ('needs_review','skipped'):exceptions.append({'indicator':indicator,'reason':metrics[indicator].get('reason','Interpretation or source review required.')})
    exceptions.extend({'indicator':k,'reason':v} for k,v in unavailable.items())
    draft={'schema_version':'2.0','generated_at':assess.utc_now(),'input':{'address':profile['address'],'jurisdiction':profile['jurisdiction']},
        'overall_project_decision':None,'metrics':metrics,'note':'Computed metric draft only. AI resolves exceptions; multi-agent ownership and independent review remain required.'}
    assess.save_json(out/'assessment-draft.json',draft)
    result={'status':'needs_review' if exceptions else 'completed','offline':bool(profile.get('offline',False)),
        'draft':str(out/'assessment-draft.json'),'exceptions':exceptions,'planned_tasks':len(config['tasks'])}
    assess.save_json(out/'automation-summary.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--resume',action='store_true');parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args();profile=read(args.profile)
    if args.plan_only:
        config,bindings,missing=prepare(profile);assess.save_json(Path(args.out)/'generated-job.json',config)
        result={'status':'planned','tasks':len(config['tasks']),'bindings':bindings,'missing':missing}
    else:result=execute(profile,args.out,args.resume)
    print(json.dumps(result))

if __name__=='__main__':main()
