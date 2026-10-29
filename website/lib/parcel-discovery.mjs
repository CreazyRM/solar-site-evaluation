import directory from './municipal-directory.json' with {type:'json'};
import {validatePolygon,polygons,inside} from '../public/solar/geometry.mjs';
import {readSourceCache,writeSourceCache,dropSourceCache} from './source-cache.mjs';
const ADMIN='https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open03/MapServer/14';
const PORTAL='https://www.arcgis.com/sharing/rest';
const SEEDS=[{authority:'Grey',url:'https://gis.grey.ca/server/rest/services/Public/Service_ParcelLabels/MapServer/0'},{authority:'Bruce',url:'https://maps.brucecounty.on.ca/arcgisserver/rest/services/public/parcels_pub_wa/MapServer/0'}];
const parcelName=/parcel|cadastr|assessment.?boundar|property.?boundar|property.?fabric|tax.?parcel/i;
const excluded=/historic|archive|proposed|flood|soil|zoning|address.?point|label|dimension|condo.?unit/i;
export function normalizeName(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(township|municipality|municipal|regional|region|county|city|town|village|district|corporation|the|of)\b/g,' ').replace(/[^a-z0-9]/g,'');}
function domain(url){return new URL(url).hostname.replace(/^www\./,'').toLowerCase();}
function within(host,root){return host===root||host.endsWith('.'+root);}
export function safePublicURL(raw){
 const u=new URL(raw);if(u.protocol==='http:')u.protocol='https:';
 if(u.protocol!=='https:'||u.username||u.password||(u.port&&u.port!=='443')||/^[\d.]+$/.test(u.hostname)||u.hostname.includes(':')||!u.hostname.includes('.')||/\.(local|internal|localhost|test|invalid)$/i.test(u.hostname)||/(^|\.)localhost$/i.test(u.hostname)||/token|password|secret|api.?key/i.test(u.search))throw Error('unsafe_source_url');
 u.hash='';return u.href.replace(/\/$/,'');
}
function publicHost(url,roots=[]){const host=domain(url);return roots.some(root=>within(host,root))||within(host,'arcgis.com')||within(host,'arcgisonline.com')||within(host,'geo.ca')||within(host,'gc.ca')||within(host,'ontario.ca')||within(host,'gov.on.ca');}
function urls(text,base){return [...String(text||'').matchAll(/(?:href|src)\s*=\s*["']([^"']+)["']|https?:\/\/[^\s<>"']+/gi)].map(m=>{try{return safePublicURL(new URL((m[1]||m[0]).replace(/&amp;/g,'&'),base).href);}catch{return null;}}).filter(Boolean);}
function createClient(roots,evidence){let calls=0;const deadline=Date.now()+40000,exhausted=new Set();
 return async function request(raw,params=null,{text=false,post=false}={}){
  const url=safePublicURL(raw);if(!publicHost(url,roots))throw Error('unverified_source_host');if(exhausted.has(url))throw Error('timeout_retry_exhausted');
  const form=new URLSearchParams(Object.entries(params||{}).map(([k,v])=>[k,String(v)]));
  for(let attempt=0;attempt<2;attempt++){
   if(++calls>46||Date.now()>deadline)throw Error('discovery_budget_reached');
   const started=new Date().toISOString();
   try{const target=params&&!post?url+'?'+form:url;const r=await fetch(target,{method:post?'POST':'GET',body:post?form:undefined,headers:{Accept:text?'text/html':'application/json'},redirect:'manual',signal:AbortSignal.timeout(Math.min(6500,Math.max(1000,deadline-Date.now())))});
    if(r.status>=300&&r.status<400){const next=safePublicURL(new URL(r.headers.get('Location'),url).href);if(!publicHost(next,roots))throw Error('unverified_redirect');if(attempt===0){raw=next;return request(next,params,{text,post});}throw Error('source_redirect');}
    if(!r.ok)throw Error(r.status===401?'authentication_required':r.status===403?'access_denied':'http_'+r.status);
    const body=await r.text();if(body.length>(text?1_500_000:5_000_000))throw Error('response_too_large');
    const data=text?body:JSON.parse(body);if(data?.error)throw Error([401,498,499].includes(data.error.code)?'authentication_required':'source_service_error');
    evidence.push({source:url,retrieved_at:started,status:'retrieved'});return data;
   }catch(error){const timed=['TimeoutError','AbortError'].includes(error.name);evidence.push({source:url,retrieved_at:started,status:timed?'timeout':String(error.message)});if(timed&&attempt===0)continue;if(timed)exhausted.add(url);throw error;}
  }
 };
}
function stage(emit,stage,message,status='completed'){emit({stage,message,status});}
function directoryFor(names){const keys=new Set(names.map(normalizeName).filter(Boolean));return directory.rows.filter(r=>keys.has(normalizeName(r.name.split(',')[0])));}
export function addressMatches(address,text){
 const tokens=String(address).toLowerCase().match(/[a-z]+|\d+/g)||[],civic=tokens[0];if(!/^\d+$/.test(civic||''))return false;
 const label=String(text||'').toLowerCase(),numbers=label.match(/\d+/g)||[];
 if(!numbers.some(t=>Number(t)===Number(civic)))return false;
 const rest=tokens.slice(1);if(/^(hwy|highway|route|county|concession|road|rd)$/.test(rest[0]||'')){const route=rest.find(t=>/^\d+$/.test(t));return !!route&&numbers.some(t=>Number(t)===Number(route));}
 const name=rest.find(t=>/^[a-z]+$/.test(t));return !!name&&new RegExp('\\b'+name+'\\b').test(label);
}
function pointCandidate(item,index=null){return{kind:'location_candidate',label:item.name,longitude:item.lng,latitude:item.lat,source:item.source||'https://geolocator.api.geo.ca/',retrieved_at:new Date().toISOString(),precision:item.tag,requires_confirmation:true,discovery_index:index};}
function extentContains(extent,point){return !Array.isArray(extent)||extent.length!==2||(point.lng>=extent[0][0]&&point.lng<=extent[1][0]&&point.lat>=extent[0][1]&&point.lat<=extent[1][1]);}
function rootService(url){return url.match(/^(.+\/(?:MapServer|FeatureServer))(?:\/\d+)?(?:\?.*)?$/i)?.[1];}
function scoreSource(item){return(parcelName.test(item.title||'')?10:0)-(excluded.test(item.title||'')?15:0);}
async function publisher(item,roots,linked,request){
 const host=domain(item.url);if(roots.some(r=>within(host,r)))return{verified:true,method:'Service hosted on an official municipality domain',evidence:item.url};
 if(linked.some(link=>domain(link)===host||link.includes('/'+(item.url.match(/arcgis\.com\/([^/]+)\//)?.[1]||'NO_ORG')+'/')))return{verified:true,method:'GIS portal linked by the official municipality website',evidence:item.discovery_source};
 const org=item.url.match(/services\d*\.arcgis\.com\/([a-z0-9]+)\//i)?.[1];
 if(org){const data=await request(PORTAL+'/portals/'+org,{f:'json'});const contact=data.portalProperties?.links?.contactUs?.url;const linkedOrg=linked.some(link=>data.urlKey&&domain(link)===data.urlKey.toLowerCase()+'.maps.arcgis.com');
  if(linkedOrg&&contact&&roots.some(r=>within(domain(contact),r)))return{verified:true,method:'Official website links the GIS organization; organization contact links back to the municipality',evidence:contact,org_id:org};
 }
 return{verified:false,method:'Publisher could not be independently corroborated'};
}
async function inspectService(item,request,proof){
 const root=rootService(item.url);if(!root)return[];
 if(/\/(MapServer|FeatureServer)\/\d+$/i.test(item.url)){const m=await request(item.url,{f:'json'});return validLayer(m,item.title)?[{url:item.url,name:m.name,publisher:proof,source_date:m.editingInfo?.lastEditDate||null}]:[];}
 const data=await request(root,{f:'json'});const layers=(data.layers||[]).filter(l=>parcelName.test(l.name)&&!excluded.test(l.name)).slice(0,4);
 if(!layers.length&&parcelName.test(item.title)&&data.layers?.length===1)layers.push(data.layers[0]);
 const results=await Promise.allSettled(layers.map(async l=>{const url=root+'/'+l.id,m=await request(url,{f:'json'});return validLayer(m,item.title)?{url,name:m.name,publisher:proof,source_date:m.editingInfo?.lastEditDate||data.editingInfo?.lastEditDate||null}:null;}));
 return results.filter(r=>r.status==='fulfilled'&&r.value).map(r=>r.value);
}
function validLayer(m,title){return m.geometryType==='esriGeometryPolygon'&&Array.isArray(m.fields)&&/query/i.test(m.capabilities||'')&&parcelName.test(m.name+' '+title)&&!excluded.test(m.name);}
function distanceMetres(point,g){const cos=Math.cos(point.lat*Math.PI/180);let best=Infinity;for(const p of polygons(g))for(const ring of p)for(let i=1;i<ring.length;i++){const a=[(ring[i-1][0]-point.lng)*111320*cos,(ring[i-1][1]-point.lat)*111320],b=[(ring[i][0]-point.lng)*111320*cos,(ring[i][1]-point.lat)*111320],dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,-(a[0]*dx+a[1]*dy)/(dx*dx+dy*dy||1)));best=Math.min(best,Math.hypot(a[0]+t*dx,a[1]+t*dy));}return best;}
async function queryLayer(layer,point,address,request,{addressOnly=false,metadata=null,nearby=false}={}){
 const meta=metadata||await request(layer.url,{f:'json'});if(!validLayer(meta,layer.name))throw Error('not_a_queryable_parcel_polygon');
 const fields=meta.fields.filter(f=>f.type==='esriFieldTypeString'&&/address|civic|street|location/i.test(f.name)&&/^[a-z0-9_]+$/i.test(f.name));
 const civic=address.match(/\d+/)?.[0]?.replace(/^0+/,'');
 let params={f:'geojson',where:'1=1',outFields:'*',outSR:4326,returnGeometry:'true',resultRecordCount:12};
 if(addressOnly){if(!civic||!fields.length)return[];params.where='('+fields.map(f=>`UPPER(${f.name}) LIKE '%${civic}%'`).join(' OR ')+')';}
 else Object.assign(params,{geometry:JSON.stringify(nearby?{xmin:point.lng-.0006,ymin:point.lat-.0004,xmax:point.lng+.0006,ymax:point.lat+.0004,spatialReference:{wkid:4326}}:{x:point.lng,y:point.lat,spatialReference:{wkid:4326}}),geometryType:nearby?'esriGeometryEnvelope':'esriGeometryPoint',inSR:4326,spatialRel:'esriSpatialRelIntersects'});
 const data=await request(layer.url+'/query',params,{post:true});if(data.exceededTransferLimit)throw Error('incomplete_parcel_query');
 const features=(data.features||[]).filter(f=>{try{validatePolygon(f.geometry,{parcel:true});}catch{return false;}return addressOnly?addressMatches(address,fields.map(v=>f.properties?.[v.name]).join(' ')):nearby?distanceMetres(point,f.geometry)<=35:inside([point.lng,point.lat],f.geometry);});
 if(!features.length&&!addressOnly&&!nearby){if(fields.length){const addressFound=await queryLayer(layer,point,address,request,{addressOnly:true,metadata:meta});if(addressFound.length)return addressFound;}return queryLayer(layer,point,address,request,{nearby:true,metadata:meta});}
 if(nearby)features.sort((a,b)=>distanceMetres(point,a.geometry)-distanceMetres(point,b.geometry));
 return features.slice(0,6).map(f=>{
  const text=fields.map(v=>f.properties?.[v.name]).filter(Boolean).join(' · '),match=addressMatches(address,text);
  const identifier=['PARCELID','PARCEL_ID','ARN','ROLL_NO','ROLLNUMBER','PIN'].map(k=>f.properties?.[k]).find(Boolean);
  return{kind:'assessment_parcel',label:(text||(identifier?'Parcel '+identifier:layer.name))+(nearby?' · near address ('+Math.round(distanceMetres(point,f.geometry))+' m); confirm':' · public parcel'),geometry:f.geometry,attributes:f.properties,source:layer.url,retrieved_at:new Date().toISOString(),source_data_date:meta.editingInfo?.lastEditDate||layer.source_date||null,publisher:layer.publisher,address_match:match?'civic_and_road_tokens':nearby?'near_location_only':'point_intersection_only',requires_confirmation:true,location_precision:point?.tag||null};
 });
}
async function officialLinks(entries,request){
 const linked=[],pages=[];const first=await Promise.allSettled(entries.slice(0,2).map(async e=>{const html=await request(e.url,null,{text:true});return{url:e.url,links:urls(html,e.url)};}));
 for(const r of first)if(r.status==='fulfilled'){linked.push(...r.value.links);pages.push(...r.value.links.filter(u=>domain(u)===domain(r.value.url)&&/open.?data|mapping|\/gis|maps|geoportal/i.test(u)).slice(0,2));}
 const extra=await Promise.allSettled([...new Set(pages)].slice(0,2).map(async url=>urls(await request(url,null,{text:true}),url)));for(const r of extra)if(r.status==='fulfilled')linked.push(...r.value);
 return [...new Set(linked)];
}
async function serviceDirectoryItems(items,linked,roots,request){
 const directories=[...new Set([...items.map(i=>i.url),...linked].filter(Boolean).filter(u=>roots.some(r=>within(domain(u),r))).map(u=>u.match(/^(.+\/rest\/services)(?:\/|$)/i)?.[1]).filter(Boolean))].slice(0,2),found=[];
 for(const base of directories){try{const root=await request(base,{f:'json'}),folders=(root.folders||[]).filter(n=>!/system|utilities|archive|historic|test/i.test(n)).sort((a,b)=>Number(/public|open|base|property/i.test(b))-Number(/public|open|base|property/i.test(a))).slice(0,2);
  const listings=[root,...(await Promise.allSettled(folders.map(f=>request(base+'/'+encodeURIComponent(f),{f:'json'})))).filter(r=>r.status==='fulfilled').map(r=>r.value)];
  for(const listing of listings)for(const service of listing.services||[]){if(['MapServer','FeatureServer'].includes(service.type)&&/parcel|property|cadastr|base.?map|base.?data|public/i.test(service.name)&&!excluded.test(service.name))found.push({url:base+'/'+service.name+'/'+service.type,title:service.name,discovery_source:base});}
 }catch{}}
 return found.slice(0,4);
}
async function discoverLayers(names,point,entries,request,emit,review){
 const roots=entries.map(e=>domain(e.url));const linked=await officialLinks(entries,request);
 stage(emit,'sources','Searching public GIS catalogues and municipality portals.','running');
 const queries=names.filter(Boolean).slice(0,2).map(name=>'(parcel OR parcels OR cadastral OR property) AND (type:"Feature Service" OR type:"Map Service") AND "'+name.replace(/[^a-z0-9 -]/gi,'')+'"');
 const searches=await Promise.allSettled(queries.map(q=>request(PORTAL+'/search',{f:'json',q,bbox:[point.lng-.02,point.lat-.02,point.lng+.02,point.lat+.02].join(','),num:18,sortField:'relevance'})));
 const items=searches.filter(r=>r.status==='fulfilled').flatMap(r=>r.value.results||[]).filter(i=>i.url&&['Feature Service','Map Service'].includes(i.type)&&extentContains(i.extent,point)&&scoreSource(i)>=0).sort((a,b)=>scoreSource(b)-scoreSource(a));
 items.push(...await serviceDirectoryItems(items,linked,roots,request));
 for(const url of linked.filter(u=>/\/(MapServer|FeatureServer)(\/\d+)?$/i.test(u)))items.unshift({url,title:'Public parcel service',discovery_source:entries[0]?.url});
 const unique=[...new Map(items.map(i=>[i.url,i])).values()].slice(0,7),layers=[];
 for(let i=0;i<unique.length;i+=3){await Promise.allSettled(unique.slice(i,i+3).map(async item=>{try{item.url=safePublicURL(item.url);const proof=await publisher(item,roots,linked,request);if(!proof.verified){review.push({url:item.url,title:item.title,status:'publisher_unverified'});return;}layers.push(...await inspectService(item,request,proof));}catch(error){review.push({url:item.url,status:String(error.message)});}}));if(layers.length>=5)break;}
 return [...new Map(layers.map(l=>[l.url,l])).values()].slice(0,5);
}
export async function locateOntario(address,{emit=()=>{},selectedIndex=null}={}){
 if(typeof address!=='string'||address.trim().length<5||address.length>240)throw Error('Enter a complete Ontario address.');
 if(selectedIndex!==null&&(!Number.isInteger(selectedIndex)||selectedIndex<0||selectedIndex>4))throw Error('Invalid location selection.');
 const evidence=[],roots=[],request=createClient(roots,evidence),review=[];let locations=[],geocoderError=null;
 stage(emit,'geocode','Locating the address with government geocoding.','running');
 try{const raw=await request('https://geolocator.api.geo.ca/',{q:address,lang:'en',keys:'locate'});locations=(Array.isArray(raw)?raw:[]).filter(i=>/^ontario$/i.test(i.province||'')&&i.lng>=-95.3&&i.lng<=-74&&i.lat>=41.5&&i.lat<=57.6&&i.category==='Street'&&addressMatches(address,i.name)).slice(0,5);}catch(error){geocoderError=String(error.message);}
 if(!locations.length){try{const raw=await request('https://geogratis.gc.ca/services/geolocation/en/locate',{q:address});locations=(Array.isArray(raw)?raw:[]).filter(i=>/Ontario\s*$/i.test(i.title||'')&&/\.Street$/.test(i.type||'')&&i.geometry?.type==='Point'&&addressMatches(address,i.title)).map(i=>({name:i.title,lng:i.geometry.coordinates[0],lat:i.geometry.coordinates[1],tag:[i.qualifier],source:'https://geogratis.gc.ca/services/geolocation/en/locate'})).filter(i=>i.lng>=-95.3&&i.lng<=-74&&i.lat>=41.5&&i.lat<=57.6).slice(0,5);}catch(error){geocoderError??=String(error.message);}}
 locations=[...new Map(locations.map(i=>[i.lng.toFixed(6)+','+i.lat.toFixed(6),i])).values()];
 const response={address,candidates:[],jurisdiction:null,evidence,source_review:review,cache:{hit:false,scope:'Validated source metadata only; addresses and parcels are not cached'},ai_fallback:{status:'not_needed'},geocoder_error:geocoderError};
 if(locations.length>1&&selectedIndex===null){response.candidates=locations.map(pointCandidate);response.notice='Choose the matching address location to discover its public parcel services.';response.discovery_status='location_selection_required';return response;}
 let point=locations[selectedIndex??0];
 if(!point){
  stage(emit,'geocode','No unique government address match. Checking previously verified public services.','running');
  const fallback=await Promise.allSettled(SEEDS.map(async seed=>{const seedRoots=[seed.authority==='Grey'?'grey.ca':'brucecounty.on.ca'];roots.push(...seedRoots);const proof={verified:true,method:'Retained official public-service source; metadata revalidated',evidence:seed.url};return queryLayer({url:seed.url,name:'Assessment parcels',publisher:proof},null,address,request,{addressOnly:true});}));
  response.candidates=fallback.filter(r=>r.status==='fulfilled').flatMap(r=>r.value);if(response.candidates.length){response.notice='Address-matched public parcel candidate. Confirm the intended parcel on the map.';response.discovery_status='parcel_candidates';return response;}
  response.discovery_status='location_unresolved';response.ai_fallback={status:'not_configured',reason:'No AI source-review service is connected.'};response.notice='No precise Ontario address location was resolved. Try a more complete address or draw a study area at the correct map location.';return response;
 }
 stage(emit,'geocode','Government address location found; it is not a parcel boundary.');
 let admin=[];try{const data=await request(ADMIN+'/query',{f:'json',where:'1=1',geometry:JSON.stringify({x:point.lng,y:point.lat,spatialReference:{wkid:4326}}),geometryType:'esriGeometryPoint',inSR:4326,spatialRel:'esriSpatialRelIntersects',outFields:'*',returnGeometry:'false'});admin=(data.features||[]).map(f=>f.attributes);}catch{}
 if(!admin.length){response.candidates=[pointCandidate(point)];response.discovery_status='jurisdiction_unresolved';response.notice='Address location found, but the Ontario municipality could not be verified. Draw a user-defined study area or retry later.';return response;}
 const attributes=admin[0],lower=attributes.MUNICIPAL_NAME_SHORTFORM||attributes.MUNICIPAL_NAME,entries=directoryFor([lower,attributes.UPPER_TIER_MUNICIPALITY]);
 const lowerEntry=entries.find(e=>normalizeName(e.name.split(',')[0])===normalizeName(lower));
 const upper=attributes.UPPER_TIER_MUNICIPALITY||((lowerEntry?.tier==='Lower Tier')?lowerEntry.area:null);
 for(const e of directoryFor([upper]))if(!entries.some(x=>x.url===e.url))entries.push(e);
 roots.push(...entries.map(e=>domain(e.url)));
 response.jurisdiction={municipality:lower,upper_tier:upper||null,id:String(attributes.MUNID||attributes.ASSESSMENT_CODE||normalizeName(lower)),source:ADMIN,retrieved_at:new Date().toISOString(),official_websites:entries.map(e=>({name:e.name,url:e.url})),directory_source:directory.source};
 stage(emit,'jurisdiction','Jurisdiction: '+lower+(upper?' / '+upper:''));
 const cacheKey=response.jurisdiction.id;let layers=await readSourceCache(cacheKey),fromCache=!!layers?.length;
 const seeds=SEEDS.filter(s=>[lower,upper,lowerEntry?.area].some(n=>normalizeName(n)===normalizeName(s.authority))).map(s=>({url:s.url,name:'Assessment parcels',publisher:{verified:true,method:'Retained official source',evidence:s.url}}));
 async function query(layers){const rs=await Promise.allSettled(layers.slice(0,5).map(async layer=>({layer,candidates:await queryLayer(layer,point,address,request)})));return rs.filter(r=>r.status==='fulfilled'&&r.value.candidates.length).map(r=>r.value);}
 let matched=[];
 if(fromCache){stage(emit,'cache','Revalidating cached public parcel-service metadata.','running');matched=await query(layers);response.cache.hit=matched.length>0;if(!matched.length)await dropSourceCache(cacheKey);}
 if(!matched.length&&seeds.length){matched=await query(seeds);}
 if(!matched.length){layers=await discoverLayers([upper||lower,lower],point,entries,request,emit,review);stage(emit,'boundary','Testing discovered polygon services against the address point.','running');matched=await query(layers);}
 if(matched.length){await writeSourceCache(cacheKey,matched.map(m=>m.layer));response.candidates=[...new Map(matched.flatMap(m=>m.candidates).map(c=>[JSON.stringify(c.geometry),c])).values()].slice(0,8);response.discovery_status='parcel_candidates';response.notice='Public parcel candidates found for '+lower+'. Confirm the address and boundary on the map. Point intersection alone does not verify title or the civic address.';stage(emit,'boundary',response.candidates.length+' public parcel candidate(s) found.');}
 else{response.candidates=[pointCandidate(point)];response.discovery_status='parcel_unresolved';response.ai_fallback={status:'not_configured',reason:'No AI source-review service is connected.',handoff:{address,jurisdiction:response.jurisdiction,source_review:review,instructions:'Find a current publicly accessible assessment parcel polygon for this Ontario address. Verify publisher, polygon layer, source date and address evidence. Exclude GeoWarehouse and login-dependent services. Never turn a geocoder extent into a parcel boundary.'}};response.notice='Jurisdiction verified, but no usable public parcel was resolved. AI source review is not connected; draw a user-defined study area. A location point is not a parcel boundary.';stage(emit,'boundary','No usable public parcel found; manual study-area drawing remains available.');}
 return response;
}
