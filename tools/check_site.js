/**
 * 需要 playwright（本机装在 node workspace 里）。运行方式：
 *
 *   NODE_PATH=<node-workspace>/node_modules node tools/check_site.js <BASE_URL>
 *
 * BASE_URL 省略时默认 http://127.0.0.1:4321/ —— 先用
 *   python3 -m http.server 4321 --bind 127.0.0.1
 * 在站点根目录起一个本地服务即可（也可以直接对线上地址跑）。
 */
/**
 * 宇宙航行全景 · 全站批量无头校验
 * 覆盖 11 个页面（首页 + 10 板块）：
 *   - 桌面/移动端无横向溢出
 *   - 侧栏与顶部导航的显示切换
 *   - 移动端表格转卡片 + td::before 字段标题
 *   - 页内锚点全部可解析
 *   - 站内跨页链接（相对路径）真实存在（HTTP 200）
 *   - 控制台错误 / 资源加载失败
 */
// 默认按 NODE_PATH 找 playwright；要指到具体路径就设 PW_PATH
const PW = process.env.PW_PATH || 'playwright';
const { chromium } = require(PW);

const BASE = process.argv[2] || 'http://127.0.0.1:4321/';
const PAGES = [
  'index.html',
  'sections/01-current.html', 'sections/02-rocket-tech.html', 'sections/03-starship.html',
  'sections/04-biosphere.html', 'sections/05-lightspeed.html', 'sections/06-lifespan.html',
  'sections/07-contact.html', 'sections/08-resources.html', 'sections/09-ai-robots.html',
  'sections/10-integration.html',
];

let fail = 0;
const bad = (p, label, d) => { console.log(`  FAIL  [${p}] ${label} ${d !== undefined ? JSON.stringify(d) : ''}`); fail++; };
const good = (p, label) => console.log(`  PASS  [${p}] ${label}`);

