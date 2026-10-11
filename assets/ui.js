import {mountLocale,setLanguage,getLanguage,locale} from './locale.js';
import {roleIdentity,roleIcon} from './role-ui.js';
// Shared presentation controls. Authentication and school data stay in cloud-app.js.
(() => {
  const names={en:['Admin','Teacher','Staff','Parent','Kid'],hi:['व्यवस्थापक','शिक्षक','कर्मचारी','अभिभावक','बच्चे'],mr:['प्रशासक','शिक्षक','कर्मचारी','पालक','मुले']};
  const tabs={en:{},hi:{today:'आज',plan:'स्कूल योजना',history:'इतिहास',preferences:'सूचनाएं',children:'बाल प्रोफ़ाइल',privacy:'मेरा डेटा',school:'स्कूल सेटिंग',enrollment:'लोग और कक्षाएं',devices:'सेंसर',classes:'कक्षाएं',operations:'योजना और गतिविधि इतिहास'},mr:{today:'आज',plan:'शाळेची योजना',history:'इतिहास',preferences:'सूचना',children:'मुलांची प्रोफाइल',privacy:'माझा डेटा',school:'शाळा सेटिंग',enrollment:'लोक आणि वर्ग',devices:'सेन्सर',classes:'वर्ग',operations:'योजना आणि कृती इतिहास'}};
  const languages={en:'English',hi:'हिन्दी',mr:'मराठी'};
  const roles=['admin','teacher','staff','parent','kid'];
  const home=document.body.classList.contains('home-page');
  const present=new URLSearchParams(location.search).get('present')==='1';
  document.body.dataset.present=String(present);
  const header=document.querySelector('header');
  if(!header)return;
  const icon=path=>`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
  const chevron=icon('m8 10 4 4 4-4');
  const read=key=>{try{return localStorage.getItem(key);}catch{return null;}};
  const save=(key,value)=>{try{localStorage.setItem(key,value);}catch{}};
  let language=getLanguage();if(!names[language])language='en';
  let demo=false,demoTimestamps=true,menuSequence=0,demoTools=null,clockOffset=null;
  const menus=[];
  const sheet=document.createElement('div');sheet.className='topbar-sheet';sheet.id='topbar-sheet';sheet.setAttribute('role','group');sheet.setAttribute('aria-label','Website controls');
  const account=document.querySelector('#account');if(account)sheet.append(account);
  const navigation=header.querySelector('nav[aria-label="Website"]');
  const primary=navigation?.querySelector('.btn-nav');if(primary)primary.remove();
  if(navigation)sheet.append(navigation);
  const controls=document.createElement('div');controls.className='shared-ui-controls';
  controls.setAttribute('role','group');controls.setAttribute('aria-label','Navigation language; school guidance remains in its original language');
  const languageMenu=document.createElement('div');languageMenu.className='topbar-menu language-menu';
  languageMenu.innerHTML=`<button type="button" class="secondary menu-button" title="Choose navigation language; guidance keeps its original wording">${icon('M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3a19 19 0 0 1 0 18 19 19 0 0 1 0-18')}<span data-current-language></span>${chevron}</button><div class="menu-popup" role="menu" aria-label="Navigation language" hidden>${Object.entries(languages).map(([code,name])=>`<button type="button" role="menuitemradio" tabindex="-1" data-language="${code}" lang="${code}">${name}</button>`).join('')}</div>`;
  controls.append(languageMenu);sheet.append(controls);
  const theme=header.querySelector('.theme-toggle');if(theme)controls.append(theme);
  if(primary)sheet.append(primary);
  header.append(sheet);
  const menuButton=document.createElement('button');menuButton.type='button';menuButton.className='secondary topbar-toggle';menuButton.setAttribute('aria-label','Open website menu');menuButton.setAttribute('aria-controls',sheet.id);menuButton.setAttribute('aria-expanded','false');menuButton.innerHTML=icon('M4 6h16 M4 12h16 M4 18h16');header.append(menuButton);
  const mobile=matchMedia('(max-width:1099px)');
  let sheetOpen=false;
  function closeMenus(except){menus.forEach(menu=>{if(menu!==except)menu.close(false);});}
  function setSheet(open,restore=false){
    sheetOpen=Boolean(open&&mobile.matches);sheet.hidden=mobile.matches&&!sheetOpen;
    header.classList.toggle('topbar-open',sheetOpen);menuButton.setAttribute('aria-expanded',String(sheetOpen));
    menuButton.setAttribute('aria-label',sheetOpen?'Close website menu':'Open website menu');
    if(!sheetOpen)closeMenus();
    if(sheetOpen)[...sheet.querySelectorAll('a,button,select')].find(node=>node.getClientRects().length&&!node.disabled)?.focus();
    if(restore)menuButton.focus();
  }
  function installMenu(container){
    const trigger=container.querySelector('.menu-button'),popup=container.querySelector('.menu-popup');
    popup.id=`topbar-menu-${++menuSequence}`;trigger.setAttribute('aria-haspopup','menu');trigger.setAttribute('aria-expanded','false');trigger.setAttribute('aria-controls',popup.id);
    const items=()=>[...popup.querySelectorAll('[role^="menuitem"]')].filter(item=>!item.hidden);
    const menu={container,close(restore=true){popup.hidden=true;trigger.setAttribute('aria-expanded','false');if(restore)trigger.focus();},open(last=false){closeMenus(menu);popup.hidden=false;trigger.setAttribute('aria-expanded','true');const list=items();(last?list.at(-1):list.find(item=>item.getAttribute('aria-checked')==='true'||item.hasAttribute('aria-current'))||list[0])?.focus();}};
    menus.push(menu);
    trigger.addEventListener('click',()=>popup.hidden?menu.open():menu.close());
    trigger.addEventListener('keydown',event=>{if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();menu.open(event.key==='ArrowUp');}});
    popup.addEventListener('keydown',event=>{
      const list=items(),index=list.indexOf(document.activeElement);
      if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?list.length-1:(index+(event.key==='ArrowDown'?1:-1)+list.length)%list.length;list[next]?.focus();}
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();menu.close();}
      if(event.key==='Tab')menu.close();
      // Anchors have native Enter activation; Space activates the same destination.
      if(event.key===' '&&event.target.tagName==='A'){event.preventDefault();event.target.click();}
    });
    container.addEventListener('focusout',event=>{if(!container.contains(event.relatedTarget))menu.close(false);});
    return menu;
  }
  const languageControl=installMenu(languageMenu);
  languageMenu.querySelectorAll('[data-language]').forEach(button=>button.addEventListener('click',()=>{language=button.dataset.language;setLanguage(language);update();languageControl.close();}));
  menuButton.addEventListener('click',()=>setSheet(!sheetOpen));
  mobile.addEventListener('change',()=>setSheet(false));
  document.addEventListener('click',event=>{menus.forEach(menu=>{if(!event.composedPath().includes(menu.container))menu.close(false);});if(sheetOpen&&!event.composedPath().includes(header))setSheet(false);});
  header.addEventListener('keydown',event=>{if(event.key==='Escape'&&sheetOpen){event.preventDefault();setSheet(false,true);}});
  navigation?.addEventListener('click',event=>{const link=event.target.closest('a');if(link){if(link.hash==='#aws-fit')document.querySelector('#aws-fit').open=true;if(mobile.matches)setSheet(false);}});
  function update(){
    languageMenu.querySelector('[data-current-language]').textContent=languages[language];
    languageMenu.querySelector('.menu-button').setAttribute('aria-label',`Navigation language: ${languages[language]}`);
    languageMenu.querySelectorAll('[data-language]').forEach(button=>button.setAttribute('aria-checked',String(button.dataset.language===language)));
    account?.querySelectorAll('.persona-chips').forEach(node=>node.remove());
    if(account){
      const select=account.querySelector('#preview-role');if(select)select.closest('label').hidden=true;
      let roleMenu=account.querySelector('.view-as-menu');
      if(demo&&!home&&!present&&select){
        if(!roleMenu){roleMenu=document.createElement('div');roleMenu.className='topbar-menu view-as-menu';roleMenu.innerHTML=`<button type="button" class="secondary menu-button"><span data-current-role></span>${chevron}</button><div class="menu-popup" role="menu" aria-label="Demo role" hidden>${roles.map(role=>`<a role="menuitem" tabindex="-1" data-role="${role}" href="${'/cloud.html?role='+role}"></a>`).join('')}<button type="button" role="menuitem" tabindex="-1" data-demo-tools hidden>Demo tools…</button></div>`;account.append(roleMenu);const control=installMenu(roleMenu);roleMenu.querySelector('[data-demo-tools]').onclick=()=>{control.close();if(mobile.matches)setSheet(false,true);demoTools?.();};}
        const active=roles.includes(select.value)?select.value:'admin';
        roleMenu.querySelector('[data-current-role]').textContent=`Viewing as: ${names.en[roles.indexOf(active)]}`;
        roleMenu.querySelectorAll('[data-role]').forEach(link=>{const identity=roleIdentity[link.dataset.role];link.innerHTML=roleIcon(link.dataset.role)+'<span><strong>'+names.en[roles.indexOf(link.dataset.role)]+'</strong><small>'+identity.title+'</small></span>';link.dataset.persona=link.dataset.role;link.title=identity.detail;if(link.dataset.role===active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
        roleMenu.querySelector('[data-demo-tools]').hidden=active!=='admin'||!demoTools;
      }else roleMenu?.remove();
    }
    document.querySelectorAll('[data-tab]').forEach(button=>{const label=button.querySelector('span');if(!label)return;if(!label.dataset.originalLabel)label.dataset.originalLabel=label.textContent;label.textContent=label.dataset.originalLabel;});
  }
  function setDemo(value){
    demo=Boolean(value);
    if(demo&&clockOffset===null){
      const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts().map(p=>[p.type,p.value]));
      clockOffset=Date.parse(`${parts.year}-${parts.month}-${parts.day}T07:30:00+05:30`)-Date.now();
    }
    let banner=document.querySelector('.preview-bar');
    if(demo&&!home&&!present&&read('ag-demo-banner-dismissed')!=='1'){
      if(!banner){banner=document.createElement('section');banner.className='preview-bar';}
      banner.dataset.uiDemoBanner='true';banner.setAttribute('aria-label','Demo environment');banner.innerHTML=`<p>Demo workspace. Sample data. No messages are sent.</p><button type="button" title="Dismiss demo banner" aria-label="Dismiss demo banner">${icon('m6 6 12 12 M18 6 6 18')}</button>`;
      header.after(banner);banner.querySelector('button').onclick=()=>{save('ag-demo-banner-dismissed','1');banner.remove();};
    }else banner?.remove();
    update();
  }
  // guardian_rules.py FLAGS, in severity order. Unknown is deliberately neutral.
  const flags=['green','yellow','orange','red'];
  let skySequence=0;
  let skyState={flag:'unknown',demo:false,example:false};
  function skyPartial(id){
    return `<svg class="sky-art" width="1200" height="360" aria-hidden="true" focusable="false">
      <defs><linearGradient id="${id}" x2="0" y2="1"><stop class="sky-top"/><stop class="sky-bottom" offset="1"/></linearGradient></defs>
      <rect width="100%" height="100%" fill="url(#${id})"/>
      <circle class="sky-sun-glow" cx="86%" cy="48" r="46"/><circle class="sky-sun" cx="86%" cy="48" r="24"/>
      <g class="sky-stars">${[8,19,30,44,56,68,78,91].map((x,i)=>`<circle cx="${x}%" cy="${12+(i*19)%58}" r="${i%2?1.2:2}"/>`).join('')}</g>
      <svg class="sky-moon" x="82%" y="30" width="72" height="72" viewBox="1025 30 72 72"><path d="M1064 38a32 32 0 1 0 17 51 29 29 0 0 1-17-51Z"/></svg>
      <svg class="sky-cloud sky-cloud-one" x="5%" y="38" width="160" height="68" viewBox="110 32 160 80"><path d="M134 96c-23 0-23-31 0-32 5-30 47-33 60-9 19-12 46 1 45 22 21 0 24 19 4 19Z"/></svg>
      <svg class="sky-cloud sky-cloud-two" x="40%" y="16" width="160" height="70" viewBox="430 0 150 80"><path d="M461 68c-29 0-29-35-5-39 7-28 43-30 54-7 23-10 45 6 44 22 21 0 25 24 4 24Z"/></svg>
      <svg class="sky-cloud sky-cloud-three" x="75%" y="90" width="170" height="80" viewBox="830 60 170 100"><path d="M868 133c-27 0-28-35-4-39 8-30 49-31 61-6 22-10 49 3 49 22 24 0 24 23 3 23Z"/></svg>
      <rect class="sky-haze" width="100%" height="100%"/>
      <g class="sky-particles">${Array.from({length:30},(_,i)=>`<circle cx="${(i*37+9)%100}%" cy="${24+(i*23)%90}" r="${i%3+1}"/>`).join('')}</g>
      <svg class="skyline-art" x="0" y="100%" width="100%" height="160" viewBox="0 200 1200 160" preserveAspectRatio="xMidYMax meet">
      <g class="sky-city"><path d="M0 339v-34h35v34h45v-56h53v56h244v-33h52v33h211v-45h48v-21h35v66h58v-39h53v39h158v-57h35v-16h44v73h88v-41h41v41h55v-25h45v25Z"/></g>
      <g class="sky-city-mid"><path d="M0 350v-23h70v23h97v-40h38v40h238v-28h60v28h156v-47h45v47h224v-35h72v35h200Z"/></g>
      <g class="sky-trees"><path d="M72 348v-54m40 54v-47m754 47v-41m34 41v-56m217 56v-41"/><circle cx="72" cy="280" r="23"/><circle cx="112" cy="295" r="17"/><circle cx="866" cy="299" r="17"/><circle cx="900" cy="279" r="23"/><circle cx="1117" cy="295" r="19"/></g>
      <g class="sky-school"><path d="M185 345v-57h59v-36h30v36h59v57Z"/><path d="m238 253 21-19 21 19Z"/><path class="sky-pole" d="M259 237v-28"/><path d="M260 208h23l-5 7 5 7h-23Z"/>
        <path class="sky-windows" d="M200 303h12v12h-12Zm23 0h12v12h-12Zm63 0h12v12h-12Zm23 0h12v12h-12ZM250 322h18v23h-18Z"/><path class="sky-bell" d="M255 259h8v10h-8Z"/>
      </g>
      <path class="sky-ground" d="M0 351q125-11 248-4t266 3 268-3 235 1 183-2v14H0Z"/>
      </svg>
    </svg>`;
  }
  let skyHour=7.5;
  function mountSkies(){document.querySelectorAll('[data-sky]').forEach(container=>{if(!container.querySelector('.sky-art'))container.innerHTML=skyPartial(`ag-sky-${++skySequence}`);});setHour(skyHour);}
  function setHour(hour){
    skyHour=Number.isFinite(hour)?Math.max(6,Math.min(18,hour)):7.5;
    const progress=(skyHour-6)/12;
    document.body.dataset.dayLight=skyHour<10?'morning':skyHour<14?'noon':'afternoon';
    document.querySelectorAll('.sky-sun,.sky-sun-glow').forEach(sun=>{sun.setAttribute('cx',`${12+progress*76}%`);sun.setAttribute('cy',String(88-Math.sin(progress*Math.PI)*62));});
  }
  function formatTime(value,{scheduled=false,schoolEvent=false}={}){
    if(!value)return 'Unavailable';
    const ms=typeof value==='number'?value*1000:Date.parse(value);
    if(!Number.isFinite(ms))return 'Unavailable';
    const display=new Date(ms+(demo&&demoTimestamps&&!scheduled?clockOffset||0:0));
    if(demo&&schoolEvent)return new Intl.DateTimeFormat(locale(),{dateStyle:'medium',timeZone:'Asia/Kolkata'}).format(display)+', 07:30 IST';
    return new Intl.DateTimeFormat(locale(),{dateStyle:'medium',timeStyle:'short',...(demo?{timeZone:'Asia/Kolkata'}:{})}).format(display);
  }
  function setFlag(flag,{demo=false,example=false,pm25=null,boundaries=[15,35,60]}={}){
    skyState={flag:flags.includes(flag)?flag:'unknown',demo:Boolean(demo),example:Boolean(example)};
    const rank=flags.indexOf(skyState.flag);document.body.dataset.flag=rank<0?'unknown':String(rank);
    const label=rank<0?`Air flag unavailable. The sky is neutral; ask staff to verify conditions.${demo?' Demo data.':''}`:`${example?'Example sky':'The sky shows today’s air flag'}: ${skyState.flag[0].toUpperCase()+skyState.flag.slice(1)}. ${example?'Not today’s school instruction.':demo?'Demo data.':'School planning guidance.'}`;
    const sceneLabel=!example&&roleIdentity[document.body.dataset.role]?`${roleIdentity[document.body.dataset.role].title} scene · Air flag: ${skyState.flag}. ${demo?'Demo data.':'School planning guidance.'}`:label;
    const intensity=rank<=0?0:Number.isFinite(pm25)?Math.min(.55,Math.max(.08,.15+(pm25-boundaries[0])/(boundaries[2]*2-boundaries[0])*.4)):[0,.15,.32,.55][rank]||0;
    document.body.style.setProperty('--haze-opacity',String(intensity));
    document.querySelectorAll('[data-sky-caption]').forEach(caption=>caption.textContent=caption.closest('.today-banner')?(demo?'Demo data · Haze is illustrative':'School planning guidance · Haze is illustrative'):sceneLabel+' Haze is illustrative.');
    mountSkies();
    document.querySelectorAll('[data-sky]').forEach(sky=>{if(!sky.querySelector('.drifting-haze'))sky.insertAdjacentHTML('beforeend','<div class="drifting-haze" aria-hidden="true"><i></i><i></i><i></i></div>');});
  }
  function decoratePanel(){
    // Small heading icons only; no form, role or content changes.
    document.querySelectorAll('#panel .card h2,#panel .plan-strip h2').forEach(heading=>{
      if(heading.querySelector('.heading-icon'))return;
      const text=heading.textContent.toLowerCase();
      const path=text.includes('source')?'M12 21s7-6 7-12a7 7 0 0 0-14 0c0 6 7 12 7 12 M15 9a3 3 0 1 1-6 0 3 3 0 0 1 6 0':text.includes('step')||text.includes('plan')||text.includes('instruction')?'M9 4h10v17H5V4h4 M9 2h6v4H9z M8 11l2 2 5-5 M8 17h8':text.includes('ahead')||text.includes('weather')?'M12 3v2 M3 12h2 M19 12h2 M5 5l2 2 M17 7l2-2 M8 12a4 4 0 1 1 8 0 M4 20h16 M7 16h10':'M3 4h18v16H3z M3 9h18 M8 4v16';
      const span=document.createElement('span');span.className='heading-icon';span.setAttribute('aria-hidden','true');span.innerHTML=icon(path);heading.prepend(span);
    });
  }
  window.AGRestyle={setDemo,update,setFlag,setHour,mountSkies,decoratePanel,formatTime,setDataMode(mode){demoTimestamps=mode==='demo';},setDemoTools(callback){demoTools=callback;update();}};
  window.addEventListener('hashchange',update);
  mountLocale();
  setSheet(false);setDemo(document.body.dataset.demo==='true');
  setFlag(home?'orange':'unknown',{example:home});
})();
