const {test,expect}=require('@playwright/test');
const forbidden=['Current school planning priority','Suggested change.','Plan reviews','Reviews ','Waiting','Reviewed','Planning bands, not official AQI','Observation:','Successful retrieval:','Draft a revision','Refresh','Daily','Messages','Insights','Setup','Notification limits','classes confirmed','awaiting class check','Class 3 A teacher','Class 4 B teacher','Class 5 C teacher','Verify conditions before outdoor activities','Keep the usual school timetable','Shorter, gentler outdoor activities'];
for(const language of ['hi','mr'])test(`${language} covers Today, School plan, Classes and Notifications`,async({page})=>{
  await page.goto('/cloud.html?role=admin');
  await page.waitForSelector('[data-tab="today"]');
  await page.locator('.language-menu .menu-button').click();
  await page.locator(`[data-language="${language}"]`).click();
  await expect(page.locator('html')).toHaveAttribute('lang',language);
  for(const screen of ['today','plan','classes','preferences']){
    await page.locator(`[data-tab="${screen}"]`).click();
    await expect(page.locator('#panel')).not.toBeEmpty();
    // Published school-authored wording is preserved and is not a UI label.
    const text=await page.locator('body').innerText();
    for(const phrase of forbidden)expect(text,`${screen}: ${phrase}`).not.toContain(phrase);
  }
});
for(const width of [390,768,1440])test(`role pages fit ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  for(const role of ['admin','teacher','staff','parent','kid']){
    await page.goto('/cloud.html?role='+role);await page.waitForSelector('#content .card');
    await expect(page.locator('#content')).not.toBeEmpty();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
    await page.screenshot({path:`.test-output/${role}-${width}.png`});
  }
});
