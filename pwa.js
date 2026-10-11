let installPrompt;
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;window.dispatchEvent(new Event('guardian-install-ready'))});
export async function installApp(){if(!installPrompt)return 'Use your browser’s install or Add to Home Screen option.';await installPrompt.prompt();const choice=await installPrompt.userChoice;installPrompt=null;return choice.outcome==='accepted'?'Installation requested.':'Installation was dismissed.'}
export function installAvailable(){return Boolean(installPrompt)}
if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
