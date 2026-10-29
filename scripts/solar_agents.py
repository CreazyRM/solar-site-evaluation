"""Prepare frozen solar runs, validate handoffs and assemble reviewed results.

Codex launches the LLM workers. This module handles deterministic contracts only.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import uuid

PROJECT = Path(__file__).resolve().parents[1]
ROLES = {
    'land_environment': ['soil', 'slope_full_area', 'wetlands', 'transmission', 'pipelines', 'railroads'],
    'grid_access': ['truck_access', 'line_phases', 'connection_route', 'distributor', 'connection_candidates', 'capacity_2mw', 'capacity_trials'],
    'planning': ['zoning', 'official_plan', 'solar_permitted_use', 'soil_exception'],
}

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(condition, message):
    if not condition:
        raise ValueError(message)

def schema_check(value, schema, root=None, path='$'):
    """Validate the subset used by the two local schemas without dependencies."""
    root = root or schema
    if '$ref' in schema:
        target = root
        for part in schema['$ref'].split('/')[1:]:
            target = target[part]
        return schema_check(value, target, root, path)
    types = {'object': dict, 'array': list, 'string': str, 'null': type(None)}
    if 'type' in schema:
        names = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        check(any(isinstance(value, types[name]) for name in names), path+': incorrect type')
    if 'const' in schema:
        check(value == schema['const'], path+': incorrect constant')
    if 'enum' in schema:
        check(value in schema['enum'], path+': invalid enum')
    if isinstance(value, str):
        check(len(value) >= schema.get('minLength', 0), path+': empty string')
        if 'pattern' in schema:
            check(re.search(schema['pattern'], value) is not None, path+': invalid pattern')
        if schema.get('format') == 'date-time':
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            check('T' in value and stamp.tzinfo is not None, path+': timestamp needs timezone')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            check(key in value, path+': missing '+key)
        properties = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for key, item in value.items():
            if key in properties:
                schema_check(item, properties[key], root, path+'.'+key)
            elif extra is False:
                raise ValueError(path+': unexpected '+key)
            elif isinstance(extra, dict):
                schema_check(item, extra, root, path+'.'+key)
    if isinstance(value, list):
        check(len(value) >= schema.get('minItems', 0), path+': too few items')
        for index, item in enumerate(value):
            schema_check(item, schema.get('items', {}), root, path+f'[{index}]')

def parcel_geometry(parcel):
    if parcel.get('type') == 'FeatureCollection':
        check(len(parcel['features']) == 1, 'Confirm exactly one assessment parcel before delegation.')
        parcel = parcel['features'][0]
    if parcel.get('type') == 'Feature':
        parcel = parcel['geometry']
    check(parcel.get('type') in ('Polygon', 'MultiPolygon'), 'A polygon parcel is required.')
    polygons = [parcel['coordinates']] if parcel['type'] == 'Polygon' else parcel['coordinates']
    check(bool(polygons) and all(polygons), 'Empty parcel geometry.')
    for polygon in polygons:
        for ring in polygon:
            check(len(ring) >= 4 and ring[0] == ring[-1], 'Parcel rings must be closed.')
            for point in ring:
                check(len(point) >= 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in point[:2]), 'Invalid parcel coordinate.')
                check(-180 <= point[0] <= 180 and -90 <= point[1] <= 90, 'Use WGS84 longitude/latitude GeoJSON.')
    return parcel

def initialize(parcel, address, boundary_source, confirmation_note, out, mode='full', offline=False):
    out = Path(out).resolve()
    check(not out.exists(), 'Choose a new run directory; existing runs are not overwritten.')
    raw = Path(parcel).read_bytes()
    parsed = json.loads(raw.decode('utf-8-sig'))
    parcel_geometry(parsed)
    check(not parsed.get('crs') or parsed['crs'].get('properties', {}).get('name') in ('EPSG:4326', 'urn:ogc:def:crs:OGC:1.3:CRS84', 'urn:ogc:def:crs:EPSG::4326'), 'Convert the declared CRS to WGS84 first.')
    check(all(isinstance(v, str) and v.strip() for v in (address, boundary_source, confirmation_note)), 'Address, boundary source and confirmation note are required.')
    roles = list(ROLES) if mode == 'full' else ['land_environment']
    boundary = out/'inputs'/'parcel.geojson'
    boundary.parent.mkdir(parents=True)
    boundary.write_bytes(raw)
    manifest = {'schema_version': '1.0', 'run_id': str(uuid.uuid4()), 'created_at': now(), 'address': address,
                'mode': mode, 'offline': offline, 'boundary_file': 'inputs/parcel.geojson',
                'boundary_sha256': digest(boundary), 'boundary_source': boundary_source,
                'confirmation_note': confirmation_note, 'horizontal_crs': 'EPSG:4326',
                'roles': roles, 'assignments': {role: ROLES[role] for role in roles}}
    write(out/'manifest.json', manifest)
    for role in roles:
        write(out/role/'assignment.json', {'run_id': manifest['run_id'], 'agent': role,
              'boundary_sha256': manifest['boundary_sha256'], 'indicators': ROLES[role],
              'result_file': role+'/result.json', 'offline': offline})
    (out/'review').mkdir()
    skipped = lambda reason: {'status': 'skipped', 'value': None, 'reason': reason}
    write(out/'coordinator'/'assessment.json', {'schema_version': '1.0', 'generated_at': now(),
          'input': {'address': address, 'boundary_file': str(boundary)}, 'overall_project_decision': None,
          'metrics': {'location': {'status': 'provided', 'value': {'address': address, 'confirmation_note': confirmation_note}, 'source': boundary_source, 'retrieved_at': now()},
                      'boundary': {'status': 'provided', 'value': {'geometry': parcel_geometry(parsed), 'sha256': manifest['boundary_sha256']}, 'source': boundary_source, 'retrieved_at': now()},
                      'pin': skipped('Coordinator must verify a public title identifier or retain this skip; GeoWarehouse is excluded.'),
                      'arn': skipped('Coordinator has not yet recorded a sourced ARN.'),
                      'acreage': skipped('Coordinator has not yet recorded a geodesic/equal-area measurement.')}})
    return manifest

def owned_file(run, relative, owner):
    candidate = Path(relative)
    check(not candidate.is_absolute(), 'Evidence paths must be relative to the run.')
    resolved = (run/candidate).resolve()
    owner_root = (run/owner).resolve()
    check(owner_root.is_relative_to(run) and resolved.is_relative_to(owner_root), 'Evidence must remain inside '+owner)
    check(resolved.is_file(), 'Evidence file missing: '+relative)
    return resolved

def validate(run):
    run = Path(run).resolve()
    manifest = read(run/'manifest.json')
    check(manifest['mode'] in ('full', 'land-soil'), 'Unknown assessment mode.')
    expected_roles = list(ROLES) if manifest['mode'] == 'full' else ['land_environment']
    check(manifest['roles'] == expected_roles, 'Manifest role set was changed.')
    check(manifest['assignments'] == {r: ROLES[r] for r in expected_roles}, 'Manifest indicator assignments were changed.')
    check(manifest['boundary_file'] == 'inputs/parcel.geojson', 'Invalid frozen boundary path.')
    check(digest(run/manifest['boundary_file']) == manifest['boundary_sha256'], 'Frozen parcel changed; start a new run.')
    result_schema = read(PROJECT/'schemas'/'agent-result.schema.json')
    reviewed = {'manifest.json': digest(run/'manifest.json'), manifest['boundary_file']: manifest['boundary_sha256']}
    results = {}
    for role in expected_roles:
        file = run/role/'result.json'
        check((run/role).resolve().is_relative_to(run) and file.resolve().is_relative_to((run/role).resolve()), 'Result escaped assigned directory.')
        result = read(file)
        schema_check(result, result_schema)
        check(result['agent'] == role and result['run_id'] == manifest['run_id'], 'Wrong role or run: '+role)
        check(result['boundary_sha256'] == manifest['boundary_sha256'], 'Wrong parcel fingerprint: '+role)
        indicators = [m['indicator'] for m in result['metrics']]
        check(len(set(indicators)) == len(indicators), 'Duplicate indicators: '+role)
        check(set(indicators) == set(ROLES[role]), 'Missing or unowned indicators: '+role)
        for metric in result['metrics']:
            if metric['status'] == 'skipped':
                check(metric['value'] is None and bool(metric['reason'] and metric['reason'].strip()), 'Skipped metric must have null value and reason.')
            else:
                check(metric['value'] is not None and bool(metric['sources']) and bool(metric['evidence_files']), 'Non-skipped metric needs value, sources and saved evidence.')
            for relative in metric['evidence_files']:
                evidence = owned_file(run, relative, role)
                reviewed[evidence.relative_to(run).as_posix()] = digest(evidence)
        reviewed[role+'/result.json'] = digest(file)
        results[role] = result
    base_file = run/'coordinator'/'assessment.json'
    base = read(base_file)
    check(base.get('overall_project_decision') is None, 'No overall project decision is allowed.')
    check(all(k in base.get('metrics', {}) for k in ('location', 'boundary', 'pin', 'arn', 'acreage')), 'Coordinator land/location indicators missing.')
    check(base['metrics']['boundary'].get('value', {}).get('sha256') == manifest['boundary_sha256'], 'Coordinator boundary fingerprint mismatch.')
    check(base.get('input', {}).get('address') == manifest['address'], 'Coordinator address differs from manifest.')
    check(base['metrics']['boundary']['value'].get('geometry') == parcel_geometry(read(run/manifest['boundary_file'])), 'Coordinator geometry differs from frozen parcel.')
    check(not (set(base['metrics']) & {m['indicator'] for r in results.values() for m in r['metrics']}), 'Coordinator/specialist metric collision.')
    sys.path.insert(0, str(PROJECT/'skills'/'solar-site-land-soil'/'scripts'))
    from site_outputs import validate_report
    checked = validate_report(base)
    check(checked['valid'], '; '.join(checked['errors']))
    check(not checked['warnings'], '; '.join(checked['warnings']))
    reviewed['coordinator/assessment.json'] = digest(base_file)
    return {'valid': True, 'run_id': manifest['run_id'], 'boundary_sha256': manifest['boundary_sha256'], 'reviewed_sha256': reviewed, 'roles': expected_roles}

def review_diff(run, baseline=None):
    """Prioritize changed evidence without granting or carrying forward approval."""
    run = Path(run).resolve()
    snapshot = validate(run)
    prior = read(baseline) if baseline else {}
    if prior:
        schema_check(prior, read(PROJECT/'schemas'/'agent-review.schema.json'))
        check(prior.get('run_id') == snapshot['run_id'] and prior.get('boundary_sha256') == snapshot['boundary_sha256'], 'Review baseline belongs to another run or boundary.')
    previous = prior.get('reviewed_sha256', {})
    current = snapshot['reviewed_sha256']
    changed = sorted(k for k,v in current.items() if previous.get(k) != v)
    removed = sorted(set(previous)-set(current))
    affected = {}
    for role in snapshot['roles']:
        result = read(run/role/'result.json')
        affected[role] = [m['indicator'] for m in result['metrics'] if
            role+'/result.json' in changed or any(p in changed or p in removed for p in m['evidence_files'])]
    context_changed = any(p in changed for p in ('manifest.json','coordinator/assessment.json'))
    reuse = bool(prior and prior['verdict'] == 'ready' and not any(i['severity']=='blocking' for i in prior['issues']) and not context_changed)
    if context_changed or not reuse:
        affected = {role: list(ROLES[role]) for role in snapshot['roles']}
    result = {'run_id':snapshot['run_id'], 'boundary_sha256':snapshot['boundary_sha256'],
        'reviewed_sha256':current, 'changed_files':changed, 'removed_files':removed,
        'unchanged_files':sorted(k for k in current if k not in changed), 'affected_indicators':affected,
        'baseline_sha256':digest(baseline) if baseline else None,
        'can_reuse_unchanged_prior_checks':reuse,
        'independent_review_required':True,
        'note':'Review focus only; reviewer must confirm complete current snapshot and cross-section impacts. This file is not review approval.'}
    write(run/'review'/'review-diff.json', result)
    return result

def assemble(run):
    run = Path(run).resolve()
    snapshot = validate(run)
    review = read(run/'review'/'review.json')
    schema_check(review, read(PROJECT/'schemas'/'agent-review.schema.json'))
    check(review['run_id'] == snapshot['run_id'] and review['boundary_sha256'] == snapshot['boundary_sha256'], 'Review belongs to another run or parcel.')
    check(review['reviewed_sha256'] == snapshot['reviewed_sha256'], 'Reviewed files changed or review snapshot is incomplete.')
    check(review['verdict'] == 'ready' and not any(i['severity'] == 'blocking' for i in review['issues']), 'Independent review requires revisions.')
    report = copy.deepcopy(read(run/'coordinator'/'assessment.json'))
    for role in snapshot['roles']:
        for metric in read(run/role/'result.json')['metrics']:
            metric = copy.deepcopy(metric)
            indicator = metric.pop('indicator')
            metric['scope'] = metric['spatial_scope']
            if metric['sources']:
                metric['source'] = metric['sources'][0]['source_url']
                metric['retrieved_at'] = metric['sources'][0]['retrieved_at']
                metric['data_date'] = metric['sources'][0]['data_date']
                metric['evidence_locator'] = metric['sources'][0]['evidence_locator']
            report['metrics'][indicator] = metric
    manifest = read(run/'manifest.json')
    report['generated_at'] = now()
    report['overall_project_decision'] = None
    report['scope'] = ['land_location_and_size', 'soil_and_slope'] + ([] if manifest['mode'] == 'land-soil' else ['interconnection_distance', 'interconnection_electrical_capacity', 'zoning_and_official_plan'])
    report['multi_agent_audit'] = {'run_id': snapshot['run_id'], 'offline': manifest['offline'], 'review': review,
                                 'note': 'Reviewed partial public screening; source dates are not refreshed by assembly.'}
    from site_outputs import validate_report, write_report
    checked = validate_report(report)
    check(checked['valid'], '; '.join(checked['errors']))
    return write_report(report, run/'final')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('init')
    for key in ('parcel', 'address', 'boundary-source', 'confirmation-note', 'out'):
        start.add_argument('--'+key, required=True)
    start.add_argument('--mode', choices=['full', 'land-soil'], default='full')
    start.add_argument('--offline', action='store_true')
    for name in ('validate', 'assemble'):
        commands.add_parser(name).add_argument('--run', required=True)
    delta = commands.add_parser('review-diff')
    delta.add_argument('--run', required=True)
    delta.add_argument('--baseline')
    args = vars(parser.parse_args())
    command = args.pop('command')
    try:
        result = initialize(**args) if command == 'init' else review_diff(**args) if command == 'review-diff' else {'validate': validate, 'assemble': assemble}[command](args['run'])
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(1, 'Solar workflow error: '+str(error)+'\n')

if __name__ == '__main__':
    main()
