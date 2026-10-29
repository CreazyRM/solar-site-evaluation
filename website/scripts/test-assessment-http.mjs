// Integration check for an already running local preview; queries public sources.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {areaM2,contained,clipToParcel} from '../public/solar/geometry.mjs';
const base=process.argv[2]||'http://127.0.0.1:8787';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('This test requires a local preview.');
const parcel=JSON.parse(fs.readFileSync(new URL('../public/solar/example-parcel.json',import.meta.url)));
const r=parcel.geometry.coordinates[0],west=Math.min(...r.map(p=>p[0]))-.002,x=r.reduce((a,p)=>a+p[0]/r.length,0),y=r.reduce((a,p)=>a+p[1]/r.length,0);
const geometry={type:'Polygon',coordinates:[[[west,y-.001],[x+.0002,y-.001],[x+.0002,y+.001],[west,y+.001],[west,y-.001]]]};
const expected=clipToParcel(geometry,parcel.geometry);
const response=await fetch(base+'/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json',Origin:base},body:JSON.stringify({address:'019471 Highway 6 Georgian Bluffs ON',geometry,parcel})});
assert.equal(response.status,200);const events=(await response.text()).trim().split('\n').map(JSON.parse);
assert(!events.some(e=>e.stage==='error'),JSON.stringify(events));const report=events.find(e=>e.stage==='complete')?.report;assert(report);
assert(contained(report.input.assessment_geometry,parcel.geometry));assert(areaM2(report.input.assessment_geometry)<areaM2(geometry));assert(Math.abs(report.metrics.area.value.square_metres-areaM2(expected))<.01);
console.log(JSON.stringify({worker_clipping:'passed',selected_acres:report.metrics.area.value.acres,soil:report.metrics.soil.status,wetlands:report.metrics.wetlands.status,municipality:report.metrics.municipality.status}));
