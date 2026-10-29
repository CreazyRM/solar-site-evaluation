/* Public-source screening. No AI permission or connection approval is inferred. */
export const SOIL='https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer/29';
export const WETLAND='https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer/15';
const MUNICIPAL='https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open03/MapServer/14';
import {validatePolygon,areaM2,contained,clipToParcel,arcgisRings} from '../public/solar/geometry.mjs';
export {validatePolygon,areaM2,contained} from '../public/solar/geometry.mjs';
import {publicJSON} from './public-data.mjs';
export {publicJSON} from './public-data.mjs';
export {locateOntario as locate} from './parcel-discovery.mjs';
export async function spatial(url,geometry){
 const rings=arcgisRings(geometry);let features=[],provenance=[];
 for(let offset=0;offset<5000;offset+=1000){
  const response=await publicJSON(url+'/query',{f:'geojson',where:'1=1',outFields:'*',returnGeometry:'false',geometry:JSON.stringify({rings,spatialReference:{wkid:4326}}),geometryType:'esriGeometryPolygon',inSR:4326,spatialRel:'esriSpatialRelIntersects',resultOffset:offset,resultRecordCount:1000},true);
  if(!Array.isArray(response.data.features))throw Error('unexpected_source_schema');features.push(...response.data.features);provenance.push({source:response.source,retrieved_at:response.retrieved_at});
  if(!response.data.exceededTransferLimit&&response.data.features.length<1000)return{features,source:url,retrieved_at:response.retrieved_at,provenance};
  if(!response.data.features.length)throw Error('incomplete_pagination');
 }throw Error('query_limit_exceeded');
}
export async function evaluate(input,emit=()=>{}){
 const geometry=clipToParcel(input.geometry,input.parcel?.geometry);if(typeof input.address!=='string'||!input.address.trim()||input.address.length>240)throw Error('Address required.');
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(geometry)));
 const fingerprint=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
 const metrics={area:{status:'estimated',value:{square_metres:areaM2(geometry),acres:areaM2(geometry)/4046.8564224,method:'Authalic-sphere polygon area; user-selected study boundary'},source:'User-confirmed map geometry',retrieved_at:new Date().toISOString()},pin:{status:'skipped',value:null,reason:'GeoWarehouse excluded; independent title verification not collected.'}};
 emit({stage:'boundary',message:'Study boundary validated and fingerprinted.'});
 await Promise.all([['soil',SOIL],['wetlands',WETLAND],['municipality',MUNICIPAL]].map(async([key,url])=>{
  try{const result=await spatial(url,geometry);let value,status='needs_review';
   if(key==='soil'){const classes=new Set();const units=result.features.map(f=>{const p=f.properties||f.attributes||{};const components=[];for(let i=1;i<=3;i++)if(p['CLI'+i]!=null&&String(p['CLI'+i]).trim()){classes.add(String(p['CLI'+i]).trim());components.push({class:String(p['CLI'+i]),percent:p['PERCENT'+i],soil_name:p['SOIL_NAME'+i]});}return{objectid:p.OBJECTID,components};});value={classes:[...classes].sort(),mapping_units:units,exception_review_required:[...classes].some(c=>['1','2','3'].includes(c)),class_area_percentages:null};status=classes.size&&[...classes].every(c=>['4','5','6','7'].includes(c))?'verified':'needs_review';}
   else if(key==='wetlands')value={mapped_intersections:result.features.length,absence_confirmed:false,regulatory_buffers_assessed:false};
   else value={intersections:result.features.map(f=>f.properties||f.attributes),scope:'Study-area spatial intersection; review jurisdiction attributes'};
   metrics[key]={status,value,source:result.source,retrieved_at:result.retrieved_at,data_date:null};
  }catch(error){metrics[key]={status:'skipped',value:null,source:url,reason:String(error.message)};}
  emit({stage:key,message:key+' query '+(metrics[key].status==='skipped'?'unavailable; reason retained.':'completed.')});
 }));
 for(const [key,reason] of Object.entries({slope_full_area:'Bare-earth raster processing service is not connected to this Site.',truck_access:'Current imagery and legal/truck access require agent review.',line_phases:'Street-level imagery and utility confirmation require agent review.',connection_route:'Confirmed entrance and electrical connection point are required.',capacity_2mw:'Hydro One calculator/browser agent is not connected; no actual trial was run.',zoning:'Local source discovery and operative by-law review require the agent service.',official_plan:'Operative planning documents and amendments require the agent service.'}))metrics[key]={status:'skipped',value:null,reason};
 return{schema_version:'3.0',generated_at:new Date().toISOString(),input:{address:input.address,assessment_geometry:geometry,study_boundary_sha256:fingerprint,original_parcel:input.parcel||null,boundary_type:input.parcel?'User-confirmed assessment subset or whole parcel':'User-drawn study area; official parcel not verified'},metrics,overall_project_decision:null,capacity_reserved:false,mode:'Live public-data preliminary screening',limitations:['Only the chosen study area was queried.','Original parcel and study boundary are separate; neither is a title survey.','This is a partial report. Skipped agent-dependent sections were not assessed.','Intersections are not clipped class-acreage percentages or confirmed environmental exclusions.']};
}
