// Pinned polygon-clipping 0.15.7, MIT; shared by the browser and Worker.
import clipping from './vendor/polygon-clipping.mjs';
export function polygons(g){if(g?.type==='Polygon')return[g.coordinates];if(g?.type==='MultiPolygon')return g.coordinates;throw Error('A polygon study area is required.');}
function orientation(a,b,c){return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
function on(p,a,b){return Math.abs(orientation(a,b,p))<1e-14&&p[0]>=Math.min(a[0],b[0])&&p[0]<=Math.max(a[0],b[0])&&p[1]>=Math.min(a[1],b[1])&&p[1]<=Math.max(a[1],b[1]);}
function intersects(a,b,c,d){return orientation(a,b,c)*orientation(a,b,d)<0&&orientation(c,d,a)*orientation(c,d,b)<0;}
function ringArea(r){const rad=Math.PI/180;let sum=0;for(let i=0;i<r.length-1;i++)sum+=(r[i+1][0]-r[i][0])*rad*(2+Math.sin(r[i][1]*rad)+Math.sin(r[i+1][1]*rad));return Math.abs(sum)*6371007.1809**2/2;}
export function areaM2(g){return polygons(g).reduce((sum,p)=>sum+p.reduce((a,r,i)=>a+(i?-1:1)*ringArea(r),0),0);}
export function validatePolygon(g,{parcel=false}={}){
 const ps=polygons(g);if(!Array.isArray(ps)||!ps.length||ps.length>100)throw Error('The study boundary is empty or too complex.');let count=0;
 for(const p of ps){if(!Array.isArray(p)||!p.length)throw Error('A closed polygon is required.');for(const r of p){
  if(!Array.isArray(r)||r.length<4||JSON.stringify(r[0])!==JSON.stringify(r.at(-1)))throw Error('Each boundary must be closed with at least three vertices.');
  count+=r.length;if(count>2500)throw Error('Boundary exceeds 2,500 vertices.');
  for(const q of r)if(!Array.isArray(q)||q.length!==2||!q.every(Number.isFinite)||q[0]<-95.3||q[0]>-74||q[1]<41.5||q[1]>57.6)throw Error('Select a study area within Ontario.');
  for(let i=0;i<r.length-1;i++)for(let j=i+2;j<r.length-1;j++){if(i===0&&j===r.length-2)continue;const a=r[i],b=r[i+1],c=r[j],d=r[j+1];if(intersects(a,b,c,d)||on(a,c,d)||on(b,c,d)||on(c,a,b)||on(d,a,b))throw Error('Boundary edges intersect or touch. Redraw the polygon.');}
 }}
 const area=areaM2(g);if(!Number.isFinite(area)||area<20||(!parcel&&area>20_000_000))throw Error('Study area must be between 20 m² and 2,000 hectares.');return g;
}
function geometry(ps){if(!ps.length)throw Error('The drawn area does not overlap the address parcel. Draw across land inside its boundary.');return ps.length===1?{type:'Polygon',coordinates:ps[0]}:{type:'MultiPolygon',coordinates:ps};}
export function clipToParcel(study,parcel){
 validatePolygon(study);if(!parcel)return study;validatePolygon(parcel,{parcel:true});
 return validatePolygon(geometry(clipping.intersection(polygons(study),polygons(parcel))));
}
export function contained(inner,outer){return clipping.difference(polygons(inner),polygons(outer)).length===0;}
export function inside(point,g){return polygons(g).some(p=>p.every((r,k)=>{let hit=false;for(let i=0,j=r.length-1;i<r.length;j=i++){const a=r[i],b=r[j];if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return k?!hit:hit;}));}
export function arcgisRings(g){return polygons(g).flatMap(p=>p.map((ring,i)=>{const signed=ring.slice(0,-1).reduce((s,q,j)=>s+q[0]*ring[j+1][1]-ring[j+1][0]*q[1],0);return(i===0?signed>0:signed<0)?[...ring].reverse():ring;}));}
