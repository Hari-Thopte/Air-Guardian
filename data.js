// Explicit demo fixtures. Never present these values as live school observations.
export const schools = [
  {id:'riverdale',name:'Delhi school campus',area:'New Delhi',city:'Delhi',lat:28.6139,lon:77.2090,demo:true},
  {id:'greenwood',name:'Mumbai school campus',area:'Mumbai, Maharashtra',city:'Mumbai',lat:19.0760,lon:72.8777,demo:true},
  {id:'horizon',name:'South Delhi campus',area:'South Delhi',city:'Delhi',lat:28.5245,lon:77.2066,demo:true}
];
export const readings = {
  good:{aqi:42,pm25:22,pm10:41,temp:27,humidity:52,pressure:1012,wind:14,direction:'NW',main:'PM10'},
  moderate:{aqi:156,pm25:77,pm10:192,temp:29,humidity:64,pressure:1008,wind:8,direction:'NW',main:'PM2.5'},
  poor:{aqi:268,pm25:110,pm10:310,temp:30,humidity:58,pressure:1009,wind:5,direction:'W',main:'PM2.5'},
  severe:{aqi:432,pm25:290,pm10:460,temp:28,humidity:71,pressure:1011,wind:3,direction:'NE',main:'PM2.5'}
};
export const series = {
  '24h':[118,112,121,138,130,145,157,168,162,175,182,174,165,151,143,147,138,149,142,159,169,166,156,156],
  '7d':[112,134,172,160,146,180,156],
  '30d':[98,102,117,119,128,145,151,120,115,111,130,137,146,162,150,144,120,133,143,155,164,177,184,170,166,174,167,162,159,156]
};
export function category(aqi,standard='India'){
  if(standard==='US'){
    if(!Number.isFinite(aqi)||aqi<0)return {label:'Unavailable',tone:'unknown'};
    if(aqi<=50)return {label:'Good',tone:'good'};
    if(aqi<=100)return {label:'Moderate',tone:'moderate'};
    if(aqi<=150)return {label:'Unhealthy for sensitive groups',tone:'warning'};
    if(aqi<=200)return {label:'Unhealthy',tone:'poor'};
    if(aqi<=300)return {label:'Very unhealthy',tone:'severe'};
    return {label:'Hazardous',tone:'severe'};
  }
  if(!Number.isFinite(aqi)||aqi<0||aqi>500)return {label:'Unavailable',tone:''};
  if(aqi<=50)return {label:'Good',tone:'good'};
  if(aqi<=100)return {label:'Satisfactory',tone:'good'};
  if(aqi<=200)return {label:'Moderate',tone:''};
  if(aqi<=300)return {label:'Poor',tone:'poor'};
  if(aqi<=400)return {label:'Very poor',tone:'poor'};
  return {label:'Severe',tone:'poor'};
}
export function guidance(aqi,caution=false,standard='India'){
  if(standard==='US'){
    if(!Number.isFinite(aqi)||aqi<0)return guidance(NaN);
    if(aqi>150||(caution&&aqi>100))return {title:'Bring the activities indoors.',description:'Review indoor alternatives for long or vigorous outdoor activities. These suggestions use the US AQI scale; staff should apply local school policy.',kid:'Ask your teacher about indoor games today.',indoor:true,actions:['Review indoor alternatives for assembly and PE','Check indoor air and ventilation conditions','Follow existing care plans and local guidance']};
    if(aqi>100)return {title:'Keep outdoor activity gentle.',description:'Children and other sensitive groups should review the length and intensity of outdoor activities. Staff should follow local guidance.',kid:'Ask your teacher before long or energetic outdoor games.',indoor:false,actions:['Review long or vigorous outdoor sessions','Give extra attention to existing care plans','Check the school’s latest activity plan']};
    return {title:'Review the usual school plan.',description:'Recheck conditions before outdoor activities and continue following existing care plans.',kid:'Check your school plan with a teacher before heading outside.',indoor:false,actions:['Recheck conditions before outdoor activities','Keep following existing care plans','Look for school notices if conditions change']};
  }
  if(!Number.isFinite(aqi)||aqi<0||aqi>500)return {title:'Check the latest school notice.',description:'Valid air quality data is unavailable. No activity clearance can be given.',kid:'Ask an adult to check your school’s latest notice.',indoor:true,actions:['Ask staff to verify current conditions','Follow the school’s existing guidance']};
  if(aqi>200 || (caution&&aqi>100))return {title:'Bring the activities indoors.',description:'The sample school policy suggests moving assembly and vigorous outdoor activities indoors. Staff should review the plan before confirming.',kid:'Your school may choose indoor games today. Check the plan with your teacher.',indoor:true,actions:['Review indoor alternatives for assembly and PE','Check indoor air and ventilation conditions','Follow the school’s instructions and existing care plans']};
  if(aqi>100)return {title:'A little less time outdoors.',description:'Keep outdoor activities gentle and review longer sessions. Give extra attention to children who need an existing care plan.',kid:'Keep outdoor games gentle today, and check with your teacher before a long sports session.',indoor:false,actions:['Review the intensity and length of outdoor play','Check the latest school update before leaving','Tell a trusted adult if you feel unwell']};
  return {title:'A good day to follow the usual plan.',description:'The sample reading supports reviewing the usual activity schedule. Recheck conditions before longer outdoor sessions.',kid:'Check with your teacher, then enjoy your usual school activities.',indoor:false,actions:['Recheck air quality before outdoor activities','Keep following any existing care plan','Look for updates if conditions change']};
}
