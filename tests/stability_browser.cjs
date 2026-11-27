const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const server = spawn(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host','127.0.0.1','--port','18173','--strictPort','--bypass-lock'], {cwd:path.join(root,'frontend'),windowsHide:true,stdio:'ignore'});
let browser;
(async()=>{
 try {
  for(let i=0;i<100;i++){
   try{if((await fetch('http://127.0.0.1:18173')).ok)break}catch{}
   await new Promise(resolve=>setTimeout(resolve,100));
  }
  browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage();
  const makeTrip=id=>({id,name:'测试旅行'+id,startDate:'2026-12-01',dayCount:3,budgetLimitCents:100000,revision:1,days:[1,2,3].map(i=>({id:'day-'+i,dayIndex:i,startMinutes:540,endMinutes:1260,items:[],expenses:[]}))});
  let trips=[makeTrip('1'),makeTrip('2')], finishSave, failSave=false;
  await page.route('**/api/v1/**',async route=>{
   const request=route.request(), url=new URL(request.url());
   let data;
   if(url.pathname.endsWith('/attractions'))data=[{id:'spot-1',name:'湖畔公园',ticketCents:0}];
   else if(url.pathname.endsWith('/trips'))data=trips;
   else if(request.method()==='PUT'){
    if(failSave){await route.fulfill({status:500,json:{message:'模拟失败'}});return}
    await new Promise(resolve=>{finishSave=resolve});
    data={...request.postDataJSON(),id:'1',revision:2};
    trips[0]=data;
   }else data=trips.find(t=>url.pathname.endsWith('/'+t.id));
   await route.fulfill({json:{code:'OK',data}});
  });
  await page.goto('http://127.0.0.1:18173');
  await page.getByRole('button',{name:'测试旅行1',exact:false}).click();
  await page.getByRole('button',{name:'加入当天'}).click();
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'返回列表'}).click();
  assert.equal(await page.getByRole('heading',{name:'测试旅行1'}).count(),1);
  assert.equal(await page.getByRole('button',{name:'删除',exact:true}).count(),1);
  await page.getByRole('button',{name:'保存旅行'}).click();
  await page.waitForFunction(()=>document.querySelector('[role=status]').textContent.includes('保存中'));
  assert.equal(await page.getByRole('button',{name:'返回列表'}).isDisabled(),true);
  while(!finishSave)await new Promise(resolve=>setTimeout(resolve,10));
  finishSave();
  await page.getByRole('status').filter({hasText:'已保存'}).waitFor();
  await page.getByRole('button',{name:'返回列表'}).click();
  await page.getByRole('button',{name:'测试旅行2',exact:false}).click();
  await page.getByRole('heading',{name:'测试旅行2'}).waitFor();
  await page.getByRole('button',{name:'加入当天'}).click();
  failSave=true;
  await page.getByRole('button',{name:'保存旅行'}).click();
  await page.getByRole('status').filter({hasText:'当前编辑已保留'}).waitFor();
  assert.equal(await page.getByRole('button',{name:'删除',exact:true}).count(),1);
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'返回列表'}).click();
  await page.getByRole('heading',{name:'我的旅行'}).waitFor();
  console.log('PASS browser: cancel unsaved leave, save navigation lock, correct trip after delayed save, failed-save draft, confirmed discard');
 } finally {
  if(browser)await browser.close();
  server.kill();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
