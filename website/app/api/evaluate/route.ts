import { evaluate } from '../../../lib/assessment.mjs';
export async function POST(request: Request){
 if(request.headers.get('origin')&&request.headers.get('origin')!==new URL(request.url).origin)return Response.json({error:'Same-origin requests required.'},{status:403});
 const raw=await request.text();if(raw.length>70000)return Response.json({error:'Boundary payload too large.'},{status:413});
 let input;try{input=JSON.parse(raw);}catch{return Response.json({error:'Invalid JSON.'},{status:400});}
 const encoder=new TextEncoder();
 const stream=new ReadableStream({async start(controller){const send=(data)=>controller.enqueue(encoder.encode(JSON.stringify(data)+'\n'));try{const report=await evaluate(input,send);send({stage:'complete',report});}catch(error){send({stage:'error',message:String(error.message)});}finally{controller.close();}}});
 return new Response(stream,{headers:{'Content-Type':'application/x-ndjson','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
