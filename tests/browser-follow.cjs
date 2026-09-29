// 0.4.1 随读目录验收：真实滚轮，不注入 CSS/JS finalizer，不把 hash 导航冒充滚动。
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {createHash} = require('node:crypto');
(async () => {
  const root = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]);
  fs.mkdirSync(out,{recursive:true});
  const browser = await chromium.launch({headless:true,
    executablePath:process.env.TAFFISH_TEST_BROWSER || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const receipt = {browser:browser.version(),checks:[],errors:[],remote:[],status:'RUNNING'};
  try {
    const context = await browser.newContext({viewport:{width:1280,height:900}});
    await context.route(/^https?:/,r=>{receipt.remote.push(r.request().url());return r.abort();});
    const page = await context.newPage();
    page.on('pageerror',e=>receipt.errors.push(String(e)));
    const url = name => pathToFileURL(path.join(root,name,'report.html')).href;
    const check = async (name,fn) => {await fn();receipt.checks.push(name);};
    const open = id => page.locator('#toc-branch-'+id).evaluate(e=>!e.hidden);
    const active = id => page.waitForFunction(id=>document.querySelector('.section-nav a.active')?.hash==='#'+id,id);
    async function wheel(id,owner=id) {
      const width = page.viewportSize().width;
      await page.mouse.move(width-30,450);
      const delta = await page.locator('#'+id).evaluate(e=>e.getBoundingClientRect().top-65);
      await page.mouse.wheel(0,delta);
      await active(owner);
      await page.waitForTimeout(120);
    }
    const bodyHash = () => page.evaluate(()=>['alpha','beta'].map(id=>document.getElementById(id).outerHTML).join(''))
      .then(value=>createHash('sha256').update(value).digest('hex'));
    // 用实时 DOM 几何独立计算读点，不能复用 renderer 的缓存或先跳深层 hash。
    const readingState = () => page.evaluate(()=>{
      const index=JSON.parse(document.getElementById('report-toc-data').textContent);
      const points=index.nodes.map(node=>({node,top:document.getElementById(node.id).getBoundingClientRect().top+scrollY}))
        .sort((a,b)=>a.top-b.top||a.node.body_order-b.node.body_order);
      const line=scrollY+Math.min(180,innerHeight*.28);
      let best=points[0];for(const point of points)if(point.top<=line)best=point;
      if(scrollY>=document.documentElement.scrollHeight-innerHeight-4)best=points.at(-1);
      const owner=index.nodes.find(node=>node.id===best.node.active_id);
      const branches=[...document.querySelectorAll('[data-toc-branch]')];
      const current=document.querySelector('.section-nav a.active');
      return {reading:best.node.id,expected:owner.id,actual:current?.hash.slice(1),
        expectedOpen:branches.filter(e=>[...owner.ancestors,owner.id].includes(e.dataset.tocBranch)).map(e=>e.dataset.tocBranch).sort(),
        open:branches.filter(e=>!e.hidden).map(e=>e.dataset.tocBranch).sort(),
        activeCount:document.querySelectorAll('.section-nav a.active[aria-current="location"]').length,
        activeVisible:!!current?.getClientRects().length,y:scrollY,
        mainTop:document.querySelector('.report-main').getBoundingClientRect().top+scrollY,
        readingTop:document.getElementById(best.node.id).getBoundingClientRect().top,
        focus:document.activeElement.outerHTML.split('>')[0],hash:location.hash};
    });
    receipt.continuousScroll=[];
    for(const [name,width] of [['long-toc-titles',390],['long-toc-titles',640],
      ...[390,640,980,981,1280].map(width=>['follow',width])])for(const lang of ['zh','en'])
      await check(`${name} ${width}px ${lang} continuous forward/backward reading`,async()=>{
        await page.setViewportSize({width,height:width===390?844:900});
        await page.goto(url(name));
        await page.locator(`[data-lang-toggle="${lang}"]`).click();
        await page.mouse.move(width-30,700);
        await page.waitForTimeout(150);
        const focus=(await readingState()).focus;
        const record={name,width,lang,samples:[]};receipt.continuousScroll.push(record);
        for(const direction of [1,-1])for(let step=0;step<55;step++){
          const before=await readingState();
          await page.mouse.wheel(0,direction*260);
          await page.waitForTimeout(160);
          const state=await readingState();record.samples.push({direction,step,...state});
          assert.equal(state.actual,state.expected,JSON.stringify(state));
          assert.deepEqual(state.open,state.expectedOpen,'only the complete current reading path is open');
          assert.equal(state.activeCount,1);assert(state.activeVisible);
          assert.equal(state.focus,focus,'ordinary reading stole keyboard focus');
          assert.equal(state.hash,'','ordinary reading changed the URL');
          const beforeProgress=before.y-before.mainTop,afterProgress=state.y-state.mainTop;
          if(beforeProgress>260 && afterProgress>260)
            assert(Math.abs(afterProgress-beforeProgress-direction*260)<2,'TOC reflow displaced body beyond the wheel input');
          if(step===54){
            await page.screenshot({path:path.join(out,`${name}-continuous-${width}-${lang}-${direction}.png`)});
            await page.waitForTimeout(250);
            const settled=await readingState();
            assert.equal(settled.actual,settled.expected);
            assert(Math.abs(settled.y-state.y)<1,'scroll position oscillated while idle');
            assert(Math.abs(settled.readingTop-state.readingTop)<1,'body moved while idle');
          }
        }
        assert(record.samples.some(s=>s.reading.includes('_window_')),'must read hidden windows');
        assert(record.samples.some(s=>s.open.includes('focused_targets')),'must enter nested target path');
        assert(!record.samples.at(-1).open.includes('focused_targets'),'must leave target path on reverse reading');
      });
    let legacyHash;
    for (const name of ['legacy','hide-only','title-only','empty-toc']) await check(name+' follows ordinary reading',async()=>{
      await page.goto(url(name));
      assert.equal(await page.locator('[data-toc-toggle],[data-toc-all]').count(),0);
      await wheel('alpha1');
      if (name==='legacy') {
        assert.equal(await page.locator('details.nav-group[open]').count(),1);
        assert(await page.locator('details.nav-group[open] a[href="#alpha1"]').isVisible());
      } else {assert(await open('alpha'));assert(!await open('beta'));}
      await wheel('beta1');
      if (name==='legacy') {
        assert.equal(await page.locator('details.nav-group[open]').count(),1);
        assert(await page.locator('details.nav-group[open] a[href="#beta1"]').isVisible());
        legacyHash = await bodyHash();
      } else {assert(!await open('alpha'));assert(await open('beta'));assert.equal(await bodyHash(),legacyHash);}
      assert.equal(new URL(page.url()).hash,'');
      if (name==='hide-only') {
        assert.equal(await page.locator('.section-nav a[href="#alpha2"]').count(),0);
        assert.equal(await page.locator('#alpha2').count(),1);
        await wheel('alpha2','alpha');
        assert(await open('alpha'));assert(!await open('beta'));
      }
      await page.screenshot({path:path.join(out,name+'.png')});
    });
    receipt.simpleBodySHA256=legacyHash;
    await page.goto(url('follow'));
    await check('ordinary deep scroll overrides collapsed and expands only active path',async()=>{
      assert(!await open('positions'));
      await wheel('candidate_19_window_10','candidate_19');
      assert(await open('positions'));assert(await open('focused_targets'));
      assert(!await open('overview'));assert(!await open('other_targets'));
      assert(await page.locator('[data-toc-link="candidate_19"]').isVisible());
      assert.equal(await page.locator('[data-toc-link="candidate_19"]').getAttribute('aria-current'),'location');
      assert(await page.locator('[data-toc-link="candidate_19"]').evaluate(e=>{
        const r=e.getBoundingClientRect(),s=e.closest('.report-sidebar').getBoundingClientRect();
        return r.top>=s.top && r.bottom<=s.bottom;
      }),'active link must be in the desktop sidebar viewport, not merely unhidden');
      assert.equal(await page.locator('[data-toc-link="candidate_19_window_10"]').count(),0);
      assert.equal(new URL(page.url()).hash,'');
      const before=await page.evaluate(()=>scrollY);
      await page.waitForTimeout(250);
      assert(Math.abs(await page.evaluate(()=>scrollY)-before)<1,'auto following moved body');
      assert.equal(await page.evaluate(()=>document.activeElement.tagName),'BODY');
      await page.screenshot({path:path.join(out,'deep-scroll.png')});
    });
    await check('cross-chapter reading closes unrelated paths',async()=>{
      await wheel('intro-text');
      assert(await open('overview'));assert(!await open('positions'));assert(!await open('focused_targets'));
      await wheel('other-text');
      assert(await open('positions'));assert(await open('other_targets'));assert(!await open('focused_targets'));
    });
    await check('deep link, navigation, history and repeated hash',async()=>{
      await page.goto(url('follow')+'#candidate_19_window_10');
      await active('candidate_19');
      assert(await open('positions'));assert(await open('focused_targets'));
      await page.locator('[data-toc-link="candidate_01"]').click();
      await page.waitForURL('**#candidate_01');
      await page.locator('[data-toc-link="candidate_02"]').click();
      await page.goBack();await page.waitForURL('**#candidate_01');await active('candidate_01');
      await page.goForward();await page.waitForURL('**#candidate_02');await active('candidate_02');
      await wheel('intro-text');
      await page.locator('[data-toc-link="positions"]').click();
      await page.locator('[data-toc-link="focused_targets"]').click();
      await page.locator('[data-toc-link="candidate_02"]').click();await active('candidate_02');
    });
    await check('keyboard focus is not hidden or stolen by reading updates',async()=>{
      await page.goto(url('follow')+'#candidate_19_window_10');
      const focus=page.locator('[data-toc-link="candidate_19"]');
      await focus.focus();
      await wheel('intro-text');
      assert(await open('positions'));assert(await open('focused_targets'));
      assert(await focus.evaluate(e=>document.activeElement===e));assert(await focus.isVisible());
      await page.locator('[data-toc-link="overview"]').focus();
      await page.waitForTimeout(100);
      assert(!await open('positions'));
      await page.keyboard.press('Tab');
      assert(await page.evaluate(()=>document.activeElement.closest('.section-nav')!==null));
      await page.keyboard.press('Shift+Tab');
      assert(await page.locator('[data-toc-link="overview"]').evaluate(e=>document.activeElement===e));
      // Enter 保留原生 fragment 导航；其后的 Tab 起点应允许进入目标正文。
      await page.keyboard.press('Enter');await page.waitForURL('**#overview');
      assert(await open('overview'));
    });
    for (const width of [1600,1280,390]) for (const lang of ['zh','en']) await check(`${width}px ${lang} follow layout`,async()=>{
      await page.setViewportSize({width,height:width===390?844:900});
      await page.goto(url('follow')+'#candidate_19_window_10');
      await page.locator(`[data-lang-toggle="${lang}"]`).click();
      await active('candidate_19');
      assert(await open('positions'));assert(await open('focused_targets'));
      assert.equal(await page.locator('[data-toc-toggle],[data-toc-all]').count(),0);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(out,`follow-${width}-${lang}.png`)});
      // 真正跨章滚轮与语言无关，仍不移动焦点。
      await wheel('intro-text');assert(!await open('positions'));
    });
    await check('manual is explicit even without structural fields',async()=>{
      await page.setViewportSize({width:1280,height:900});
      await page.goto(url('manual-simple'));
      assert.equal(await page.locator('.section-nav').getAttribute('data-toc-interaction'),'manual');
      await page.locator('[data-toc-toggle="alpha"]').click();
      await wheel('alpha1');assert(!await open('alpha'));
      await wheel('beta1');assert(!await open('alpha'));assert(await open('beta'));
      assert.equal(await bodyHash(),legacyHash);
    });
    await check('print media keeps every body component despite closed navigation',async()=>{
      await page.goto(url('follow'));
      await page.emulateMedia({media:'print'});
      for(const id of ['candidate_01_score','candidate_01_window_01','candidate_19_window_10']) assert(await page.locator('#'+id).isVisible());
      const counts = await page.evaluate(()=>{
        const nodes=JSON.parse(document.getElementById('report-toc-data').textContent).nodes.filter(n=>n.kind==='component');
        return {expected:nodes.length,visible:nodes.filter(n=>document.getElementById(n.id).getClientRects().length).length};
      });
      assert.deepEqual(counts,{expected:212,visible:212});receipt.printDOM=counts;
      if (process.env.TAFFISH_TEST_PRINT==='1') for (const lang of ['zh','en']) {
        await page.evaluate(lang=>document.querySelector(`[data-lang-toggle="${lang}"]`).click(),lang);
        await page.pdf({path:path.join(out,`toc-print-${lang}.pdf`),format:'A4',printBackground:true});
      }
      await page.emulateMedia({media:'screen'});
    });
    assert.deepEqual(receipt.errors,[]);assert.deepEqual(receipt.remote,[]);receipt.status='PASS';
  } catch(error) {receipt.status='FAIL';receipt.failure=String(error);throw error;}
  finally {fs.writeFileSync(path.join(out,'browser-follow-receipt.json'),JSON.stringify(receipt,null,2)+'\n');await browser.close();}
  console.log(JSON.stringify(receipt,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
