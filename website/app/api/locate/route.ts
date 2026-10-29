import {locateOntario} from '../../../lib/parcel-discovery.mjs';
export async function GET(request: Request){
 const params=new URL(request.url).searchParams,address=params.get('address'),selectedIndex=params.has('location')?Number(params.get('location')):null;
 if(params.get('stream')!=='1'){try{return Response.json(await locateOntario(address,{selectedIndex}),{headers:{'Cache-Control':'no-store'}});}catch(error){return Response.json({error:String(error.message)},{status:400});}}
 const encoder=new TextEncoder();const stream=new ReadableStream({async start(controller){
  const emit=data=>controller.enqueue(encoder.encode(JSON.stringify(data)+'\n'));
  try{const result=await locateOntario(address,{selectedIndex,emit});emit({stage:'complete',result});}catch(error){emit({stage:'error',message:String(error.message)});}finally{controller.close();}
 }});
 return new Response(stream,{headers:{'Content-Type':'application/x-ndjson','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
