// Cache only validated public service metadata, never addresses or parcel results.
const memory=new Map(),TTL=7*24*3600;
const keyFor=key=>new Request('https://solar-source-cache.invalid/ontario-v1/'+encodeURIComponent(key));
export async function readSourceCache(key){
 const local=memory.get(key);if(local&&local.expires>Date.now())return structuredClone(local.value);
 try{if(typeof caches!=='undefined'){const response=await caches.default.match(keyFor(key));if(response){const record=await response.json();if(record.expires>Date.now()){remember(key,record);return record.value;}}}}catch{/* Cache unavailability never establishes source unavailability. */}
 return null;
}
function remember(key,record){if(memory.size>=128)memory.delete(memory.keys().next().value);memory.set(key,record);}
export async function writeSourceCache(key,value){const record={expires:Date.now()+TTL*1000,value};remember(key,record);try{if(typeof caches!=='undefined')await caches.default.put(keyFor(key),new Response(JSON.stringify(record),{headers:{'Content-Type':'application/json','Cache-Control':'public, max-age='+TTL}}));}catch{/* Per-worker memory remains a bounded fallback. */}}
export async function dropSourceCache(key){memory.delete(key);try{if(typeof caches!=='undefined')await caches.default.delete(keyFor(key));}catch{}}
