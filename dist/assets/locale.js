// One catalogue serves UI phrases, engine action codes and server notifications.
export const catalogue=await fetch('/assets/catalogue.json',{cache:'no-cache',signal:AbortSignal.timeout(12000)}).then(async r=>{if(!r.ok)throw new Error('Catalogue unavailable');const data=await r.json();try{localStorage.setItem('ag-public-catalogue',JSON.stringify(data));}catch{}return data;}).catch(()=>{try{const saved=JSON.parse(localStorage.getItem('ag-public-catalogue'));if(saved?.meta?.en&&saved.entries)return saved;}catch{}console.warn('[i18n] Catalogue unavailable; using source English');return {meta:{en:{locale:'en-IN'}},entries:{}};});
let language='en';try{language=localStorage.getItem('ag-ui-language')||'en';}catch{}
if(!catalogue.meta[language])language='en';
export const getLanguage=()=>language;
export const locale=()=>catalogue.meta[language].locale;
export const number=(value,options={})=>new Intl.NumberFormat(locale(),options).format(value);
const warn=new Set();
function missing(key){if(!warn.has(key)&&['127.0.0.1','localhost'].includes(location.hostname)){warn.add(key);console.warn('[i18n] Missing catalogue key:',key);}}
export function t(key,params=[]){
  const entry=catalogue.entries[key];if(!entry){missing(key);return key;}
  const text=entry[language]||entry.en;if(!entry[language])missing(key+'.'+language);
  return text.replace(/\{(\d+)\}/g,(_,n)=>String(params[Number(n)]??''));
}
const escapeRx=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const lookup=new Map(Object.entries(catalogue.entries).map(([key,value])=>[value.en,key]));
const patterns=Object.entries(catalogue.entries).filter(([,v])=>/\{\d+\}/.test(v.en)).map(([key,value])=>({key,
  expression:new RegExp('^'+value.en.split(/\{\d+\}/).map(escapeRx).join('(.+?)')+'$')}));
const fragments=[...lookup.keys()].filter(v=>v.length>5&&!/\{\d+\}/.test(v)).sort((a,b)=>b.length-a.length);
export function translateText(value,depth=0){
  if(language==='en'||!value.trim())return value;
  if(/^\d+(?:\.\d+)?$/.test(value.trim()))return number(Number(value.trim()),{maximumFractionDigits:2});
  const original=value.trim(),key=lookup.get(original);
  let translated;
  if(key)translated=t(key);
  else{
    const match=depth<3?patterns.map(p=>({p,m:original.match(p.expression)})).find(item=>item.m):null;
    if(match)translated=t(match.p.key,match.m.slice(1).map(v=>translateText(v,depth+1)));
    else{
      translated=original;
      // Compound labels keep their dynamic values while all known UI fragments
      // resolve through stable catalogue keys. School-authored wording is excluded.
      for(const fragment of fragments)if(translated.includes(fragment))translated=translated.replace(new RegExp('(?<![A-Za-z])'+escapeRx(fragment)+'(?![A-Za-z])','g'),t(lookup.get(fragment)));
      translated=translated.split(/(\s*[·:→]\s*)/).map(part=>lookup.has(part.trim())?part.replace(part.trim(),t(lookup.get(part.trim()))):part).join('');
      if(translated===original&&/[A-Za-z]{3}/.test(original)&&!/^Air Guardian|^PM|^N95|^KN95|^CPCB|^Open|^NASA|^WhatsApp|^SMS|^Class \d|^Demo School|^Explorer \d|^Child [A-Z]/.test(original))missing('ui.unregistered-'+[...original].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,0).toString(16));
    }
  }
  return value.replace(original,translated);
}
const originals=new WeakMap(),attributeOriginals=new WeakMap();
let observer,queued=false;
export function localizeDom(root=document.body){
  observer?.disconnect();
  document.documentElement.lang=language;
  root.querySelectorAll('[data-i18n]').forEach(element=>{
    const params=JSON.parse(element.dataset.i18nParams||'[]');
    element.textContent=t(element.dataset.i18n,params.map(value=>translateText(String(value))));
  });
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let node;
  while((node=walker.nextNode())){
    if(node.parentElement?.closest('script,style,textarea,[data-original-wording],[data-no-translate],[data-i18n]'))continue;
    let record=originals.get(node);if(!record||node.textContent!==record.rendered)record={original:node.textContent};
    record.rendered=translateText(record.original);if(node.textContent!==record.rendered)node.textContent=record.rendered;originals.set(node,record);
  }
  root.querySelectorAll('[aria-label],[title],[placeholder]').forEach(element=>{
    if(element.closest('[data-original-wording],[data-no-translate]'))return;
    const records=attributeOriginals.get(element)||{};
    for(const attribute of ['aria-label','title','placeholder']){
      if(!element.hasAttribute(attribute))continue;
      let record=records[attribute];if(!record||element.getAttribute(attribute)!==record.rendered)record={original:element.getAttribute(attribute)};
      record.rendered=translateText(record.original);if(element.getAttribute(attribute)!==record.rendered)element.setAttribute(attribute,record.rendered);records[attribute]=record;
    }
    attributeOriginals.set(element,records);
  });
  observer?.observe(document.body,{subtree:true,childList:true,characterData:true});
}
export function setLanguage(value){
  if(!catalogue.meta[value])return;language=value;try{localStorage.setItem('ag-ui-language',value);}catch{}
  localizeDom();window.dispatchEvent(new CustomEvent('ag:language',{detail:value}));
}
export function mountLocale(){
  observer=new MutationObserver(()=>{if(!queued){queued=true;queueMicrotask(()=>{queued=false;localizeDom();});}});
  localizeDom();
  window.AGLocale={t,translateText,getLanguage,number,locale};
}
