const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'./tests/browser',timeout:30000,workers:1,snapshotPathTemplate:'{testDir}/{testFilePath}-snapshots/{arg}{ext}',use:{baseURL:process.env.AG_PREVIEW_URL||'http://127.0.0.1:5187',headless:true},reporter:'list'});
