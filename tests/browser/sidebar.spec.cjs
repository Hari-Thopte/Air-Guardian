const {test,expect}=require('@playwright/test');
const inside=(a,b)=>a.x>=b.x-.5&&a.y>=b.y-.5&&a.x+a.width<=b.x+b.width+.5&&a.y+a.height<=b.y+b.height+.5;
const overlaps=(a,b)=>Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>1&&Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>1;
for(const language of ['en','hi','mr'])for(const width of [390,768,1440])test(`${language} sidebar rows and translated geometry at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  await page.addInitScript(lang=>localStorage.setItem('ag-ui-language',lang),language);
  for(const role of ['admin','teacher','staff','parent']){
    await page.goto('/cloud.html?role='+role);
    await expect(page.locator('.school-nav')).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('lang',language);
    if(await page.locator('.topbar-toggle').isVisible()&&await page.locator('.topbar-toggle').getAttribute('aria-expanded')==='true')await page.locator('.topbar-toggle').click();
    for(const theme of ['light','dark']){
      if(await page.locator('html').getAttribute('data-theme')!==theme){
        if(!await page.locator('.theme-toggle').isVisible())await page.locator('.topbar-toggle').click();
        await page.locator('.theme-toggle').click();
        if(await page.locator('.topbar-toggle').isVisible())await page.locator('.topbar-toggle').click();
      }
      const nav=page.locator('.school-nav'),navBox=await nav.boundingBox();
      const items=await nav.locator('button,a').all();
      const boxes=await Promise.all(items.map(item=>item.boundingBox()));
      for(const heading of await nav.locator('.nav-group-label').all()){
        const box=await heading.boundingBox();expect(box).not.toBeNull();expect(inside(box,navBox)).toBeTruthy();
        for(const item of boxes)expect(Math.min(box.y+box.height,item.y+item.height)-Math.max(box.y,item.y)).toBeLessThanOrEqual(.5);
        const semantics=await heading.evaluate(el=>({tag:el.tagName,tabIndex:el.tabIndex,editable:el.isContentEditable,interactive:el.matches('a,button,input,select,textarea,[role="button"],[role="link"]'),cursor:getComputedStyle(el).cursor,lineHeight:parseFloat(getComputedStyle(el).lineHeight)/parseFloat(getComputedStyle(el).fontSize),next:el.nextElementSibling?.hasAttribute('data-tab')}));
        expect(semantics.tag).toBe('P');expect(semantics.tabIndex).toBe(-1);expect(semantics.interactive||semantics.editable).toBeFalsy();expect(semantics.cursor).toBe('default');expect(semantics.lineHeight).toBeGreaterThanOrEqual(1.59);expect(semantics.next).toBeTruthy();
      }
      for(const box of boxes){expect(inside(box,navBox)).toBeTruthy();expect(Math.abs(box.width-navBox.width)).toBeLessThan(1);}
      const active=await nav.locator('[aria-current="page"]').boundingBox();expect(Math.abs(active.width-navBox.width)).toBeLessThan(1);
      const banner=await page.locator('.today-banner').boundingBox(),card=await page.locator('.banner-card').boundingBox(),refresh=await page.locator('#refresh').boundingBox();
      expect(inside(card,banner)).toBeTruthy();expect(inside(refresh,banner)).toBeTruthy();expect(overlaps(card,refresh)).toBeFalsy();
      const face=await page.locator('.gauge-face').boundingBox(),readout=await page.locator('.gauge-readout').boundingBox();expect(overlaps(face,readout)).toBeFalsy();
      for(const caption of await page.locator('.gauge-readout>*').all())expect(overlaps(face,await caption.boundingBox())).toBeFalsy();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
      if(role==='admin'&&theme==='light'){
        await nav.screenshot({path:`.test-output/sidebar-${language}-${width}.png`});
        if(width===1440){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`.test-output/sidebar-page-${language}.png`});}
      }
    }
    if(role==='admin'){
      const labels=page.locator('[data-i18n="review.classTeacher"]');await expect(labels.first()).toHaveText(({en:'Class 3 A teacher',hi:'कक्षा 3 A शिक्षक',mr:'वर्ग 3 A शिक्षक'})[language]);
      await page.locator('[data-tab="plan"]').click();await expect(page.locator('[data-i18n="review.classTeacher"]').first()).toHaveText(({en:'Class 3 A teacher',hi:'कक्षा 3 A शिक्षक',mr:'वर्ग 3 A शिक्षक'})[language]);
    }
  }
});
