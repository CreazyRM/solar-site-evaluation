"""Public ArcGIS collection and GeometryServer calculations, independent of UI."""
import json
import math
import assess

def unwrap(data):
    return data.get('data',data) if isinstance(data,dict) else data

def geometry(data):
    data=unwrap(data)
    if data.get('type')=='FeatureCollection':
        if len(data['features'])!=1:raise ValueError('Exactly one confirmed parcel is required.')
        data=data['features'][0]
    if data.get('type')=='Feature':data=data['geometry']
    if data.get('type') not in ('Polygon','MultiPolygon'):
        raise ValueError('Expected WGS84 GeoJSON parcel Polygon or MultiPolygon.')
    return data

def query(client,url,parcel=None,where='1=1',fields='*',ttl=0):
    records=[];features=[];seen=set()
    for offset in range(0,10000,1000):
        params={'f':'geojson','where':where,'outFields':fields,'returnGeometry':'true','outSR':4326,'resultOffset':offset,'resultRecordCount':1000}
        if parcel:
            kind,spatial=assess.arcgis_geometry(geometry(parcel))
            params.update(geometry=json.dumps(spatial),geometryType=kind,inSR=4326,spatialRel='esriSpatialRelIntersects')
        record,data=client.json(url.rstrip('/')+'/query',params,ttl=ttl)
        if not isinstance(data,dict) or not isinstance(data.get('features'),list):raise assess.Unavailable('unexpected_service_schema')
        records.append(record)
        for feature in data['features']:
            fingerprint=json.dumps(feature,sort_keys=True)
            if fingerprint in seen:raise assess.Unavailable('duplicate_page_or_feature')
            seen.add(fingerprint);features.append(feature)
        if not data.get('exceededTransferLimit') and len(data['features'])<1000:
            return {'type':'FeatureCollection','features':features,'query_provenance':records}
        if not data['features']:raise assess.Unavailable('incomplete_pagination')
    raise assess.Unavailable('query_limit_exceeded')

def parcel_lookup(client,url,arn=None,address=None,arn_field='ARN',address_field='address3',ttl=0):
    import re
    if not all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',f) for f in (arn_field,address_field)):
        raise ValueError('Invalid field identifier.')
    if not arn and not address:raise ValueError('Provide an exact ARN or civic address.')
    conditions=[]
    if arn:conditions.append(arn_field+" = '"+str(arn).replace("'","''")+"'")
    if address:conditions.append(address_field+" = '"+address.replace("'","''")+"'")
    result=query(client,url,where=' AND '.join(conditions),ttl=ttl)
    result['match_status']='needs_review' if len(result['features'])!=1 else 'candidate_requires_visual_confirmation'
    return result

def geometry_call(client,server,operation,params):
    record,data=client.json(server.rstrip('/')+'/'+operation,{'f':'json',**params},method='POST')
    return {'source':record['source'],'request':record['request'],'retrieved_at':record['retrieved_at'],'data':data}

def area(client,server,parcel):
    _,spatial=assess.arcgis_geometry(geometry(parcel))
    result=geometry_call(client,server,'areasAndLengths',{'sr':4326,'polygons':json.dumps([spatial]),'areaUnit':json.dumps({'areaUnit':'esriSquareMeters'}),'lengthUnit':9001,'calculationType':'geodesic'})
    values=result['data'].get('areas',[])
    if len(values)!=1 or not math.isfinite(values[0]):raise assess.Unavailable('invalid_area_response')
    result['summary']={'square_metres':abs(values[0]),'acres':abs(values[0])/assess.ACRE_M2,'method':'GeometryServer geodesic area','net_developable_area':None}
    return result

def project(client,server,parcel,epsg):
    _,spatial=assess.arcgis_geometry(geometry(parcel))
    return geometry_call(client,server,'project',{'inSR':4326,'outSR':int(epsg),'geometries':json.dumps({'geometryType':'esriGeometryPolygon','geometries':[spatial]})})

def clip_areas(client,server,parcel,features):
    features=unwrap(features)['features']
    if not features:return {'intersections':[],'total_square_metres':0,'note':'No features returned; completeness still needs review.'}
    polygons=[];attributes=[]
    for feature in features:
        g=feature['geometry']
        if 'rings' in g:polygons.append(g)
        else:polygons.append(assess.arcgis_geometry(g)[1])
        attributes.append(feature.get('properties',feature.get('attributes',{})))
    spatial=assess.arcgis_geometry(geometry(parcel))[1]
    clipped=geometry_call(client,server,'intersect',{'sr':4326,'geometries':json.dumps({'geometryType':'esriGeometryPolygon','geometries':polygons}),'geometry':json.dumps({'geometryType':'esriGeometryPolygon','geometry':spatial})})
    geometries=clipped['data'].get('geometries',[])
    if len(geometries)!=len(features):raise assess.Unavailable('intersection_count_mismatch')
    measured=geometry_call(client,server,'areasAndLengths',{'sr':4326,'polygons':json.dumps(geometries),'areaUnit':json.dumps({'areaUnit':'esriSquareMeters'}),'lengthUnit':9001,'calculationType':'geodesic'})
    values=measured['data'].get('areas',[])
    if len(values)!=len(features) or not all(math.isfinite(a) for a in values):raise assess.Unavailable('area_count_mismatch')
    return {'intersections':[{'attributes':a,'geometry':g,'square_metres':abs(v),'acres':abs(v)/assess.ACRE_M2,'boundary_touch_only':v==0} for a,g,v in zip(attributes,geometries,values)],
            'total_square_metres':sum(abs(v) for v in values),'evidence':{'clipping':clipped,'area':measured},
            'note':'Overlapping layers can double-count area. Mixed soil proportions are not component locations. This is not net buildable acreage.'}

def export_image(client,url,params,destination):
    record,data=client.json(url,params)
    if not data.get('href') or not data.get('extent'):raise assess.Unavailable('missing_export_image_or_extent')
    provenance,path=client.download(data['href'],destination)
    return {'source':url,'request':params,'retrieved_at':record['retrieved_at'],'data':data,'image_file':path,'download':provenance}

def osm_query(client,endpoint,bbox):
    xmin,ymin,xmax,ymax=bbox
    if not(-180<=xmin<xmax<=180 and -90<=ymin<ymax<=90) or xmax-xmin>.1 or ymax-ymin>.1:
        raise ValueError('OSM query requires a bounded site context, at most 0.1 degree per dimension.')
    box=f'{ymin},{xmin},{ymax},{xmax}'
    text=f'[out:json][timeout:12];(way["power"~"^(line|minor_line)$"]({box});way["man_made"="pipeline"]({box});way["railway"]({box}););out tags geom;'
    record,data=client.json(endpoint,{'data':text},method='POST')
    return {'source':record['source'],'retrieved_at':record['retrieved_at'],'data':data,'scope':'Context only; missing OSM features do not prove absence.'}
