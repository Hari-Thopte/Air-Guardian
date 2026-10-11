const {test,expect}=require('@playwright/test');
const inside=(a,b)=>a.x>=b.x-.5&&a.y>=b.y-.5&&a.x+a.width<=b.x+b.width+.5&&a.y+a.height<=b.y+b.height+.5;
const overlaps=(a,b)=>Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>1&&Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>1;
for(const width of [390,768,1440])test(`Today banner contains its contents at ${width}px in both themes`,async({page})=>{
  await page.setViewportSize({width,height:900});await page.goto('/cloud.html?role=admin');
  await page.waitForSelector('.today-banner');
  for(const theme of ['light','dark']){
    if(await page.locator('html').getAttribute('data-theme')!==theme){
      if(!await page.locator('.theme-toggle').isVisible())await page.locator('.topbar-toggle').click();
      await page.locator('.theme-toggle').click();
      if(await page.locator('.topbar-toggle').isVisible()&&await page.locator('.topbar-toggle').getAttribute('aria-expanded')==='true')await page.locator('.topbar-toggle').click();
    }
    const banner=await page.locator('.today-banner').boundingBox();
    const elements=await Promise.all(['.banner-card','#refresh'].map(s=>page.locator('.today-banner '+s).boundingBox()));
    for(const box of elements)expect(inside(box,banner)).toBeTruthy();
    for(let i=0;i<elements.length;i++)for(let j=i+1;j<elements.length;j++)expect(overlaps(elements[i],elements[j])).toBeFalsy();
    const content=await page.locator('.school-layout').boundingBox();expect(content.y).toBeGreaterThanOrEqual(banner.y+banner.height);
    expect(Math.abs(banner.y+banner.height/2-(elements[1].y+elements[1].height/2))).toBeLessThan(1);
  }
});
test('landing simulator keeps controls above the fold and role content below them',async({page})=>{
  await page.setViewportSize({width:1440,height:900});await page.goto('/home.html');
  await expect(page.locator('#scenario')).toBeEnabled();
  for(const role of ['admin','teacher','staff','parent','kid']){
    await page.locator('[data-sim-role='+role+']').click();
    const controls=await Promise.all(['#scenario','#day-hour'].map(s=>page.locator(s).boundingBox()));
    for(const box of controls)expect(box.y+box.height).toBeLessThan(900);
    const title=await page.locator('#simulator-role').boundingBox();expect(title.y).toBeGreaterThan(controls[1].y+controls[1].height);
    const chips=await page.locator('[data-sim-role]').evaluateAll(elements=>elements.map(e=>e.getBoundingClientRect().top));
    expect(new Set(chips).size).toBe(1);
    expect(await page.locator('#day-result>h3').count()).toBe(1);
  }
});
