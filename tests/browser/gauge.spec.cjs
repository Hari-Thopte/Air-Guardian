const {test,expect}=require('@playwright/test');
for(const width of [390,768,1440])test(`gauge parts do not overlap at ${width}px for all sample concentrations`,async({page})=>{
  await page.setViewportSize({width,height:900});await page.goto('/cloud.html?role=admin');await page.waitForSelector('.planning-gauge');
  for(const value of [8,30,45,113,150]){
    // Exercise the shared component in its real dashboard container; not an API reading.
    await page.evaluate(async value=>{const {gauge}=await import('/assets/day-ui.js');document.querySelector('.planning-gauge').outerHTML=gauge(value,[15,35,60]);},value);
    const face=await page.locator('.gauge-face').boundingBox(),readout=await page.locator('.gauge-readout').boundingBox();
    expect(face.x+face.width).toBeLessThanOrEqual(readout.x);
    const svg=await page.locator('.gauge-face svg').boundingBox();expect(svg.width).toBeLessThanOrEqual(face.width+.5);
    const size=await page.locator('.gauge-readout small').evaluate(e=>parseFloat(getComputedStyle(e).fontSize));expect(size).toBeGreaterThanOrEqual(13);
    const needle=await page.locator('path.needle').getAttribute('d');const coords=needle.match(/L([\d.]+) ([\d.]+)/).slice(1).map(Number);
    const angle=Math.PI*(1-value/150);expect(coords[0]).toBeCloseTo(100+72*Math.cos(angle),5);expect(coords[1]).toBeCloseTo(100-72*Math.sin(angle),5);
    for(const flag of ['green','yellow','orange','red'])await expect(page.locator('.gauge-band.'+flag)).toHaveCount(1);
  }
});
