const {test,expect}=require('@playwright/test');
const cases=[['red','red','indoor-pe'],['green','green','usual'],['yellow','yellow','gentle'],['orange','orange','indoor-pe'],['stale','unknown','verify']];
async function select(request,scenario){
  const r=await request.post('/v1/demo/scenario',{headers:{Origin:'http://127.0.0.1:5187','X-Preview-Role':'admin'},data:{scenario}});
  expect(r.ok()).toBeTruthy();
}
test('manual Red → Green → Yellow → Orange → Stale updates every role',async({page,request})=>{
  for(const [scenario,flag,code] of cases){
    await select(request,scenario);
    for(const role of ['admin','teacher','staff','parent','kid']){
      await page.goto('/cloud.html?role='+role);
      await expect(page.locator('body')).toHaveAttribute('data-flag',String(['green','yellow','orange','red'].indexOf(flag)).replace('-1','unknown'));
      await expect(page.locator('#content .badge').first()).toHaveClass(new RegExp(flag));
      const heading=role==='kid'?page.locator('.kid-workspace h1'):page.locator('.current-air h2');
      const expected=role==='staff'&&flag==='red'?'rotate':code;
      await expect(heading).toHaveAttribute('data-action-code',expected);
      await expect(heading).toContainText({usual:role==='kid'?'planned':'usual',gentle:role==='kid'?'shorter':'gentler','indoor-pe':'indoors',rotate:'Rotate',verify:role==='kid'?'grown-up':'Verify'}[expected],{ignoreCase:true});
    }
  }
});
test('landing scenarios update flag, headline and sky for every role',async({page})=>{
  
  await page.goto('/home.html');await expect(page.locator('#scenario')).toBeEnabled();
  for(const [scenario,flag,code] of cases){
    await page.locator('#scenario').selectOption(scenario==='stale'?'stale reading':scenario);
    for(const role of ['admin','teacher','staff','parent','kid']){
      await page.locator('[data-sim-role='+role+']').click();
      await expect(page.locator('#day-result>.badge')).toHaveClass(new RegExp(flag));
      await expect(page.locator('#day-result>h3')).toHaveAttribute('data-action-code',code);
      await expect(page.locator('body')).toHaveAttribute('data-flag',String(['green','yellow','orange','red'].indexOf(flag)).replace('-1','unknown'));
    }
  }
});


