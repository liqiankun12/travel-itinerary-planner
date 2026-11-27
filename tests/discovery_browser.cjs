const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const assert = require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'travel-ui-'));
const backend=spawn(path.join(root,'backend/.venv/Scripts/python.exe'),['-c',"import os;from pathlib import Path;import main,uvicorn;main.DB=Path(os.environ['TRAVEL_TEST_DB']);uvicorn.run(main.app,host='127.0.0.1',port=18000,log_level='error')"],{cwd:path.join(root,'backend'),env:{...process.env,TRAVEL_TEST_DB:path.join(folder,'test.db')},windowsHide:true,stdio:'ignore'});
const vite=spawn(process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','18174','--strictPort'],{cwd:path.join(root,'frontend'),windowsHide:true,stdio:'ignore'});
let browser;
async function ready(url){for(let i=0;i<100;i++){try{if((await fetch(url)).ok)return}catch{} await new Promise(r=>setTimeout(r,100))}throw new Error('Server not ready')}
(async()=>{
 try{
  await Promise.all([ready('http://127.0.0.1:18000/api/v1/trips'),ready('http://127.0.0.1:18174')]);
  browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  // Send the Vite proxy requests to the isolated backend instead of the developer database.
  await page.route('**/api/v1/**',async route=>{
   const req=route.request(), url=new URL(req.url());
   const response=await route.fetch({url:'http://127.0.0.1:18000'+url.pathname+url.search});
   await route.fulfill({response});
  });
  await page.goto('http://127.0.0.1:18174');
  await page.getByLabel('旅行名称',{exact:true}).fill('周末湖畔漫游');
  const shots=path.join(root,'tmp/ui-review');fs.mkdirSync(shots,{recursive:true});
  await page.screenshot({path:path.join(shots,'home.png'),fullPage:true});
  await page.getByRole('button',{name:'创建三日旅行',exact:false}).click();
  await page.getByRole('heading',{name:'周末湖畔漫游'}).waitFor();
  await page.getByLabel('搜索景点',{exact:true}).fill('博物馆');
  await page.getByRole('heading',{name:'城市博物馆',exact:true}).waitFor();
  assert.equal(await page.locator('.spot-card').count(),1);
  await page.getByRole('button',{name:'查看城市博物馆详情'}).click();
  await page.getByRole('dialog').waitFor();
  assert.ok((await page.getByRole('dialog').innerText()).includes('09:00–17:00'));
  await page.getByRole('button',{name:'关闭详情'}).click();
  await page.getByLabel('搜索景点',{exact:true}).fill('不存在');
  await page.getByRole('heading',{name:'还没有找到'}).waitFor();
  await page.getByRole('button',{name:'清除筛选'}).click();
  await page.getByRole('button',{name:'文化艺术',exact:true}).click();
  assert.equal(await page.locator('.spot-card').count(),1);
  await page.getByRole('button',{name:'加入当天',exact:false}).click();
  await page.getByRole('button',{name:'全部',exact:true}).click();
  await page.locator('.spot-card').filter({has:page.getByRole('heading',{name:'湖畔公园',exact:true})}).getByRole('button',{name:'加入当天',exact:false}).click();
  assert.equal(await page.locator('.itinerary-card').count(),2);
  await page.getByRole('button',{name:'上移湖畔公园',exact:true}).click();
  assert.ok((await page.locator('.itinerary-card').first().innerText()).includes('湖畔公园'));
  assert.ok((await page.locator('.ticket-total').innerText()).includes('20.00'));
  await page.getByRole('button',{name:'保存旅行',exact:true}).click();
  await page.getByRole('status').filter({hasText:'已保存'}).waitFor();
  await page.screenshot({path:path.join(shots,'editor.png'),fullPage:true});
  await page.reload();
  await page.getByRole('button',{name:'周末湖畔漫游',exact:false}).click();
  await page.locator('.itinerary-card').first().waitFor();
  assert.ok((await page.locator('.itinerary-card').first().innerText()).includes('湖畔公园'));
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(shots,'mobile.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS integrated UI: search, category, detail, empty reset, add, reorder, subtotal, save/reload, 390px overflow, no page errors');
 }finally{
  if(browser)await browser.close();
  backend.kill();vite.kill();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
