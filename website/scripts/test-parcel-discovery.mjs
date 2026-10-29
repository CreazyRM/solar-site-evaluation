// Offline fixtures exercise discovery decisions without querying public services.
import assert from 'node:assert/strict';
import {locateOntario,addressMatches,safePublicURL} from '../lib/parcel-discovery.mjs';
assert(addressMatches('019471 Highway 6 Georgian Bluffs Ontario','019471 Highway 6'));
assert(!addressMatches('1 Carden Street Guelph Ontario','Township Road 1 Township of Guelph/Eramosa'));
for(const url of ['http://127.0.0.1/data','https://[::1]/data','https://localhost/data','https://host.internal/data','https://user:password@barrie.ca/data','https://barrie.ca/data?token=private'])assert.throws(()=>safePublicURL(url));
const nativeFetch=globalThis.fetch,layer='https://gispublic.barrie.ca/arcgis/rest/services/Public/TaxParcels/MapServer/2';
let mode='success',searches=0,forbiddenQueries=0,queryCalls=0;
const geometry={type:'Polygon',coordinates:[[[-79.690,44.387],[-79.684,44.387],[-79.684,44.393],[-79.690,44.393],[-79.690,44.387]]]};
const json=data=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}});
globalThis.fetch=async(raw,options={})=>{const url=new URL(raw),params=options.method==='POST'?new URLSearchParams(options.body):url.searchParams;
 if(url.hostname==='geolocator.api.geo.ca')return json([{name:'70 Collier Street City of Barrie Ontario',province:mode==='quebec'?'Quebec':'Ontario',category:'Street',lng:-79.687,lat:44.390,tag:['INTERPOLATED_POSITION']}]);
 if(url.pathname.endsWith('LIO_Open03/MapServer/14/query'))return json({features:[{attributes:{MUNICIPAL_NAME_SHORTFORM:'BARRIE',MUNID:'fixture-'+mode}}]});
 if(url.hostname==='www.barrie.ca')return new Response('<html><body>Official municipal fixture</body></html>');
 if(url.pathname.endsWith('/sharing/rest/search')){searches++;return json({results:[{id:'fixture',title:'Tax Parcels',type:'Map Service',extent:[[-79.8,44.2],[-79.5,44.5]],url:mode==='untrusted'?'https://services3.arcgis.com/UnknownOrg/arcgis/rest/services/Parcels/FeatureServer':layer}]});}
 if(url.pathname.includes('/sharing/rest/portals/'))return json({name:'Unverified publisher',portalProperties:{}});
 if(url.href.startsWith('https://services3.arcgis.com/UnknownOrg')){forbiddenQueries++;throw Error('An unverified service must never be queried.');}
 if(url.href.startsWith(layer)&&!url.pathname.endsWith('/query'))return mode==='auth'?json({error:{code:499}}):json({name:'Parcel',geometryType:mode==='point'?'esriGeometryPoint':'esriGeometryPolygon',capabilities:'Map,Query,Data',fields:[{name:'ADDRESS',type:'esriFieldTypeString'}]});
 if(url.href.startsWith(layer)&&url.pathname.endsWith('/query')){queryCalls++;return json({features:[{type:'Feature',properties:{ADDRESS:'70 Collier Street'},geometry}]});}
 if(url.pathname.endsWith('/rest/services'))return json({services:[],folders:[]});
 return json({error:{code:404}});
};
try{
 const first=await locateOntario('70 Collier Street Barrie Ontario');assert.equal(first.discovery_status,'parcel_candidates');assert.equal(first.candidates[0].source,layer);assert.equal(first.candidates[0].requires_confirmation,true);assert.equal(first.candidates[0].address_match,'civic_and_road_tokens');assert.equal(first.cache.hit,false);
 const before=searches,second=await locateOntario('70 Collier Street Barrie Ontario');assert.equal(second.cache.hit,true);assert.equal(searches,before);assert(queryCalls>=2,'Cached sources must still query current parcel geometry.');
 mode='auth';const auth=await locateOntario('70 Collier Street Barrie Ontario');assert.equal(auth.discovery_status,'parcel_unresolved');assert(auth.evidence.some(e=>e.status==='authentication_required'));assert.equal(auth.ai_fallback.status,'not_configured');
 mode='untrusted';const untrusted=await locateOntario('70 Collier Street Barrie Ontario');assert.equal(untrusted.discovery_status,'parcel_unresolved');assert.equal(forbiddenQueries,0);
 mode='point';const point=await locateOntario('70 Collier Street Barrie Ontario');assert(!point.candidates.some(c=>c.kind==='assessment_parcel'));
 mode='quebec';const quebec=await locateOntario('70 Collier Street Barrie Ontario');assert(!quebec.candidates.some(c=>c.kind==='assessment_parcel'));
 await assert.rejects(locateOntario('70 Collier Street Barrie Ontario',{selectedIndex:99}),/Invalid/);
 console.log('Discovery fixtures passed: official publisher, current polygon query, source-cache revalidation, login skip, untrusted publisher rejection, point rejection, Ontario filtering and numbered-road matching.');
}finally{globalThis.fetch=nativeFetch;}
