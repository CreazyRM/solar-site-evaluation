// Dependency-free Node adapter for the same public UI and assessment modules.
import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,sep,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {locateOntario} from './lib/parcel-discovery.mjs';
import {evaluate} from './lib/assessment.mjs';

const publicRoot=resolve(fileURLToPath(new URL('./public/',import.meta.url)));
const host=process.env.HOST||'127.0.0.1',port=Number(process.env.PORT||3000);
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.ico':'image/x-icon','.woff2':'font/woff2'};
function sendJSON(response,value,status=200){response.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});response.end(JSON.stringify(value));}
async function stream(response,run){response.writeHead(200,{'Content-Type':'application/x-ndjson; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});const emit=data=>{if(!response.destroyed)response.write(JSON.stringify(data)+'\n');};try{await run(emit);}catch(error){emit({stage:'error',message:String(error.message)});}finally{response.end();}}
async function bodyJSON(request){let size=0;const chunks=[];for await(const part of request){size+=part.length;if(size>70000)throw Object.assign(Error('Boundary payload too large.'),{status:413});chunks.push(part);}try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Object.assign(Error('Invalid JSON.'),{status:400});}}

export const server=createServer(async(request,response)=>{
 try{
  const url=new URL(request.url,'http://localhost');
  if(url.pathname==='/api/locate'){
   if(request.method!=='GET')return sendJSON(response,{error:'GET required.'},405);
   const selectedIndex=url.searchParams.has('location')?Number(url.searchParams.get('location')):null;
   if(url.searchParams.get('stream')==='1')return stream(response,async emit=>{const result=await locateOntario(url.searchParams.get('address'),{emit,selectedIndex});emit({stage:'complete',result});});
   return sendJSON(response,await locateOntario(url.searchParams.get('address'),{selectedIndex}));
  }
  if(url.pathname==='/api/evaluate'){
   if(request.method!=='POST')return sendJSON(response,{error:'POST required.'},405);
   const origin=request.headers.origin;
   if(origin&&new URL(origin).host!==request.headers.host)return sendJSON(response,{error:'Same-origin requests required.'},403);
   const input=await bodyJSON(request);
   return stream(response,async emit=>{const report=await evaluate(input,emit);emit({stage:'complete',report});});
  }
  if(!['GET','HEAD'].includes(request.method))return sendJSON(response,{error:'Method not allowed.'},405);
  if(url.pathname==='/'){response.writeHead(302,{Location:'/solar/'});return response.end();}
  let pathname;try{pathname=decodeURIComponent(url.pathname);}catch{return sendJSON(response,{error:'Invalid path.'},400);}
  if(pathname.includes('\0'))return sendJSON(response,{error:'Invalid path.'},400);
  let path=resolve(publicRoot,'.'+pathname);if(path!==publicRoot&&!path.startsWith(publicRoot+sep))return sendJSON(response,{error:'Not found.'},404);
  try{if((await stat(path)).isDirectory())path=resolve(path,'index.html');const data=await readFile(path);response.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Cache-Control':'no-cache'});response.end(request.method==='HEAD'?undefined:data);}catch(error){if(['ENOENT','ENOTDIR','EISDIR'].includes(error.code))return sendJSON(response,{error:'Not found.'},404);throw error;}
 }catch(error){if(response.headersSent)return response.end();sendJSON(response,{error:String(error.message)},error.status||400);}
});

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 server.listen(port,host,()=>console.log('Solar Atlas: http://'+host+':'+server.address().port+'/solar/'));
 for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>process.exit(0)));
}
