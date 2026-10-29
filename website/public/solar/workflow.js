import {validatePolygon,areaM2,clipToParcel,polygons,contained} from './geometry.mjs';
import {createReportMap,initSavedReportMap} from './report-map.mjs';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'Unknown').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let map,selection,official,parcel=null,chosen=null,lookupAddress='',pending=false,lastReport=null,requestNumber=0,boundaryRevision=0,candidateOutlines=null,lookupContext=null;
function message(text){$('boundary-status').textContent=text;}
function invalidate(){boundaryRevision++;chosen=null;lastReport=null;$('study-confirm').checked=false;$('live-report').hidden=true;$('evaluate-study').disabled=true;$('evaluation-events').replaceChildren();}
function drawSelection(g){selection.clearLayers();L.geoJSON(g,{style:{color:'#bc781e',weight:3,fillColor:'#e4bb61',fillOpacity:.25}}).eachLayer(layer=>selection.addLayer(layer));}
function changed(){invalidate();const layers=selection.getLayers();if(!layers.length){$('study-area').textContent='No study boundary';message('');return;}
 try{const parts=layers.flatMap(layer=>polygons(layer.toGeoJSON(false).geometry));const raw=validatePolygon(parts.length===1?{type:'Polygon',coordinates:parts[0]}:{type:'MultiPolygon',coordinates:parts});const g=clipToParcel(raw,parcel?.geometry);const clipped=parcel&&!contained(raw,parcel.geometry);drawSelection(g);chosen=g;$('study-area').textContent=`${(areaM2(g)/4046.8564224).toFixed(3)} acres selected`;message(clipped?'Outside-parcel segments were trimmed automatically.':'');}
 catch(error){selection.clearLayers();message(error.message);$('study-area').textContent='No overlapping study area';}}
