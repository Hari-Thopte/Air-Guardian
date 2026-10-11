// Retry idempotent reads only. Never repeat publications or receipts automatically.
export async function resilientFetch(url,options={}){
  const attempts=(options.method||'GET')==='GET'?3:1;
  for(let attempt=0;attempt<attempts;attempt++){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(url,{...options,signal:controller.signal});
      if(response.status<500||attempt===attempts-1)return response;
    }catch(error){if(attempt===attempts-1)throw error;}
    finally{clearTimeout(timeout);}
    await new Promise(resolve=>setTimeout(resolve,400*2**attempt));
  }
}
