// This public learning example collects no child information and makes no air reading.
const feedback = document.querySelector('#game-feedback');
const readButton=document.querySelector('#read-aloud');
if(readButton){
  if(!('speechSynthesis' in window)){readButton.disabled=true;readButton.title='Read aloud is unavailable in this browser. Read the short instructions with an adult.';}
  else{
    const reset=()=>{readButton.textContent='Read aloud';readButton.setAttribute('aria-pressed','false');};
    readButton.onclick=()=>{
      if(readButton.getAttribute('aria-pressed')==='true'){speechSynthesis.cancel();reset();return;}
      const spoken=new SpeechSynthesisUtterance('Read the school plan with a grown-up. Ask your teacher where your class will play. Tell an adult if you feel unwell. Your school says indoor play today. What would you do? Ask your teacher what is planned.');
      spoken.lang='en-IN';spoken.rate=.9;spoken.onend=reset;spoken.onerror=reset;
      speechSynthesis.cancel();speechSynthesis.speak(spoken);readButton.textContent='Stop reading';readButton.setAttribute('aria-pressed','true');
    };
    window.addEventListener('pagehide',()=>speechSynthesis.cancel());
  }
}
document.querySelectorAll('[data-answer]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-answer]').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
    const correct = button.dataset.answer === 'ask';
    feedback.textContent = correct
      ? 'That’s a thoughtful choice! Your teacher can explain today’s activities and the school plan.'
      : 'Try asking your teacher first. They know the school’s plan, including where your class will play.';
    feedback.dataset.result = correct ? 'correct' : 'retry';
  });
});

// The public cloud site has no unauthenticated school/area lookup endpoint.
// Give a useful next step without fabricating a current reading or storing queries.
document.querySelector('#search').addEventListener('submit', event => {
  event.preventDefault();
  const input = document.querySelector('#q');
  if (!input.value.trim()) {
    input.setCustomValidity('Enter a school or area.');
    input.reportValidity();
    return;
  }
  input.setCustomValidity('');
  document.querySelector('#search-result').hidden = false;
});
document.querySelector('#q').addEventListener('input', event => {
  event.target.setCustomValidity('');
  document.querySelector('#search-result').hidden = true;
});
