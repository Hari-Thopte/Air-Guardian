const {test,expect}=require('@playwright/test');
const scenarios=['green','yellow','orange','red','stale'];
const flags={green:'green',yellow:'yellow',orange:'orange',red:'red',stale:'unknown'};
const codes={green:'usual',yellow:'gentle',orange:'indoor-pe',red:'indoor-pe',stale:'verify'};
const headlines={green:'Keep the usual school timetable',yellow:'Shorter, gentler outdoor activities',orange:'Move PE and assembly indoors',red:'Move PE and assembly indoors',stale:'Verify conditions before outdoor activities'};
const inside=(a,b)=>a.x>=b.x-.5&&a.y>=b.y-.5&&a.x+a.width<=b.x+b.width+.5&&a.y+a.height<=b.y+b.height+.5;
const overlaps=(a,b)=>Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>1&&Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>1;
async function theme(page,value){
  if(await page.locator('html').getAttribute('data-theme')===value)return;
  if(!await page.locator('.theme-toggle').isVisible())await page.locator('.topbar-toggle').click();
  await page.locator('.theme-toggle').click();
  if(await page.locator('.topbar-toggle').isVisible()&&await page.locator('.topbar-toggle').getAttribute('aria-expanded')==='true')await page.locator('.topbar-toggle').click();
}
async function separate(page,selectors){
  const boxes=await Promise.all(selectors.map(s=>page.locator(s).boundingBox()));
  boxes.forEach(box=>expect(box).not.toBeNull());
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++)expect(overlaps(boxes[i],boxes[j]),`${selectors[i]} overlaps ${selectors[j]}`).toBeFalsy();
}
test('Demo tools switches Red → Green → Yellow → Orange → Stale without retained flags',async({page})=>{
  await page.goto('/cloud.html?role=admin');await page.waitForSelector('.current-air');
  for(const scenario of ['red','green','yellow','orange','stale']){
    await page.locator('.view-as-menu .menu-button').click();await page.locator('[data-demo-tools]').click();
    await page.locator('#demo-scenario').selectOption(scenario);await expect(page.locator('#demo-scenario')).toHaveCount(0);
    await expect(page.locator('.current-air>.badge')).toHaveText(flags[scenario]);
    await expect(page.locator('.current-air h2')).toContainText(headlines[scenario]);
    await expect(page.locator('.banner-card h1')).toHaveText(headlines[scenario]);
    await expect(page.locator('#receipts-panel')).toContainText('Reviews 0 of');
    await expect(page.locator('body')).toHaveAttribute('data-flag',scenario==='stale'?'unknown':String(scenarios.indexOf(scenario)));
  }
});
for(const width of [390,768,1440])for(const scenario of scenarios)for(const screen of ['cloud','home'])for(const mode of ['light','dark']){
  test(`${screen} ${scenario} ${width}px ${mode} visual regression`,async({page,request})=>{
    await page.setViewportSize({width,height:900});
    if(screen==='cloud'){
      const r=await request.post('/v1/demo/scenario',{headers:{Origin:'http://127.0.0.1:5187','X-Preview-Role':'admin'},data:{scenario}});expect(r.ok()).toBeTruthy();
    }
    await page.goto(screen==='cloud'?'/cloud.html?role=admin':'/home.html');
    if(screen==='cloud')await page.waitForSelector('.current-air');
    else {await expect(page.locator('#scenario')).toBeEnabled();await page.locator('#scenario').selectOption(scenario==='stale'?'stale reading':scenario);}
    await theme(page,mode);await page.evaluate(()=>document.fonts.ready);
    const options={animations:'disabled',maxDiffPixelRatio:.005};
    if(screen==='cloud'){
      const banner=await page.locator('.today-banner').boundingBox(),card=await page.locator('.banner-card').boundingBox();expect(inside(card,banner)).toBeTruthy();
      await separate(page,['.banner-card','#refresh']);
      await separate(page,['.gauge-face','.gauge-readout']);
      const below=await page.locator('.school-layout').boundingBox();expect(below.y).toBeGreaterThanOrEqual(banner.y+banner.height);
      // Screenshot the visible decision area, including the banner, sidebar and gauge.
      // Only retrieval timestamps are masked, leaving the reading and labels visible.
      options.mask=[page.locator('.reading-evidence>div:nth-child(2)')];
      await expect(page).toHaveScreenshot(`cloud-${scenario}-${width}-${mode}.png`,options);
    }else{
      await separate(page,['.instrument-sky','.simulator-roles','#scenario','#day-hour','#day-result>.badge','#simulator-role']);
      await expect(page.locator('#day-result>h3')).toHaveAttribute('data-action-code',codes[scenario]);
      await expect(page.locator('.landing-grid')).toHaveScreenshot(`home-${scenario}-${width}-${mode}.png`,options);
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  });
}
