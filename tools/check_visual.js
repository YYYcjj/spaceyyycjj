/**
 * 需要 playwright（本机装在 node workspace 里）。运行方式：
 *
 *   NODE_PATH=<node-workspace>/node_modules node tools/check_visual.js <BASE_URL>
 *
 * BASE_URL 省略时默认 http://127.0.0.1:4321/ —— 先用
 *   python3 -m http.server 4321 --bind 127.0.0.1
 * 在站点根目录起一个本地服务即可（也可以直接对线上地址跑）。
 */
/**
 * 视觉专项校验：对比度 + 舷窗背景图 + 进场动效不留白
 *
 * 结构校验（multipage-check.js）查不到这三类问题，而它们恰恰是改视觉时最容易踩的：
 *   1. 深色面板上的文字对比度不够 —— 屏幕上看「还行」，但换了显示器或投影就读不出来；
 *   2. CSS 背景图路径写错 —— 页面还是能看，只是星场整块没了，不报任何错；
 *   3. reveal 动效把内容永久藏起来 —— IO 没触发就 opacity:0，页面看着像空的。
 *
 * 用法：node visual-check.js <BASE_URL>
 */
// 默认按 NODE_PATH 找 playwright；要指到具体路径就设 PW_PATH
const PW = process.env.PW_PATH || 'playwright';
const { chromium } = require(PW);

const BASE = process.argv[2] || 'http://127.0.0.1:4321/';
const PAGES = [
  'index.html',
  'sections/01-current.html', 'sections/05-lightspeed.html',
  'sections/07-contact.html', 'sections/10-integration.html',
];

// 要检查对比度的关键文字。
// scope：'all' = 每页都必须有（缺了算回归）；'hub' = 只有首页有；'opt' = 有就查、没有跳过。
// 上次踩的坑：把所有选择器都当必查，结果在不含 KPI / 收口卡片的页面上报了一堆假失败。
const TARGETS = [
  ['.hero h1', '首屏大标题', 'all'],
  ['.hero .dek', '首屏导语', 'all'],
  ['.hero .eyebrow', '首屏眉标', 'all'],
  ['.hero .meta span', '首屏遥测标签', 'all'],
  ['.kpi .v', 'KPI 数值', 'opt'],
  ['.kpi .k', 'KPI 说明', 'opt'],
  ['.board-card.capstone h3', '收口卡片标题', 'hub'],
  ['.board-card.capstone .bc-dek', '收口卡片描述', 'hub'],
  ['.board-card.capstone .bc-num', '收口卡片编号', 'hub'],
  ['.board-card.capstone .bc-go', '收口卡片入口', 'hub'],
  ['.vt-i dt', '赛道判断标签', 'opt'],
  ['.vt-i dd', '赛道判断正文', 'opt'],
  ['.vs-md .lb', '阶段元数据标签', 'opt'],
  ['.vs-st .lb', '止损线标签', 'opt'],
  ['.trs-fig figcaption', '配图图注', 'opt'],
  ['.figure figcaption', '大图图注', 'opt'],
];

let fail = 0;
const bad = (p, t, d) => { console.log(`  FAIL  [${p}] ${t} ${JSON.stringify(d)}`); fail++; };
const good = (p, t) => console.log(`  PASS  [${p}] ${t}`);