(async () => {
  const browser = await chromium.launch();
  const dctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 2 });
  const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });

  for (const p of PAGES) {
    const url = BASE + p;
    const isHub = p === 'index.html';
    const errors = [], failedReq = [];

    // ---------------- 桌面 ----------------
    const dp = await dctx.newPage();
    dp.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    dp.on('pageerror', e => errors.push('pageerror: ' + e.message));
    dp.on('requestfailed', r => failedReq.push(r.url() + ' :: ' + ((r.failure() || {}).errorText || '')));

    const resp = await dp.goto(url, { waitUntil: 'load' });
    if (!resp || resp.status() !== 200) bad(p, 'HTTP 200', resp && resp.status());
    await dp.waitForTimeout(1000);

    const desk = await dp.evaluate(() => {
      const cs = el => el ? getComputedStyle(el) : null;
      const q = s => document.querySelector(s);
      const ids = new Set([...document.querySelectorAll('[id]')].map(e => e.id));
      const hrefs = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href').slice(1)).filter(Boolean);
      const cross = [...new Set([...document.querySelectorAll('a[href]')]
        .map(a => a.getAttribute('href'))
        .filter(h => h && !h.startsWith('#') && !h.startsWith('http') && !h.startsWith('mailto')))];
      const tdNoTh = [...document.querySelectorAll('tbody td:not(.nm)')].filter(td => !td.hasAttribute('data-th')).length;
      const kpi = [...document.querySelectorAll('.kpi .v')].map(e => e.textContent.trim());
      return {
        title: document.title,
        h1: q('h1') ? q('h1').textContent.trim() : null,
        sections: document.querySelectorAll('main section').length,
        tables: document.querySelectorAll('table').length,
        // ⚠️ 必须跟 clientWidth 比，不能跟 window.innerWidth 比：
        // isMobile 模拟下 innerWidth 会被撑成内容宽（= scrollWidth），
        // 于是「有横向溢出」永远判成 false —— 这个漏报让「手机上整页能左右拖」
        // 一直没被抓到（真因是顶部胶囊导航用负 margin 出血撑宽了文档）。
        hScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        hScrollNum: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        rail: cs(q('.rail')) ? cs(q('.rail')).display : null,
        topnav: cs(q('.topnav')) ? cs(q('.topnav')).display : null,
        tableDisp: cs(q('table')) ? cs(q('table')).display : null,
        missing: [...new Set(hrefs)].filter(h => !ids.has(h)),
        tdNoTh, cross, kpi,
        bg: cs(document.body).backgroundColor,
        fg: cs(document.body).color,
        cards: document.querySelectorAll('.board-card').length,
        // 重复 id：内联 SVG 的 marker/gradient 很容易全页重名（本次修的就是这个），
        // 重名既让 HTML 非法，也让 url(#id) 只命中文档里第一个，图形会串。
        dupIds: (() => {
          const seen = new Set(), dup = new Set();
          document.querySelectorAll('[id]').forEach(e => { if (seen.has(e.id)) dup.add(e.id); seen.add(e.id); });
          return [...dup];
        })(),
        skip: (() => {
          const a = document.querySelector('a.skip');
          return a ? { href: a.getAttribute('href'), target: !!document.querySelector(a.getAttribute('href')) } : null;
        })(),
        ariaCurrent: document.querySelectorAll('[aria-current="page"]').length,
        chainfigs: (() => {
          const sec = q('#chain');
          return sec ? sec.querySelectorAll('.trs-fig').length : null;
        })(),
        intro: (() => {
          const sec = q('#intro');
          if (!sec) return null;
          const main = sec.closest('main') || document.body;
          const secs = [...main.querySelectorAll('section[id]')];
          return {
            figs: sec.querySelectorAll('.trs-fig').length,
            first: secs.length > 0 && secs[0].id === 'intro',
          };
        })(),
        // 层级路标：五层「概览栏目」（带层序号块）+ 一个「正文」分组标题。
        // 这两个东西原来都没有——层与编号小节在视觉上完全同位，长页里找不到路标。
        layers: (() => {
          const main = document.querySelector('main') || document.body;
          const secs = [...main.querySelectorAll('section[id]')];
          const ly = secs.filter(s => s.classList.contains('layer'));
          const g = main.querySelector('.grp-hd');
          return {
            count: ly.length,
            chips: ly.filter(s => s.querySelector('.ly')).length,
            nums: ly.map(s => {
              const c = s.querySelector('.ly');
              return c ? (c.textContent.match(/\d+/) || [''])[0] : '';
            }),
            grp: main.querySelectorAll('.grp-hd').length,
            // 分组标题必须在所有层之后（跑到层前面，「正文」这个词就没有意义了）
            grpOrdered: g ? ly.every(s => (s.compareDocumentPosition(g) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0) : null,
          };
        })(),
        // 注意：不能用 rail 这个键——上面已经用它存「侧栏 display」了，
        // 同名的后一个键会静默覆盖前一个，结果「桌面显示侧栏目录」这条断言直接挂掉。
        railGroups: (() => {
          const r = document.querySelector('.rail nav');
          return r ? { lyLinks: r.querySelectorAll('a.toc-ly').length, grp: r.querySelectorAll('.rail-grp').length } : null;
        })(),
        venture: (() => {
          const sec = q('#venture');
          if (!sec) return null;
          // 「块级 + 内容长」= 正文加粗被误当标签渲染（标签必须用 .lb 且是短文本）。
          // 曾经踩过：标签写成 <b>、CSS 给了 display:block，正文里的加粗也跟着独占一行。
          const orphan = [...sec.querySelectorAll('.vs-meta b, .vs-st b')]
            .filter(b => cs(b).display === 'block' && b.textContent.trim().length > 12).length;
          return {
            track: sec.querySelectorAll('.vt-i').length,
            steps: sec.querySelectorAll('.vs > li').length,
            meta: sec.querySelectorAll('.vs-meta > span').length,
            stop: sec.querySelectorAll('.vs-st').length,
            lb: sec.querySelectorAll('.lb').length,
            figs: sec.querySelectorAll('.trs-fig').length,
            orphan,
          };
        })(),
      };
    });

    if (desk.dupIds && desk.dupIds.length) bad(p, '全页无重复 id', desk.dupIds.slice(0, 5));
    else good(p, '全页无重复 id');
    if (desk.skip) {
      if (!desk.skip.target) bad(p, '跳转链接指向存在的锚点', desk.skip.href);
      else good(p, '跳转链接指向 #main');
    }
    // 板块页上「当前页」有两处：侧栏板块列表 + 顶部胶囊导航，所以是 2；
    // 首页不是任何板块，所以是 0。
    const wantCur = isHub ? 0 : 2;
    if (desk.ariaCurrent !== wantCur) bad(p, `当前页标记 aria-current 应为 ${wantCur} 处`, desk.ariaCurrent);
    else good(p, `当前页标记 aria-current（${wantCur} 处）`);
    if (desk.hScroll) bad(p, '桌面无横向溢出', { 超出: desk.hScrollNum });
    else good(p, '桌面无横向溢出');
    if (isHub) {
      if (desk.cards !== 10) bad(p, '首页 10 张板块卡片', desk.cards); else good(p, '首页 10 张板块卡片');
      if (desk.rail !== null) bad(p, '首页无侧栏', desk.rail); else good(p, '首页无侧栏（单列）');
    } else {
      if (desk.rail !== 'block') bad(p, '桌面显示侧栏目录', desk.rail); else good(p, '桌面显示侧栏目录');
      if (desk.topnav !== 'none') bad(p, '桌面隐藏顶部胶囊导航', desk.topnav); else good(p, '桌面隐藏顶部胶囊导航');
      if (desk.tableDisp !== 'table' && desk.tables > 0) bad(p, '桌面表格 table 布局', desk.tableDisp);
      else good(p, `桌面表格 table 布局 (${desk.tables} 表)`);
    }
    if (desk.missing.length) bad(p, '页内锚点全部可解析', desk.missing); else good(p, '页内锚点全部可解析');
    if (desk.tdNoTh) bad(p, '表格 td 均有 data-th', desk.tdNoTh); else good(p, '表格 td 均有 data-th');
    if (desk.kpi.some(v => v === '0' || v === '')) bad(p, 'KPI 计数动画完成', desk.kpi);
    else if (desk.kpi.length) good(p, `KPI 计数动画完成 (${desk.kpi.join(' / ')})`);

    // 技术链路的每一环都要有配图（九板块 × 6 环）
    if (desk.chainfigs !== null) {
      if (desk.chainfigs !== 6) bad(p, '技术链路 6 张链路图', desk.chainfigs);
      else good(p, '技术链路 6 张链路图');
    }

    // 层级路标（板块页才有；首页没有 rail 也没有层）
    if (desk.layers && (desk.layers.count || desk.layers.grp)) {
      const L = desk.layers;
      if (L.chips !== L.count) bad(p, '每个层都要有层序号块', { chips: L.chips, layers: L.count });
      else good(p, `层级路标完整（${L.count} 层，各有层序号块）`);
      if (L.count !== 5 && L.count !== 1) bad(p, '概览层应为 5 层（收口页只有导览 1 层）', L.count);
      const want = L.nums.map((_, i) => String(i + 1).padStart(2, '0')).join(',');
      if (L.nums.join(',') !== want) bad(p, '层序号从 01 连续递增', L.nums);
      else good(p, '层序号从 01 连续递增');
      if (L.grp !== 1) bad(p, '正文分组标题恰好 1 个', L.grp);
      else good(p, '正文分组标题恰好 1 个');
      if (L.grpOrdered === false) bad(p, '正文分组标题必须排在所有层之后', L.grpOrdered);
      else good(p, '正文分组标题排在所有层之后');
    }
    if (desk.railGroups && desk.railGroups.grp) {
      if (desk.railGroups.grp !== 1) bad(p, '侧栏有 1 个分组标签', desk.railGroups.grp);
      else good(p, '侧栏有 1 个分组标签');
      if (desk.layers && desk.railGroups.lyLinks !== desk.layers.count) {
        bad(p, '侧栏层项数与页面层数一致', { rail: desk.railGroups.lyLinks, page: desk.layers.count });
      } else good(p, '侧栏层项数与页面层数一致');
    }

    // 板块开头的导览区（十个板块都有；首页没有，所以以元素存在为准）
    if (desk.intro) {
      if (desk.intro.figs !== 2) bad(p, '导览区 2 张图', desk.intro.figs);
      else good(p, '导览区 2 张图');
      if (!desk.intro.first) bad(p, '导览区必须排在所有章节之前', desk.intro.first);
      else good(p, '导览区排在所有章节之前');
    }

    // 创业者路线图的结构（板块 1–9 有，收口页没有，所以以元素存在为准）
    if (desk.venture) {
      const v = desk.venture;
      if (v.track !== 6) bad(p, '赛道判断 6 格', v.track); else good(p, '赛道判断 6 格');
      if (v.steps !== 5) bad(p, '路线图 5 个阶段', v.steps); else good(p, '路线图 5 个阶段');
      if (v.meta !== 20) bad(p, '每阶段 4 项元数据 × 5 阶段', v.meta); else good(p, '每阶段 4 项元数据 × 5 阶段');
      if (v.stop !== 5) bad(p, '5 条止损线', v.stop); else good(p, '5 条止损线');
      if (v.lb !== 25) bad(p, '标签共 25 个（.lb）', v.lb); else good(p, '标签共 25 个（.lb）');
      if (v.figs !== 6) bad(p, '创业者路线图 6 张理论图', v.figs); else good(p, '创业者路线图 6 张理论图（图都有 SVG）');
      if (v.orphan) bad(p, '正文加粗被渲染成块级（标签用了 <b>）', v.orphan);
      else good(p, '标签与正文加粗未混淆');
    }

    // 跨页相对链接 HTTP 探测
    for (const rel of desk.cross) {
      const u = new URL(rel, url).href;
      const r = await dp.request.get(u);
      if (r.status() !== 200) bad(p, `跨页链接 ${rel}`, r.status());
    }
    if (desk.cross.length) good(p, `跨页链接 ${desk.cross.length} 条全部 200`);
    await dp.close();

    // ---------------- 移动端 ----------------
    const mp = await mctx.newPage();
    mp.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    mp.on('pageerror', e => errors.push('pageerror: ' + e.message));
    await mp.goto(url, { waitUntil: 'load' });
    await mp.waitForTimeout(900);
    const mob = await mp.evaluate(() => {
      const cs = el => el ? getComputedStyle(el) : null;
      const q = s => document.querySelector(s);
      const td = q('tbody td:not(.nm)');
      // 卡片化后 td 必须撑满卡片：取前 3 行里最窄的 td 与所在 tr 比
      let minRatio = 1;
      [...document.querySelectorAll('tbody tr')].slice(0, 3).forEach(tr => {
        const cells = [...tr.querySelectorAll('td')];
        if (!cells.length) return;
        const trW = tr.getBoundingClientRect().width;
        if (trW <= 0) return;
        cells.forEach(c => {
          const w = c.getBoundingClientRect().width;
          if (w > 0) minRatio = Math.min(minRatio, w / trW);
        });
      });
      return {
        // ⚠️ 必须跟 clientWidth 比，不能跟 window.innerWidth 比：
        // isMobile 模拟下 innerWidth 会被撑成内容宽（= scrollWidth），
        // 于是「有横向溢出」永远判成 false —— 这个漏报让「手机上整页能左右拖」
        // 一直没被抓到（真因是顶部胶囊导航用负 margin 出血撑宽了文档）。
        hScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        hScrollNum: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        rail: cs(q('.rail')) ? cs(q('.rail')).display : null,
        topnav: cs(q('.topnav')) ? cs(q('.topnav')).display : null,
        table: cs(q('table')) ? cs(q('table')).display : null,
        tr: cs(q('tbody tr')) ? cs(q('tbody tr')).display : null,
        td: td ? cs(td).display : null,
        thead: cs(q('thead')) ? cs(q('thead')).display : null,
        tdBefore: td ? getComputedStyle(td, '::before').content : null,
        h1: cs(q('h1')) ? cs(q('h1')).fontSize : null,
        tables: document.querySelectorAll('table').length,
        minRatio: Number(minRatio.toFixed(3)),
      };
    });
    if (mob.hScroll) bad(p, '移动端无横向溢出', { 超出: mob.hScrollNum }); else good(p, '移动端无横向溢出');
    if (isHub) {
      if (mob.rail !== null) bad(p, '首页移动端无侧栏', mob.rail); else good(p, '首页移动端无侧栏');
      if (mob.topnav !== null) bad(p, '首页移动端无顶部胶囊', mob.topnav); else good(p, '首页移动端无顶部胶囊');
    } else {
      if (mob.rail !== 'none') bad(p, '移动端隐藏侧栏', mob.rail); else good(p, '移动端隐藏侧栏');
      if (mob.topnav !== 'block') bad(p, '移动端显示顶部胶囊导航', mob.topnav); else good(p, '移动端显示顶部胶囊导航');
    }
    if (mob.tables > 0) {
      if (!(mob.table === 'block' && mob.tr === 'block' && mob.td === 'block')) bad(p, '移动端表格转卡片', mob);
      else good(p, '移动端表格转卡片');
      if (mob.thead !== 'none') bad(p, '移动端隐藏表头', mob.thead); else good(p, '移动端隐藏表头');
      if (!mob.tdBefore || mob.tdBefore === 'none' || mob.tdBefore === '""') bad(p, '卡片显示字段标题', mob.tdBefore);
      else good(p, '卡片显示字段标题 (td::before)');
      if (mob.minRatio < 0.85) bad(p, '卡片内 td 撑满宽度', { minRatio: mob.minRatio });
      else good(p, '卡片内 td 撑满宽度');
    }
    await mp.close();

    if (errors.length) bad(p, '无控制台错误', errors); else good(p, '无控制台错误');
    if (failedReq.length) bad(p, '无资源加载失败', failedReq); else good(p, '无资源加载失败');
    console.log('');
  }

  // ---------------- 中间宽度带扫描 ----------------
  // 原来的校验只测 1366（桌面）与 390（手机）两个宽度，而「显示切换」的断点在
  // 641–1080（侧栏隐藏、胶囊导航出现）——这一整段从没被测过，横向溢出就藏在这里。
  const SWEEP = [700, 900, 1024];
  const SWEEP_PAGES = ['sections/02-rocket-tech.html', 'index.html'];
  for (const sp of SWEEP_PAGES) {
    for (const w of SWEEP) {
      const c = await browser.newContext({ viewport: { width: w, height: 820 } });
      const pg = await c.newPage();
      await pg.goto(BASE + sp, { waitUntil: 'load' });
      await pg.waitForTimeout(900);
      const r = await pg.evaluate(() => ({
        over: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        nav: (() => { const n = document.querySelector('.topnav'); return n ? getComputedStyle(n).display : null; })(),
        rail: (() => { const n = document.querySelector('.rail'); return n ? getComputedStyle(n).display : null; })(),
      }));
      if (r.over > 1) bad(sp, `${w}px 无横向溢出`, { 超出: r.over });
      else good(sp, `${w}px 无横向溢出（nav ${r.nav} / 侧栏 ${r.rail}）`);
      await c.close();
    }
  }
  console.log('');

  await browser.close();
  console.log(fail ? `==> 失败 ${fail} 项` : `==> 全部 ${PAGES.length} 个页面通过`);
  process.exit(fail ? 1 : 0);
})();
