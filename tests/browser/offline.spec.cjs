const {test,expect}=require('@playwright/test');
test('failed reads retain labelled session-memory plan and block review',async({page})=>{
  await page.goto('/cloud.html?role=parent');await page.waitForSelector('[data-role-review]');
  await page.route('**/v1/schools/*/workspace',route=>route.fulfill({status:503,contentType:'application/json',body:'{"message":"Service unavailable"}'}));
  await page.locator('#refresh').click();
  await expect(page.locator('#content .notice')).toContainText('Offline · last known plan',{timeout:15000});
  await expect(page.locator('[data-role-review]')).toBeDisabled();
  await page.locator('[data-tab="plan"]').click();
  await expect(page.locator('#content .notice')).toContainText('Offline · last known plan');
  await expect(page.locator('#review')).toBeDisabled();
});
test('lost authorization clears the previous private workspace',async({page})=>{
  await page.goto('/cloud.html?role=parent');await page.waitForSelector('[data-role-review]');
  await page.route('**/v1/schools/*/workspace',route=>route.fulfill({status:403,contentType:'application/json',body:'{"message":"Membership denied"}'}));
  await page.locator('#refresh').click();
  await expect(page.locator('#content')).toContainText('Current school information is unavailable');
  await expect(page.locator('.role-child-list')).toHaveCount(0);
});
