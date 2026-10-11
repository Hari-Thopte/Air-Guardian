const {test,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
test('publish, parent review and admin receipt complete the demo',async({page})=>{
  await page.goto('/home.html');await expect(page.locator('h1')).toBeVisible();
  await page.goto('/cloud.html?role=admin#plan');
  await page.waitForSelector('#edit-plan');await page.locator('#edit-plan').click();
  await page.locator('#publish textarea').fill('Demo: review indoor assembly and classroom conditions.');
  await page.locator('#publish button[type="submit"],#publish button').first().click();
  await page.locator('#confirm-publish').click();
  await expect(page.locator('#receipts-panel')).toContainText('Reviews 0 of');
  await page.goto('/cloud.html?role=parent#plan');await page.locator('#review').click();
  await page.goto('/cloud.html?role=admin#plan');
  await expect(page.locator('#receipts-panel')).toContainText('Reviews 1 of');
});
test('landing and Today have no serious or critical axe violations',async({page})=>{
  for(const url of ['/home.html','/cloud.html?role=admin']){
    await page.goto(url);await page.waitForSelector(url.includes('cloud')?'#panel .card':'h1');
    for(const theme of ['light','dark']){
      if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('.theme-toggle').click();
      const results=await new AxeBuilder({page}).analyze();
      expect(results.violations.filter(v=>['serious','critical'].includes(v.impact)).map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,reason:n.failureSummary}))}))).toEqual([]);
    }
  }
});
