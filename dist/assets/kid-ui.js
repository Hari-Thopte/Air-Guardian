import {escape} from './day-ui.js';
import {t,translateText,getLanguage,locale,localizeDom} from './locale.js';

export function kidView(w){
  const panel=document.querySelector('#content');
  const action=t('kid.action.'+w.kid.actionCode);
  panel.innerHTML=`<section class="card kid-workspace"><p class="eyebrow">Air Explorer</p><img class="kid-mascot" src="/assets/guardian-emblem-2x.webp" width="240" height="150" alt=""><h1 data-action-code="${escape(w.kid.actionCode)}">${escape(action)}</h1><span class="badge ${escape(w.kid.flag)}">${escape(w.kid.flag)}</span><p class="kid-instruction">${escape(action)}</p><p>Tell an adult if you feel unwell.</p><button class="secondary" id="kid-read">Read aloud</button><section class="kid-question"><h2>${escape(t(w.kid.questionCode))}</h2><p>Example only. Follow your teacher’s actual instruction.</p><div class="row"><button data-kid-answer="ask">Ask my teacher what’s planned</button><button class="secondary" data-kid-answer="guess">Choose outdoor play on my own</button></div><p id="kid-feedback" role="status" aria-live="polite"></p><span class="kid-sticker" hidden aria-hidden="true">★</span></section><a href="/home.html">Back to home</a></section>`;
  panel.querySelectorAll('[data-kid-answer]').forEach(button=>button.onclick=()=>{
    const correct=button.dataset.kidAnswer==='ask';
    document.querySelector('#kid-feedback').textContent=translateText(correct?'You earned an Air Explorer sticker!':'Ask your teacher first. They know the school plan.');
    panel.querySelector('.kid-sticker').hidden=!correct;
  });
  const read=panel.querySelector('#kid-read');
  if(!('speechSynthesis' in window)){read.disabled=true;read.title=translateText('Read aloud is unavailable in this browser.');}
  else read.onclick=()=>{
    speechSynthesis.cancel();const speech=new SpeechSynthesisUtterance(action+' '+translateText('Tell an adult if you feel unwell.'));
    speech.lang=locale();speech.rate=.85;
    const voice=speechSynthesis.getVoices().find(v=>v.lang===locale())||speechSynthesis.getVoices().find(v=>v.lang.startsWith(getLanguage()));
    if(voice)speech.voice=voice;
    speechSynthesis.speak(speech);
  };
  localizeDom();
}
