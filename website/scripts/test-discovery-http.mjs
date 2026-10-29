// Live integration check for a local Worker; uses a public municipal test address.
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8787';if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw Error('Use a local Worker preview.');
for(let n=0;n<2;n++){
 const response=await fetch(base+'/api/locate?'+new URLSearchParams({address:'70 Collier Street Barrie Ontario',stream:'1'}));assert.equal(response.status,200);
 const events=(await response.text()).trim().split('\n').map(JSON.parse);assert(!events.some(e=>e.stage==='error'),JSON.stringify(events));
 const result=events.find(e=>e.stage==='complete')?.result;assert(result);assert.equal(result.jurisdiction.municipality,'BARRIE');assert.equal(result.discovery_status,'parcel_candidates');assert(result.candidates.some(c=>c.kind==='assessment_parcel'&&c.publisher.verified&&c.requires_confirmation));
 if(n===1)assert.equal(result.cache.hit,true);
 console.log(JSON.stringify({run:n+1,worker:'passed',jurisdiction:result.jurisdiction.municipality,parcels:result.candidates.length,cache_hit:result.cache.hit,source_checks:result.evidence.length}));
}