const IN_PAGE = (TARGETS) => {
  const parse = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  // 把从页面底色到自己这一层的不透明背景叠起来，得到「文字实际坐在什么颜色上」
  const bgOf = (el) => {
    const stack = [];
    let n = el;
    while (n && n.nodeType === 1) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      n = n.parentElement;
    }
    let out = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) {
      const c = stack[i];
      out = { r: c.r * c.a + out.r * (1 - c.a),
              g: c.g * c.a + out.g * (1 - c.a),
              b: c.b * c.a + out.b * (1 - c.a), a: 1 };
    }
    return out;
  };

  const out = { targets: [], reveal: null, bg: [] };

  TARGETS.forEach(([sel, label, scope]) => {
    const el = document.querySelector(sel);
    if (!el) {
      if (scope !== 'opt') out.targets.push({ sel, label, missing: true, scope });
      return;
    }
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    // WCAG：≥24px，或 ≥18.66px 且粗体，算大字号，阈值 3.0；其余 4.5
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    out.targets.push({
      sel, label, missing: false,
      ratio: +ratio(fg, bgOf(el)).toFixed(2),
      need: large ? 3 : 4.5, size, weight,
    });
  });

  // 进场动效：等兜底定时器走过之后，不该还有停在不可见状态的元素
  const hidden = [];
  document.querySelectorAll('.reveal').forEach((el) => {
    const cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) < 0.9) hidden.push(el.className || el.tagName);
  });
  out.reveal = { total: document.querySelectorAll('.reveal').length, hidden };

  // 数字滚动动画：改动了进场动效之后，要确认它没卡在 0
  out.counts = [];
  document.querySelectorAll('[data-count]').forEach((el) => {
    out.counts.push({ want: el.getAttribute('data-count'), got: el.textContent.trim() });
  });

  // 舷窗背景图是否真的解析并加载了
  const sky = document.querySelector('.hero .sky') || document.querySelector('.hero');
  if (sky) {
    const bg = getComputedStyle(sky).backgroundImage || '';
    const m = /url\(["']?([^"')]+)["']?\)/.exec(bg);
    out.bg.push({ who: 'hero .sky', url: m ? m[1] : '' });
  }
  const cap = document.querySelector('.board-card.capstone');
  if (cap) {
    const bg = getComputedStyle(cap).backgroundImage || '';
    const m = /url\(["']?([^"')]+)["']?\)/.exec(bg);
    out.bg.push({ who: 'capstone', url: m ? m[1] : '' });
  }
  return out;
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 2 });

  for (const p of PAGES) {
    const page = await ctx.newPage();
    await page.goto(BASE + p, { waitUntil: 'load' });
    // 5 秒 > site.js 里 4 秒的兜底定时器，用来验证「兜底真的生效」
    await page.waitForTimeout(5200);
    const r = await page.evaluate(IN_PAGE, TARGETS);

    r.targets.forEach((t) => {
      const required = t.scope === 'all' || (t.scope === 'hub' && p === 'index.html');
      if (t.missing) {
        if (required) bad(p, '缺少元素 ' + t.label, t.sel);
        return;                                  // 非必查的页面直接跳过，不报假失败
      }
      if (t.ratio < t.need) bad(p, `${t.label} 对比度不足`, { ratio: t.ratio, need: t.need, size: t.size });
      else good(p, `${t.label} 对比度 ${t.ratio}:1`);
    });

    if (r.reveal.hidden.length) bad(p, '有元素停在不可见状态', r.reveal.hidden);
    else good(p, `进场动效无残留（${r.reveal.total} 个元素已显示）`);

    const stuck = r.counts.filter(c => parseFloat(c.got) !== parseFloat(c.want));
    if (r.counts.length) {
      if (stuck.length) bad(p, '首屏数字动画未走到终值', stuck);
      else good(p, `首屏数字动画正常（${r.counts.length} 个计数）`);
    }

    for (const b of r.bg) {
      if (!b.url) { bad(p, b.who + ' 没有背景图', b); continue; }
      const resp = await page.request.get(b.url.startsWith('http') ? b.url : new URL(b.url, page.url()).href);
      if (!resp.ok()) bad(p, b.who + ' 背景图加载失败', { url: b.url, status: resp.status() });
      else good(p, `${b.who} 背景图 ${resp.status()} ${b.url.split('/').pop()}`);
    }

    await page.close();
    console.log('');
  }

  await browser.close();
  console.log(fail ? `==> 视觉校验失败 ${fail} 项` : '==> 视觉校验全部通过');
  process.exit(fail ? 1 : 0);
})();
