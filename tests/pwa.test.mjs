import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
test('first service-worker claim does not reload; an accepted update reloads once',async()=>{
  let onControllerChange,button,reloads=0,activations=0;
  const registration={waiting:{postMessage(){activations++;}},addEventListener(){}};
  const context={navigator:{serviceWorker:{register:async()=>registration,addEventListener(type,fn){if(type==='controllerchange')onControllerChange=fn;}}},document:{createElement:()=>({}),querySelector:()=>({prepend(value){button=value;}})},location:{reload(){reloads++;}}};
  vm.runInNewContext(await readFile(new URL('../assets/pwa-upgrade.js',import.meta.url),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  onControllerChange();assert.equal(reloads,0);
  button.onclick();assert.equal(activations,1);
  onControllerChange();onControllerChange();assert.equal(reloads,1);
});
