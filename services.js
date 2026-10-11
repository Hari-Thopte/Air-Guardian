// Public non-commercial Open-Meteo endpoints. No secret API keys in the browser.
export async function fetchRegionalAir(school,signal){
 const base=`latitude=${school.lat}&longitude=${school.lon}&timezone=GMT`;
 const aqUrl=`https://air-quality-api.open-meteo.com/v1/air-quality?${base}&current=us_aqi,pm2_5,pm10,nitrogen_dioxide,ozone,sulphur_dioxide,carbon_monoxide&hourly=us_aqi,pm2_5,pm10&past_days=1&forecast_days=1`;
 const weatherUrl=`https://api.open-meteo.com/v1/forecast?${base}&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m`;
 const responses=await Promise.all([fetch(aqUrl,{signal}),fetch(weatherUrl,{signal})]);
 if(responses.some(r=>!r.ok))throw new Error('The regional data provider is unavailable. Try again later.');
 const [air,weather]=await Promise.all(responses.map(r=>r.json()));
 const a=air.current,w=weather.current;
 if(!a||!Number.isFinite(a.us_aqi)||!a.time)throw new Error('The provider did not return a valid current air-quality estimate.');
 const observedAt=`${a.time}Z`;
 const age=(Date.now()-Date.parse(observedAt))/1000;
 if(!Number.isFinite(age)||age>10800||age< -3600)throw new Error('The provider estimate is too old or has an invalid timestamp. Please check another source.');
 const direction=['N','NE','E','SE','S','SW','W','NW'][Math.round((w?.wind_direction_10m??0)/45)%8];
 const now=Date.parse(observedAt);
 const history=(air.hourly?.time??[]).map((t,i)=>({time:`${t}Z`,aqi:air.hourly.us_aqi[i]})).filter(p=>Date.parse(p.time)<=now&&Date.parse(p.time)>now-86400000&&Number.isFinite(p.aqi));
 return {aqi:Math.round(a.us_aqi),pm25:a.pm2_5,pm10:a.pm10,no2:a.nitrogen_dioxide,o3:a.ozone,so2:a.sulphur_dioxide,co:Number.isFinite(a.carbon_monoxide)?a.carbon_monoxide/1000:null,temp:w?.temperature_2m,humidity:w?.relative_humidity_2m,pressure:w?.surface_pressure,wind:w?.wind_speed_10m,direction,main:null,standard:'US',observedAt,weatherObservedAt:w?.time?`${w.time}Z`:null,history,source:'Open-Meteo / CAMS',coverage:'Regional model · approximately 45 km grid in India',mode:'live'};
}

export function csvDownload(filename,rows){
 const safeCell=v=>{let s=String(v??'');if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};
 const csv='\uFEFF'+rows.map(row=>row.map(safeCell).join(',')).join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
