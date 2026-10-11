export async function guardianApi(path,options={}){
 const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers},signal:AbortSignal.timeout(25000)});
 let data;try{data=await response.json()}catch{throw new Error('Guardian is unavailable. Start the local server and retry.')}
 if(!response.ok){const error=new Error(data.message||data.error||'The request could not be completed.');error.status=response.status;throw error}
 return data;
}
