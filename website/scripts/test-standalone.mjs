// Offline HTTP checks for the portable adapter; no public data sources are queried.
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {server} from '../standalone-server.mjs';

server.listen(0,'127.0.0.1');
await once(server,'listening');
const base='http://127.0.0.1:'+server.address().port;
const nativeFetch=globalThis.fetch;
globalThis.fetch=(url,options)=>{
 const target=new URL(url);
 assert.equal(target.origin,base,'Offline adapter checks must not query public sources.');
 return nativeFetch(url,options);
};
try{
 const root=await fetch(base+'/',{redirect:'manual'});
 assert.equal(root.status,302);assert.equal(root.headers.get('location'),'/solar/');
 const page=await fetch(base+'/solar/');assert.equal(page.status,200);assert.match(await page.text(),/Ontario Solar/);
 for(const [path,type] of [['styles.css','text/css'],['workflow.js','text/javascript'],['geometry.mjs','text/javascript'],['assets/solar-farm-photo.webp','image/webp']]){
  const result=await fetch(base+'/solar/'+path);assert.equal(result.status,200);assert.match(result.headers.get('content-type'),new RegExp(type));await result.arrayBuffer();
 }
 assert.equal((await fetch(base+'/solar/styles.css',{method:'HEAD'})).status,200);
 assert.equal((await fetch(base+'/.openai/hosting.json')).status,404);
 assert.equal((await fetch(base+'/%2e%2e%5cpackage.json')).status,404);
 assert.equal((await fetch(base+'/api/locate',{method:'POST'})).status,405);
 assert.equal((await fetch(base+'/api/evaluate')).status,405);
 assert.equal((await fetch(base+'/api/evaluate',{method:'POST',headers:{Origin:'https://example.invalid'},body:'{}'})).status,403);
 assert.equal((await fetch(base+'/api/evaluate',{method:'POST',body:'invalid'})).status,400);
 assert.equal((await fetch(base+'/api/evaluate',{method:'POST',body:'x'.repeat(70001)})).status,413);
 const invalid=await fetch(base+'/api/evaluate',{method:'POST',body:JSON.stringify({address:'Offline test',geometry:{type:'Point',coordinates:[-81,44]}})});
 assert.match(invalid.headers.get('content-type'),/application\/x-ndjson/);
 const records=(await invalid.text()).trim().split('\n').map(line=>JSON.parse(line));
 assert.equal(records.at(-1).stage,'error');
 console.log('Standalone HTTP checks passed: UI, assets, route isolation, methods, origin, body limits and streamed validation errors.');
}finally{
 globalThis.fetch=nativeFetch;
 await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));
}
