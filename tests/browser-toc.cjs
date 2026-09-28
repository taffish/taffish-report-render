// 人工长报告的真实浏览器验收；浏览器由维护者环境提供，不进入 Docker build-time。
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
  const report = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3]);
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    executablePath: process.env.TAFFISH_TEST_BROWSER || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  try {
  const page = await context.newPage();
  const errors = [], remote = [];
  page.on('pageerror', e => errors.push(String(e)));
  await context.route(/^https?:/, route => { remote.push(route.request().url()); return route.abort(); });
  const url = pathToFileURL(report).href;
  const checks = [];
  async function check(name, task) { await task(); checks.push(name); }
  const opened = id => page.locator(`[data-toc-toggle="${id}"]`).getAttribute('aria-expanded');
  const toggle = id => page.locator(`[data-toc-toggle="${id}"]`).click();
  await page.goto(url);
  await check('initial collapsed chapter and hidden windows', async () => {
    assert.equal(await opened('positions'), 'false');
    assert.equal(await page.locator('.toc-tree > li[data-toc-node^="candidate_"]').count(), 0);
    assert.equal(await page.locator('[data-toc-link="candidate_01_window_01"]').count(), 0);
    assert.equal(await page.locator('#candidate_01_window_01').count(), 1);
  });
  await check('deep hidden anchor opens all ancestors', async () => {
    await page.goto(url + '#candidate_19_window_10');
    for (const id of ['positions', 'focused_targets']) assert.equal(await opened(id), 'true');
    await page.waitForFunction(() => document.querySelector('[data-toc-link="candidate_19"]').getAttribute('aria-current') === 'location');
    const top = await page.locator('#candidate_19_window_10').evaluate(e => e.getBoundingClientRect().top);
    assert(top >= 0 && top < 110, `anchor offset ${top}`);
  });
  await check('independent collapse never hides body', async () => {
    await toggle('positions');
    assert.equal(await opened('positions'), 'false');
    assert(await page.locator('#candidate_19_window_10').isVisible());
    await page.mouse.wheel(0, -80);
    await page.waitForTimeout(100);
    assert.equal(await opened('positions'), 'false');
  });
  await check('link versus toggle, keyboard and history', async () => {
    await page.goto(url);
    const button = page.locator('[data-toc-toggle="positions"]');
    await button.focus();
    await page.keyboard.press('Enter');
    assert.equal(await opened('positions'), 'true');
    assert.equal(new URL(page.url()).hash, '');
    await page.locator('[data-toc-link="candidate_01"]').click();
    await page.waitForURL('**#candidate_01');
    await page.locator('[data-toc-link="candidate_02"]').click();
    await page.waitForURL('**#candidate_02');
    await page.goBack();
    await page.waitForURL('**#candidate_01');
    await page.goForward();
    await page.waitForURL('**#candidate_02');
    await page.locator('[data-toc-all="collapse"]').click();
    assert.equal(await opened('positions'), 'false');
    await page.locator('[data-toc-all="expand"]').click();
    assert.equal(await opened('positions'), 'true');
  });
  for (const viewport of [{ width: 1600, height: 1000 }, { width: 1280, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    for (const lang of ['zh', 'en']) {
      await page.goto(url + '#candidate_01_window_01');
      await page.locator(`[data-lang-toggle="${lang}"]`).click();
      await page.waitForTimeout(150);
      await check(`${viewport.width} ${lang} layout and active owner`, async () => {
        const geometry = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
          body: document.querySelector('#candidate_01_window_01').getBoundingClientRect().width }));
        assert(geometry.scroll <= geometry.width + 1, JSON.stringify(geometry));
        assert(geometry.body > 0);
        assert.equal(await page.locator('[data-toc-link="candidate_01"]').getAttribute('aria-current'), 'location');
      });
      await page.screenshot({ path: path.join(out, `body-${viewport.width}-${lang}.png`) });
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: path.join(out, `toc-${viewport.width}-${lang}.png`) });
    }
  }
  await check('200 percent equivalent reflow at 640 CSS pixels', async () => {
    // CSS zoom 不等于浏览器缩放：用 1280/2 CSS viewport 测 reflow，不注入报告 CSS。
    await page.setViewportSize({ width: 640, height: 450 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({ path: path.join(out, 'zoom-200.png') });
  });
  await check('print does not inherit toc collapse', async () => {
    await page.locator('[data-toc-all="collapse"]').click();
    await page.emulateMedia({ media: 'print' });
    for (const lang of ['zh', 'en']) {
      await page.evaluate(lang => document.querySelector(`[data-lang-toggle="${lang}"]`).click(), lang);
      for (const id of ['candidate_01_window_01', 'candidate_19_window_10']) assert(await page.locator('#' + id).isVisible());
      await page.pdf({ path: path.join(out, `toc-print-${lang}.pdf`), format: 'A4', printBackground: true });
    }
    await page.emulateMedia({ media: 'screen' });
  });
  if (process.argv[4]) await check('legacy navigation and native subreport interaction', async () => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(pathToFileURL(path.resolve(process.argv[4])).href);
    assert.equal(await page.locator('.section-nav').getAttribute('data-toc-mode'), 'legacy');
    assert(await page.locator('.nav-group').count() > 0);
    assert.equal(await page.locator('.toc-tree').count(), 0);
    const link = page.locator('.subreport-open-link').first();
    const popupPromise = page.waitForEvent('popup');
    await link.click();
    const popup = await popupPromise;
    await popup.waitForFunction(() => document.body && document.body.innerText.length > 50);
    assert(!popup.url().startsWith('blob:'));
    await popup.close();
    await page.screenshot({ path: path.join(out, 'legacy-native.png') });
  });
  if (process.argv[5]) await check('portrait media and lightbox compatibility', async () => {
    await page.goto(pathToFileURL(path.resolve(process.argv[5])).href);
    for (const width of [1600, 1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const lang of ['zh', 'en']) {
        await page.locator(`[data-lang-toggle="${lang}"]`).click();
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        const geometry = await page.locator('.plot-media-image img').evaluateAll(images => images.map(img => ({
          naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight,
          width: img.getBoundingClientRect().width, height: img.getBoundingClientRect().height,
          complete: img.complete, fit: getComputedStyle(img).objectFit
        })));
        assert(geometry.length >= 3);
        assert(geometry.every(i => i.complete && i.naturalWidth > 0 && i.width > 0 && i.fit === 'contain'),
          `media image decode/layout failure: ${JSON.stringify({width, lang, geometry})}`);
        if (width <= 1280) assert(geometry.every(i => i.height <= 720.5));
        await page.locator('.plot-card-media').first().scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(out, `media-${width}-${lang}.png`) });
      }
    }
    await page.locator('.plot-image-button[data-open-image]').first().click();
    assert(await page.locator('[data-image-modal]').isVisible());
    const before = await page.evaluate(() => scrollY);
    await page.mouse.wheel(0, 180);
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => scrollY), before);
    await page.locator('[data-image-modal] button[data-modal-close]').click();
    assert(!(await page.locator('[data-image-modal]').isVisible()));
  });
  assert.deepEqual(errors, []);
  assert.deepEqual(remote, []);
  fs.writeFileSync(path.join(out, 'browser-receipt.json'), JSON.stringify({ browser: browser.version(), report, checks, errors, remote, print_scope: 'body visibility; full pagination acceptance separate' }, null, 2));
  console.log(`BROWSER_TOC_OK checks=${checks.length}`);
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
