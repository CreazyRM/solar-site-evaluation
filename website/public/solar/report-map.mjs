// Shared interactive report maps. Reference overlays never change report findings.
const instances=new Map();
const SOIL='https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer';
const WETLAND='https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer';
function referenceTiles(service,layerId,status){
 const ArcGIS=L.TileLayer.extend({getTileUrl(coords){
  const size=this.getTileSize(),nw=this._map.options.crs.project(this._map.unproject(L.point(coords.x*size.x,coords.y*size.y),coords.z)),se=this._map.options.crs.project(this._map.unproject(L.point((coords.x+1)*size.x,(coords.y+1)*size.y),coords.z));
  return service+'/export?'+new URLSearchParams({f:'image',bbox:[nw.x,se.y,se.x,nw.y].join(','),bboxSR:3857,imageSR:3857,size:'256,256',format:'png32',transparent:'true',layers:'show:'+layerId});
 }});
 const layer=new ArcGIS('',{maxZoom:19,opacity:.6,attribution:'Ontario public mapping · reference layer'});
 layer.on('tileerror',()=>status('A reference layer could not load. Report findings and source dates are unchanged.'));
 return layer;
}
export function createReportMap(id,{study,parcel,statusId,savedLayers=[]}={}){
 if(instances.has(id))instances.get(id).remove();
 const status=text=>{const e=document.getElementById(statusId);if(e)e.textContent=text;};
 const map=L.map(id,{preferCanvas:true,scrollWheelZoom:false});instances.set(id,map);
 const streets=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
 const satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagery © Esri and its data providers'});
 const overlays={};let fit;
 if(parcel){const layer=L.geoJSON(parcel,{style:{color:'#236c67',weight:3,fillOpacity:.02,dashArray:'7 5'}}).addTo(map);overlays['Original parcel']=layer;fit=layer;}
 if(study){const layer=L.geoJSON(study,{style:{color:'#b47417',weight:3,fillColor:'#e4bb61',fillOpacity:.25}}).addTo(map);overlays['Assessed study area']=layer;fit=layer;}
 if(!savedLayers.length){overlays['Soil · live reference']=referenceTiles(SOIL,29,status);overlays['Wetlands · live reference']=referenceTiles(WETLAND,15,status);}
 L.control.layers({'Street map':streets,'Satellite':satellite},overlays,{collapsed:false}).addTo(map);L.control.scale({imperial:false}).addTo(map);
 if(fit)map.fitBounds(fit.getBounds(),{padding:[30,30]});else map.setView([45.1,-80],7);
 const observer=new ResizeObserver(()=>map.invalidateSize({pan:false}));observer.observe(document.getElementById(id));map.on('unload',()=>observer.disconnect());
 let savedOverlay=null;
 function selectSaved(index){if(savedOverlay)map.removeLayer(savedOverlay);const layer=savedLayers[index];if(!layer){status('Street / satellite context only. Saved report values are unchanged.');return;}savedOverlay=L.imageOverlay(layer.file,layer.bounds,{opacity:1,attribution:'Saved evidence · Grey County / Ontario · dates in layer notes'}).addTo(map);savedOverlay.on('error',()=>status('Saved evidence image could not load.'));status(layer.note);}
 if(savedLayers.length)selectSaved(0);
 return{map,selectSaved};
}
export function initSavedReportMap(){
 let ready=null,controller=null;
 async function show(){
  if(document.getElementById('report').hidden)return;
  if(controller){controller.map.invalidateSize();return;}
  try{
   ready??=Promise.all([fetch('example-parcel.json').then(r=>{if(!r.ok)throw Error();return r.json();}),fetch('saved-map-layers.json').then(r=>{if(!r.ok)throw Error();return r.json();})]);
   const[parcel,saved]=await ready;if(controller)return;
   controller=createReportMap('saved-report-map',{parcel:parcel.geometry,statusId:'saved-map-status',savedLayers:saved.layers});
   const select=document.getElementById('saved-evidence-layer');select.replaceChildren();
   for(const[index,layer]of saved.layers.entries()){const option=document.createElement('option');option.value=index;option.textContent=layer.name;select.append(option);}
   const context=document.createElement('option');context.value='-1';context.textContent='Street / satellite context only';select.append(context);
   select.onchange=()=>controller.selectSaved(Number(select.value));
  }catch{ready=null;document.getElementById('saved-map-status').textContent='Saved map layers could not load. Please reopen this report.';}
 }
 window.addEventListener('solar:saved-report-open',show);
 window.addEventListener('solar:map-resize',()=>controller?.map.invalidateSize());
 show();
}