function setSelection(g){drawSelection(g);changed();}
function initMap(){if(map){map.invalidateSize();return;}map=L.map('boundary-map',{preferCanvas:true}).setView([45.1,-80],7);
 const streets=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
 const satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagery © Esri and its data providers'});
 L.control.layers({'Street map':streets,'Satellite':satellite},null,{position:'topright'}).addTo(map);
 selection=L.featureGroup().addTo(map);official=L.featureGroup().addTo(map);candidateOutlines=L.featureGroup().addTo(map);
 map.addControl(new L.Control.Draw({position:'topleft',draw:{polygon:{allowIntersection:false,showArea:true,shapeOptions:{color:'#bc781e'}},rectangle:false,polyline:false,circle:false,marker:false,circlemarker:false},edit:{featureGroup:selection}}));
 let actionApplied=false;
 map.on(L.Draw.Event.CREATED,event=>{actionApplied=true;selection.clearLayers();selection.addLayer(event.layer);changed();});
 map.on('draw:edited draw:deleted',()=>{actionApplied=true;changed();});
 map.on('draw:drawstart draw:editstart draw:deletestart',()=>{actionApplied=false;invalidate();});
 map.on('draw:drawstop draw:editstop draw:deletestop',()=>{if(!actionApplied)changed();});
}
function candidateSelected(candidate){parcel=candidate.kind==='assessment_parcel'?{...candidate,discovery:lookupContext}:null;candidateOutlines.clearLayers();official.clearLayers();selection.clearLayers();invalidate();
 if(parcel){L.geoJSON(parcel.geometry,{style:{color:'#2b6b65',weight:2,fillOpacity:.04,dashArray:'7 5'},interactive:false}).addTo(official);setSelection(parcel.geometry);map.fitBounds(official.getBounds(),{padding:[35,35]});$('parcel-meta').textContent=`Original public assessment parcel · retrieved ${candidate.retrieved_at?.slice(0,10)||'date unknown'}. ${candidate.address_match==='near_location_only'?'Nearby location candidate; civic-address match is not established. ':candidate.address_match==='point_intersection_only'?'Address-point intersection only; confirm the civic address. ':''}Teal dashed outline stays unchanged.`;}
 else{map.setView([candidate.latitude,candidate.longitude],16);$('parcel-meta').textContent='Location candidate only. No parcel boundary is verified. Click consecutive vertices to draw your study polygon; automatic trimming requires a matched parcel.';message('');}
 $('run-address').textContent=lookupAddress;
}
async function findBoundary(event,locationIndex=null){event?.preventDefault();event?.stopImmediatePropagation();if(pending)return;if(!$('address-form').reportValidity())return;
 const address=locationIndex===null?$('address').value.trim():lookupAddress;lookupAddress=address;const number=++requestNumber;
 $('boundary-workspace').hidden=false;$('welcome').hidden=true;$('library').hidden=true;$('report').hidden=true;$('live-report').hidden=true;$('search-status').hidden=true;
 document.querySelectorAll('.report-nav').forEach(el=>el.hidden=true);history.replaceState(null,'',location.pathname);
 initMap();parcel=null;lookupContext=null;official.clearLayers();candidateOutlines.clearLayers();selection.clearLayers();invalidate();$('candidate-list').replaceChildren();$('lookup-progress').replaceChildren();$('lookup-evidence').replaceChildren();$('lookup-note').textContent='';message('Discovering public parcel sources…');$('parcel-meta').textContent='Locating the address and checking the jurisdiction.';
 const button=$('address-form').querySelector('[type=submit]');button.disabled=true;const rows=new Map();
 function progress(item){if(!item.message)return;let row=rows.get(item.stage);if(!row){row=document.createElement('li');rows.set(item.stage,row);$('lookup-progress').append(row);}row.textContent=item.message;}
 try{
  const params=new URLSearchParams({address,stream:'1'});if(locationIndex!==null)params.set('location',locationIndex);
  const r=await fetch('/api/locate?'+params);if(!r.ok)throw Error('Address lookup failed.');
  const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='',response=null;
  while(true){const{done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.trim())continue;const item=JSON.parse(line);if(item.stage==='error')throw Error(item.message);if(item.stage==='complete')response=item.result;else progress(item);}}
  if(number!==requestNumber)return;if(!response)throw Error('Source discovery did not return a result.');
  lookupContext={jurisdiction:response.jurisdiction,evidence:response.evidence,cache:response.cache,discovery_status:response.discovery_status,source_review:response.source_review,ai_fallback:response.ai_fallback};
  $('lookup-note').textContent=response.notice||'';
  const evidence=$('lookup-evidence');if(response.jurisdiction){const jurisdiction=document.createElement('p');jurisdiction.textContent='Jurisdiction: '+response.jurisdiction.municipality+(response.jurisdiction.upper_tier?' / '+response.jurisdiction.upper_tier:'');evidence.append(jurisdiction);}
  if(response.cache?.hit){const cached=document.createElement('p');cached.textContent='Reused and revalidated a previously discovered public parcel service.';evidence.append(cached);}
  if(response.evidence?.length){const details=document.createElement('details'),summary=document.createElement('summary'),list=document.createElement('ul');summary.textContent='Source checks ('+response.evidence.length+')';for(const record of response.evidence){const row=document.createElement('li');row.textContent=record.status+' · '+record.source;list.append(row);}details.append(summary,list);evidence.append(details);}
  if(!response.candidates?.length){$('parcel-meta').textContent='No verified parcel was found. Navigate to the correct location and draw a study area; it will remain user-defined.';message('Try a more complete address, or draw a study area at the correct location.');}
  const choose=(candidate,b)=>{if(Number.isInteger(candidate.discovery_index)){findBoundary(null,candidate.discovery_index);return;}document.querySelectorAll('.candidate-button').forEach(el=>el.classList.remove('selected'));b.classList.add('selected');candidateSelected(candidate);};
  for(const[i,candidate]of(response.candidates||[]).entries()){
   const b=document.createElement('button');b.className='candidate-button';b.textContent=(response.candidates.length>1?(i+1)+'. ':'')+candidate.label;b.type='button';b.addEventListener('click',()=>choose(candidate,b));$('candidate-list').append(b);
   if(response.candidates.length===1){b.classList.add('selected');candidateSelected(candidate);}
   else if(candidate.geometry){const outline=L.geoJSON(candidate.geometry,{style:{color:'#537da2',weight:2,fillOpacity:.08}}).addTo(candidateOutlines);outline.bindTooltip('Candidate '+(i+1));outline.on('click',()=>choose(candidate,b));}
  }
  if(candidateOutlines.getLayers().length)map.fitBounds(candidateOutlines.getBounds(),{padding:[35,35]});
  if(response.candidates?.length>1){$('parcel-meta').textContent=response.discovery_status==='location_selection_required'?'Choose an address location to continue public parcel discovery.':'Candidate parcels are shown in blue. Choose one to establish the assessment boundary.';message('Choose the correct candidate, then confirm its location and boundary on the map.');}
 }catch(error){message('Lookup unavailable: '+error.message+'. You may draw a user-defined study boundary at the correct location.');}
 finally{if(number===requestNumber)button.disabled=false;map.invalidateSize();$('boundary-workspace').scrollIntoView({behavior:'smooth',block:'start'});}
}
function renderReport(report){lastReport=report;const m=report.metrics;const area=m.area.value;
 const facts=(values)=>'<dl class="facts">'+values.map(([k,v])=>`<div class="fact"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')+'</dl>';
 const metric=(name,item,detail)=>`<section class="detail-section"><div class="detail-header"><h2>${esc(name)}</h2><span class="section-status review">${esc(item.status.replaceAll('_',' '))}</span></div>${item.status==='skipped'?`<p class="section-intro">${esc(item.reason)}</p>`:detail}<p class="live-source">${item.source?.startsWith('https://')?`<a href="${esc(item.source)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:esc(item.source||'')}${item.retrieved_at?' · Retrieved '+esc(item.retrieved_at):''}</p></section>`;
 const soil=m.soil;let soilDetail='';if(soil.value)soilDetail=facts([['Classes intersecting the study area',soil.value.classes.join(', ')||'Unclassified'],['Soil mapping units',soil.value.mapping_units.length],['Lower-class exception review',soil.value.exception_review_required?'Required for CLI 1–3':'No CLI 1–3 returned; other requirements still apply']])+`<p class="callout">These are intersecting mapping units, not clipped class-acreage shares. Mixed-unit proportions do not locate components inside the study area.</p>`;
 const wet=m.wetlands;const wetDetail=wet.value?facts([['Mapped wetland intersections',wet.value.mapped_intersections],['Absence confirmed','No'],['Regulatory buffers','Not assessed']]):'';
 const omitted=['slope_full_area','truck_access','line_phases','connection_route','capacity_2mw','zoning','official_plan'];
 $('live-report').innerHTML=`<header class="report-header"><div><h1>${esc(report.input.address)}</h1><p>Selected study area · ${esc(new Date(report.generated_at).toLocaleString())}</p></div><span class="status-pill">Partial assessment</span></header><div class="report-notice"><p>Public data was queried for the confirmed study boundary. Unavailable sections below were not assessed. No development approval or grid capacity is established.</p></div>${metric('1. Land & study area',m.area,facts([['Selected area',area.acres.toFixed(3)+' acres'],['Area method','Authalic-sphere estimate'],['Boundary type',report.input.boundary_type],['Title PIN','Not independently verified'],['Parcel address evidence',({civic_and_road_tokens:'Civic and road tokens matched; verify on map',near_location_only:'Nearby candidate only; civic address is not verified',point_intersection_only:'Address-point intersection only; civic address is not verified'})[report.input.original_parcel?.address_match]||'No independent parcel address match'],['Source jurisdiction',report.input.original_parcel?.discovery?.jurisdiction?.municipality||'See municipality query in report data']]))}${metric('2. Agricultural soil capability',soil,soilDetail)}${metric('Wetlands',wet,wetDetail)}${omitted.map(k=>metric(({slope_full_area:'Terrain slope',truck_access:'3. Truck access',line_phases:'Line phases',connection_route:'Connection distance',capacity_2mw:'4. Electrical capacity at 2 MW',zoning:'5. Zoning',official_plan:'Official Plan'})[k],m[k],'')).join('')}<div class="report-actions"><button class="primary" id="download-live">Download report JSON ↓</button><button class="outline-button" id="print-live">Print report</button></div><p class="fingerprint">Study boundary SHA-256: ${esc(report.input.study_boundary_sha256)}</p>`;
 $('live-report').insertAdjacentHTML('afterbegin','<section class="map-panel report-interactive-panel"><div class="map-panel-header"><h2>Assessment map</h2></div><div id="live-report-map" class="interactive-report-map" aria-label="Interactive assessment report map"></div><p class="report-map-note">Gold: assessed study area. Teal: original parcel. Use Layers to select the basemap and reference overlays.</p><p id="live-map-status" class="report-map-note" role="status"></p></section>');
 $('live-report').hidden=false;createReportMap('live-report-map',{study:report.input.assessment_geometry,parcel:report.input.original_parcel?.geometry,statusId:'live-map-status'});$('download-live').onclick=()=>download(report,'study-area-report.json');$('print-live').onclick=()=>window.print();$('live-report').scrollIntoView({behavior:'smooth'});
}
function download(value,name){const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function runAssessment(){if(pending||!chosen||!$('study-confirm').checked)return;pending=true;$('evaluate-study').disabled=true;$('address-form').querySelector('button[type=submit]').disabled=true;
 const geometry=structuredClone(chosen),originalParcel=parcel?structuredClone(parcel):null,address=lookupAddress,revision=boundaryRevision;
 message('Evaluating the confirmed study boundary…');$('evaluation-events').replaceChildren();
 try{
  const response=await fetch('/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({address,geometry,parcel:originalParcel})});
  if(!response.ok){const result=await response.json();throw Error(result.error||'Assessment request failed.');}
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',result=null;
  while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.trim())continue;const item=JSON.parse(line);if(item.stage==='error')throw Error(item.message);if(item.stage==='complete')result=item.report;else{const row=document.createElement('li');row.textContent=item.message;$('evaluation-events').append(row);}}}
  if(!result)throw Error('No completed assessment was returned.');if(revision!==boundaryRevision){message('Boundary changed during assessment. Confirm it and run again for the new area.');return;}renderReport(result);message('Partial assessment completed. Review the source results and unassessed sections below.');
 }catch(error){message('Assessment could not complete: '+error.message);}
 finally{pending=false;$('evaluate-study').disabled=!chosen||!$('study-confirm').checked;$('address-form').querySelector('button[type=submit]').disabled=false;}
}
function init(){
 $('address-form').addEventListener('submit',findBoundary,true);
 $('address-form').querySelector('button[type=submit]').disabled=false;
 $('study-confirm').addEventListener('change',()=>{$('evaluate-study').disabled=!chosen||!$('study-confirm').checked||pending;});
 $('evaluate-study').addEventListener('click',runAssessment);
 $('reset-study').onclick=()=>{if(pending)return;if(parcel)setSelection(parcel.geometry);else{selection.clearLayers();changed();}};
 $('clear-study').onclick=()=>{if(pending)return;selection.clearLayers();changed();};
 initSavedReportMap();
 for(const id of ['open-example','try-example','back-overview','overview-nav','home-brand','library-nav'])$(id)?.addEventListener('click',()=>{if(!pending){$('boundary-workspace').hidden=true;$('live-report').hidden=true;}});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
