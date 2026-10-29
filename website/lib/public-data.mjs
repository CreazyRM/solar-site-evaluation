export async function publicJSON(url,params={},post=false){
 for(let n=0;n<2;n++){
  try{const form=new URLSearchParams(Object.entries(params).map(([k,v])=>[k,String(v)]));
   const response=await fetch(post?url:url+'?'+form,{method:post?'POST':'GET',body:post?form:undefined,signal:AbortSignal.timeout(12000),headers:{Accept:'application/json'}});
   if(!response.ok)throw Error(response.status===401?'authentication_required':response.status===403?'access_denied':`http_${response.status}`);
   const text=await response.text();if(text.length>8_000_000)throw Error('response_too_large');const data=JSON.parse(text);
   if(data?.error)throw Error([498,499,401].includes(data.error.code)?'authentication_required':'source_service_error');
   return{data,source:url,retrieved_at:new Date().toISOString()};
  }catch(error){if(n===0&&['TimeoutError','AbortError'].includes(error.name))continue;throw error;}
 }
}
