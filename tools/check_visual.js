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
  ['.ly', '层序号块', 'opt'],
  ['.grp-hd b', '正文分组标题', 'opt'],
  ['.grp-hd .en', '正文分组英文标签', 'opt'],
  ['.rail-grp', '侧栏分组标签', 'opt'],
  ['.rail nav a.toc-ly', '侧栏层项', 'opt'],
  ['h2 .en', '标题英文标签', 'opt'],
  ['.chain-legend .clg-cap', '链路图例标题', 'opt'],
  ['.m3d-lg b', '模型图例名称', 'opt'],
  ['.m3d-lg span', '模型图例说明', 'opt'],
  ['.m3d-pin', '模型编号点', 'opt'],
  ['.m3d-hint', '模型操作提示', 'opt'],
];

let fail = 0;
const bad = (p, t, d) => { console.log(`  FAIL  [${p}] ${t} ${JSON.stringify(d)}`); fail++; };
const good = (p, t) => console.log(`  PASS  [${p}] ${t}`);

const IN_PAGE = async (TARGETS) => {

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
  // ---- 可旋转的 3D 模型 ----
  //
  // 这里只查「Python 侧算不出来、或算出来可能已过时」的东西：
  //   · 台面的**实际渲染尺寸**必须和 tools/models3d.py 里 STAGE_W/STAGE_H 的假设一致——
  //     自适配是按那两个数解的，CSS 一改（比如把 height 从 400 调成 340）断言就变陈旧了，
  //     页面上会表现为模型贴边甚至出血，而 Python 侧一无所知。
  //   · 编号点在**默认角度**下两两不重叠，并且都落在台面里；这与构建期断言互为交叉验证
  //     （构建期算的是生成期写进 HTML 的那个 left/top，这里量的是浏览器最后画出来的）。
  //   · 交互后模型仍在台面里：光验证默认角度不够，转到极限位置才是最容易出血的。
  const st = document.querySelector('#model .m3d-stage');
  if (st) {
    const r = st.getBoundingClientRect();
    const pins = [...st.querySelectorAll('.m3d-pin')];
    const at = (el) => {
      const b = el.getBoundingClientRect();
      return { cx: b.left + b.width / 2 - r.left, cy: b.top + b.height / 2 - r.top,
               w: b.width, h: b.height };
    };
    const ps = pins.map(at);
    let minD = Infinity;
    for (let i = 0; i < ps.length; i++) {
      for (let j = i + 1; j < ps.length; j++) {
        minD = Math.min(minD, Math.hypot(ps[i].cx - ps[j].cx, ps[i].cy - ps[j].cy));
      }
    }
    const faces = [...st.querySelectorAll('.m3d-f')];
    // 平滑着色的覆盖率：带 linear-gradient 的面片占比。
    // 「圆柱看起来是圆的」靠的就是它，而它失效时几何、包围盒、面片数全都不变——
    // 只有截图能看出来。所以在浏览器这一侧也量一次（构建期那条断言查的是 HTML 文本，
    // 这里查的是**真的生效的**计算样式，能顺带挡住 CSS 覆盖一类的问题）。
    const gradN = faces.filter(f => /linear-gradient/.test(getComputedStyle(f).backgroundImage)).length;
    // background-origin 必须是 border-box：默认的 padding-box 会让渐变只铺到内容区，
    // 最外那 1px 露出平色的 background-color，十个像素宽的面片上就是一条清楚的竖线，
    // 一圈下来正好把连续曲面又切回棱柱。它写在 CSS 里，只有这里能验。
    const origins = new Set(faces.map(f => getComputedStyle(f).backgroundOrigin));
    const sh = st.querySelector('.m3d-shadow i');
    const shb = sh ? sh.getBoundingClientRect() : null;
    out.model = {
      w: Math.round(r.width), h: Math.round(r.height),
      faces: faces.length,
      gradN,
      origins: [...origins],
      shadow: shb ? { w: Math.round(shb.width), h: Math.round(shb.height),
                      cx: Math.round(shb.left + shb.width / 2 - r.left),
                      cy: Math.round(shb.top + shb.height / 2 - r.top) } : null,
      pins: pins.length,
      minPinDist: ps.length > 1 ? +minD.toFixed(1) : null,
      pinsInside: ps.every(q => q.cx > 8 && q.cx < r.width - 8 && q.cy > 8 && q.cy < r.height - 8),
      offCount: pins.filter(el => el.classList.contains('off')).length,
      k: getComputedStyle(st).getPropertyValue('--m3d-k').trim(),
    };
  }
  const road = document.querySelector('#model .m3d-road');
  if (road) {
    // ⚠️ 一切都锁到**第一个** #model .m3d 里。收口页有两个模型，
    // 不锁的话部件分组会被两边的加在一起（实测 54 个），快照也会数成 10 张。
    const mroot = document.querySelector('#model .m3d');
    const steps = [...road.querySelectorAll('.m3d-rs')];
    const parts = [...mroot.querySelectorAll('.m3d-stage:not(.m3d-mini) .m3d-p')];
    out.road = {
      steps: steps.length,
      groups: parts.map(e => e.getAttribute('data-g') || ''),
      claimed: steps.map(b => (b.getAttribute('data-g') || '').split('|').filter(Boolean)),
      minis: mroot.querySelectorAll('.m3d-mini').length,
      hasStrip: !!mroot.querySelector('.m3d-strip'),
    };
  }
  return out;
};

// 星场亮度：把背景图按页面里的同一底色合成，再按 32×32 区块取平均，量**文字所在区域**里
// 最亮的块与最弱那档文字色的对比度。
//
// ⚠️ 三个关键点，都踩过：
//  1. 逐像素取高分位是错的——那样抓到的是几颗亮星（点可以到 1.0），而文字并不会正好压在星点上。
//     真正决定可读性的是「那一带的底色有多亮」，所以要按区块取平均。
//  2. **必须按真实的 background-position 取景。** 窄屏下 cover 只露出星场图的约 1/3 宽，
//     取错了区域会量到星云那一侧，得出「窄屏只有 3.95:1」的假结论——实际文字坐的是纯暗底 6:1。
//     CSS 会把 left 算成 "0% 50%"，所以不能按字符串匹配 left/right，要按百分比语义还原。
//  3. 所以这个函数要在**多个宽度**上跑：桌面取景和窄屏取景完全是两块区域。
const SKY_IN_PAGE = async () => {
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lumRGB = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const parse = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const q = m[1].split(',').map(Number);
    return { r: q[0], g: q[1], b: q[2], a: q.length > 3 ? q[3] : 1 };
  };
  const hero = document.querySelector('.hero');
  const sky = document.querySelector('.hero .sky');
  if (!hero || !sky) return null;
  const cs = getComputedStyle(sky);
  const mm = /url\(["']?([^"')]+)["']?\)/.exec(cs.backgroundImage || '');
  if (!mm) return null;
  const img = new Image();
  img.src = mm[1];
  await img.decode();
  const box = hero.getBoundingClientRect();
  const cv = document.createElement('canvas');
  cv.width = img.naturalWidth; cv.height = img.naturalHeight;
  const g = cv.getContext('2d');
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, cv.width, cv.height).data;
  const W = cv.width, H = cv.height;
  const scale = Math.max(box.width / W, box.height / H);
  const dw = W * scale, dh = H * scale;
  // 百分比语义：pos 形如 "0% 50%" / "100% 50%"
  const frac = (t) => (t === 'left' || t === 'top') ? 0 : (t === 'right' || t === 'bottom') ? 1
    : (t === 'center') ? 0.5 : (parseFloat(t) || 0) / 100;
  const [pf, qf] = (cs.backgroundPosition || '50% 50%').split(/\s+/).map(frac);
  const ox = pf * (box.width - dw);
  const oy = qf * (box.height - dh);

  const ti = hero.querySelector('.hero-in').getBoundingClientRect();
  const base = parse(getComputedStyle(hero).backgroundColor) || { r: 43, g: 58, b: 75 };
  const textEl = hero.querySelector('.meta span') || hero.querySelector('.dek') || hero;
  const tc = parse(getComputedStyle(textEl).color) || { r: 238, g: 243, b: 248 };

  const x0 = Math.max(0, Math.round((ti.left - box.left - ox) / scale));
  const y0 = Math.max(0, Math.round((ti.top - box.top - oy) / scale));
  const x1 = Math.min(W, Math.round((ti.right - box.left - ox) / scale));
  const y1 = Math.min(H, Math.round((ti.bottom - box.top - oy) / scale));
  const B = 32, blocks = [];
  for (let by = y0; by + B <= y1; by += B) {
    for (let bx = x0; bx + B <= x1; bx += B) {
      let sum = 0, n = 0;
      for (let y = by; y < by + B; y += 2) {
        for (let x = bx; x < bx + B; x += 2) {
          const i = (y * W + x) * 4;
          const a = d[i + 3] / 255;
          sum += lumRGB(d[i] * a + base.r * (1 - a),
                        d[i + 1] * a + base.g * (1 - a),
                        d[i + 2] * a + base.b * (1 - a));
          n++;
        }
      }
      blocks.push(sum / n);
    }
  }
  blocks.sort((x, y) => x - y);
  const lt = lumRGB(tc.r, tc.g, tc.b);
  const R = (l) => (Math.max(l, lt) + 0.05) / (Math.min(l, lt) + 0.05);
  const at = (q) => blocks[Math.min(Math.floor(q * blocks.length), blocks.length - 1)];
  return { src: mm[1].split('/').pop(), blocks: blocks.length, pos: cs.backgroundPosition,
           p50: +R(at(0.5)).toFixed(2), p99: +R(at(0.99)).toFixed(2),
           max: +R(blocks[blocks.length - 1]).toFixed(2) };
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
    // 星场亮度：桌面取景与窄屏取景是两块完全不同的区域，两个宽度都要量
    for (const [w, h, who] of [[1366, 900, '桌面'], [390, 844, '窄屏']]) {
      await page.setViewportSize({ width: w, height: h });
      await page.waitForTimeout(350);
      const sc = await page.evaluate(SKY_IN_PAGE);
      if (!sc) { bad(p, `${who}星场取不到`, sc); continue; }
      if (sc.p99 < 4.5) bad(p, `${who}星场文字区对比度不足`, sc);
      else good(p, `${who}星场亮度安全（${sc.src} 取景 ${sc.pos} 区块 50% ${sc.p50}:1 / 99% ${sc.p99}:1）`);
    }

    // 模型：台面尺寸必须与 tools/models3d.py 的假设一致，编号点默认角度下不重叠
    if (r.model) {
      // 台面尺寸这一条是**跨语言的交叉验证**：自适配在 Python 侧按 460×400 解，
      // 这里量浏览器真正渲染出来的尺寸。CSS 一改（比如 height 调成 340），
      // Python 侧的断言会静默变陈旧，只有这条能拦住。
      const M = r.model;
      const wantW = 460, wantH = 400;
      if (M.w !== wantW || M.h !== wantH) {
        bad(p, `模型台面渲染尺寸与 models3d.py 的假设不一致（要 ${wantW}×${wantH}）`, M);
      } else good(p, `模型台面 ${M.w}×${M.h}，与自适配假设一致（面片 ${M.faces}）`);
      if (M.pins && M.minPinDist < 20) bad(p, '模型编号点在默认角度下重叠', M);
      else if (M.pins) good(p, `模型编号点 ${M.pins} 个，最近间距 ${M.minPinDist}px（≥20）`);
      if (M.pins && !M.pinsInside) bad(p, '模型编号点转出台面', M);
      else if (M.pins) good(p, '模型编号点全在台面内');
      if (r.model.faces < 1) bad(p, '模型没有渲染出任何面片', M);
      // 平滑着色：至少六成面片要带渐变（六面体零件的面片没有渐变，所以不是 100%）
      if (M.faces >= 20 && M.gradN / M.faces < 0.6) {
        bad(p, `带平滑着色的面片只有 ${M.gradN}/${M.faces}（应 ≥60%）——`
               + '平滑着色失效了，圆柱会变回棱柱', M);
      } else if (M.faces >= 20) {
        good(p, `平滑着色覆盖 ${M.gradN}/${M.faces} 张面片`);
      }
      // ⚠️ background-origin 在**多层背景**下会返回逗号分隔的多值
      //（「纹理层, 渐变层」→ "border-box, border-box"），所以不能直接比字符串等值。
      const originOK = M.origins.every(v => v.split(',').every(x => x.trim() === 'border-box'));
      if (!originOK) {
        bad(p, '面片的 background-origin 不是 border-box（渐变铺不满，面片之间会出竖线）',
            M.origins);
      } else {
        good(p, '面片 background-origin:border-box（渐变铺满整个面片）');
      }
      // 接地影：尺寸与位置都要按模型投影算，不能跑到台面外
      if (!M.shadow) {
        bad(p, '模型缺少接地影（.m3d-shadow）', M);
      } else if (M.shadow.w < 12 || M.shadow.h < 8) {
        bad(p, '接地影太小', M.shadow);
      } else if (M.shadow.cx < 0 || M.shadow.cx > M.w || M.shadow.cy < 0 || M.shadow.cy > M.h) {
        bad(p, '接地影的中心跑到台面外', M.shadow);
      } else {
        good(p, `接地影 ${M.shadow.w}×${M.shadow.h} @(${M.shadow.cx},${M.shadow.cy})`);
      }
    } else if (p.indexOf('sections/') === 0) {
      bad(p, '板块页缺少可旋转模型（#model .m3d-stage）', {});
    }

    // ---- 「点一下放大」的交互 ----
    // 几何能不能装下由构建期的 Python 自检保证（那里能按旋转范围采样，比这里测得更全）；
    // 这里只查**状态机**：点了要进聚焦、只亮一个部件、其余编号点收起、Esc 要能还原。
    // 这几条正是最容易改坏的（比如 preventDefault 吃掉 click、capture 让 click 目标变成台面）。
    if (r.model) {
      // ⚠️ 先关掉平滑滚动。html{scroll-behavior:smooth} 下 scrollIntoView 是异步的，
      // 量完坐标再点，页面还在滚——坐标已经过期，点会落到别处，
      // 表现为「点编号点没反应」的假失败（拖拽测试也栽过同一个坑）。
      await page.addStyleTag({ content: 'html{scroll-behavior:auto!important}' });
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.evaluate(() => document.querySelector('#model').scrollIntoView());
      await page.waitForTimeout(600);
      // ⚠️ 必须锁定到**第一个**模型：收口页的 #model 里有两个模型，
      // 用 '#model .m3d-pin' 会把两边的编号点加在一起数（实测数出 8 个，实际各 7 个）。
      const FOCUS_IN_PAGE = () => {
        const root = document.querySelector('#model .m3d');
        if (!root) return null;
        return {
          focus: root.classList.contains('focus'),
          on: [...root.querySelectorAll('.m3d-p')].filter(e => e.classList.contains('on')).length,
          scaled: [...root.querySelectorAll('.m3d-p')]
            .filter(e => /^scale3d/.test(e.style.transform)).length,
          pinsShown: [...root.querySelectorAll('.m3d-pin')]
            .filter(e => !e.classList.contains('hid') && !e.classList.contains('off')).length,
          back: !root.querySelector('.m3d-back').hidden,
          // 聚焦时那个可见的编号点必须还在台面里（放大倍数会把锚点往外推）
          pinInside: (() => {
            const st = root.querySelector('.m3d-stage');
            const pn = [...root.querySelectorAll('.m3d-pin')]
              .find(e => !e.classList.contains('hid') && !e.classList.contains('off'));
            if (!st || !pn) return null;
            const a = st.getBoundingClientRect(), b = pn.getBoundingClientRect();
            const cx = b.left + b.width / 2 - a.left, cy = b.top + b.height / 2 - a.top;
            return cx > 10 && cx < a.width - 10 && cy > 10 && cy < a.height - 10;
          })(),
        };
      };
      const pinBox = await page.evaluate(() => {
        const root = document.querySelector('#model .m3d');
        const el = root && root.querySelector('.m3d-pin:not(.hid):not(.off)');
        if (!el) return null;
        const b = el.getBoundingClientRect();
        return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
      });
      if (!pinBox) {
        bad(p, '模型没有可点的编号点', r.model);
      } else {
        await page.mouse.click(pinBox.x, pinBox.y);
        await page.waitForTimeout(700);
        const during = await page.evaluate(FOCUS_IN_PAGE);
        if (!during || !during.focus || during.on !== 1 || during.scaled !== 1) {
          bad(p, '点编号点没有进入聚焦', during);
        } else if (!during.back) {
          bad(p, '聚焦后没有显示「返回全貌」', during);
        } else if (during.pinsShown > 1) {
          bad(p, '聚焦后其余编号点没有收起', during);
        } else if (during.pinInside === false) {
          bad(p, '聚焦后编号点被放大倍数推出台面', during);
        } else {
          good(p, `点击放大正常（聚焦 1 个部件、编号点收到 ${during.pinsShown} 个、显示返回按钮）`);
        }
        await page.keyboard.press('Escape');
        await page.waitForTimeout(700);
        const after = await page.evaluate(FOCUS_IN_PAGE);
        if (!after || after.focus || after.on || after.scaled || after.back) {
          bad(p, 'Esc 没有还原成全貌', after);
        } else {
          good(p, 'Esc 还原成全貌');
        }
      }
    }

    // ---- 3D 演示路线图 ----
    // 构建期已经断言过「分组不遗漏、不重复、渲染出来的文本里分组和部件对得上」。
    // 这里补的是**只有浏览器才知道的事**：懒建的快照有没有真的建出来、
    // 点某一步到底藏掉了哪些零件、快照里的模型有没有出框、拖动会不会带动主模型。
    if (r.road) {
      const R = r.road;
      const live = [...new Set(R.groups.filter(Boolean))];
      const flat = R.claimed.reduce((a, b) => a.concat(b), []);
      const miss = live.filter(g => flat.indexOf(g) < 0);
      const extra = flat.filter(g => live.indexOf(g) < 0);
      const dup = [...new Set(flat.filter((g, i) => flat.indexOf(g) !== i))];
      if (R.steps < 3) bad(p, `演示路线图只有 ${R.steps} 步（至少 3 步）`, R);
      else if (miss.length) bad(p, `这些部件分组不属于任何一步：${miss.join('、')}`, R);
      else if (extra.length) bad(p, `路线图认领了模型里不存在的分组：${extra.join('、')}`, R);
      else if (dup.length) bad(p, `有分组被两步同时认领：${dup.join('、')}`, R);
      else if (R.minis !== R.steps) bad(p, `快照 ${R.minis} 张、里程碑 ${R.steps} 步，对不上`, R);
      else if (!R.hasStrip) bad(p, '有里程碑条却没有快照条', R);
      else good(p, `演示路线图 ${R.steps} 步 / ${live.length} 个部件分组 / ${R.minis} 张快照`);

      const ROAD_IN_PAGE = () => {
        const root = document.querySelector('#model .m3d');
        if (!root) return null;
        const strip = root.querySelector('.m3d-strip');
        const minis = [...root.querySelectorAll('.m3d-mini')];
        const shown = (el) => !el.classList.contains('off') && !el.classList.contains('hid')
                             && getComputedStyle(el).visibility !== 'hidden';
        const parts = [...root.querySelectorAll('.m3d-stage:not(.m3d-mini) .m3d-p')];
        // 快照里的模型不许出框：逐张比外接矩形与台面
        let outMax = 0, minW = 1e9;
        const counts = [];
        minis.forEach(m => {
          const b = m.getBoundingClientRect();
          counts.push(m.querySelectorAll('.m3d-p').length);
          minW = Math.min(minW, b.width);
          let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
          m.querySelectorAll('.m3d-f').forEach(f => {
            const q = f.getBoundingClientRect();
            x0 = Math.min(x0, q.left); x1 = Math.max(x1, q.right);
            y0 = Math.min(y0, q.top); y1 = Math.max(y1, q.bottom);
          });
          if (x0 < 1e8) outMax = Math.max(outMax, b.left - x0, x1 - b.right, b.top - y0, y1 - b.bottom);
        });
        const snaps = root.querySelector('.m3d-snaps');
        const mainWorld = root.querySelector('.m3d-world');
        const ry = mainWorld ? mainWorld.style.getPropertyValue('--ry') : '';
        // 图例项只有编号点对应的那几个（几十个部件里只有 4~7 个有图例），
        // 所以「禁用了几项」不能拿来跟「藏掉几个部件」比，只能比「该禁的禁了没有」
        const hiddenIdx = new Set(parts.filter(e => !shown(e)).map(e => e.getAttribute('data-i')));
        const legend = [...root.querySelectorAll('.m3d-lb')];
        const worlds = minis.map(m => m.querySelector('.m3d-world'));
        return {
          // ⚠️ 「建好了」要连台面里的 world 一起看：strip 不 hidden 只说明克隆跑过了，
          // 而下面每一处都要读 mini 里的 world，拿到 null 会在页面里直接抛异常
          // （表现为整条校验中断，而不是一条 FAIL）。
          built: !!(strip && !strip.hidden && worlds.length && worlds.every(Boolean)),
          steps: root.querySelectorAll('.m3d-rs').length,
          parts: parts.length,
          visibleParts: parts.filter(shown).length,
          visiblePins: [...root.querySelectorAll('.m3d-pin')].filter(shown).length,
          legendDisabled: legend.filter(b => b.disabled).length,
          legendShouldDisable: legend.filter(b => hiddenIdx.has(b.getAttribute('data-part'))).length,
          miniCounts: counts,
          miniOut: Math.round(outMax),
          miniW: Math.round(minW),
          snapsOverflow: snaps ? snaps.scrollWidth - snaps.clientWidth : -1,
          ry,
          miniRy: worlds.map(w => (w ? w.style.getPropertyValue('--ry') : null)),
          // 这一层不许比它的容器宽。⚠️ **不能改成量整页横向溢出**：
          // 页面外层有裁剪，`.m3d-road` 涨到 790px 时 documentElement.scrollWidth
          // 仍然等于视口宽（实测过），量整页永远量不到。直接比宽度才有区分度。
          roadOver: Math.round(root.querySelector('.m3d-road').getBoundingClientRect().width
                               - root.getBoundingClientRect().width),
        };
      };

      // 先关掉平滑滚动：scrollIntoView 是异步的，量完坐标页面还在滚，量到的是过期值
      await page.addStyleTag({ content: 'html{scroll-behavior:auto!important}' });
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.evaluate(() => document.querySelector('#model .m3d-road').scrollIntoView());
      // 快照是懒建的（IntersectionObserver 触发才克隆），要等**克隆真的填进去**再量。
      // 固定 sleep 不够：页面大小不同、面片数差一倍，跑得快慢不一样。
      await page.waitForFunction(() => {
        const s = document.querySelector('#model .m3d .m3d-strip');
        return !!(s && !s.hidden && s.querySelector('.m3d-mini .m3d-world'));
      }, { timeout: 10000 }).catch(() => { /* 超时留给下面那条断言报出来 */ });
      await page.evaluate(() => window.scrollBy(0, 240));
      await page.waitForTimeout(500);

      const r0 = await page.evaluate(ROAD_IN_PAGE);
      if (!r0 || !r0.built) {
        bad(p, '快照条没有建出来（懒建的 IntersectionObserver 没触发）', r0);
      } else {
        if (r0.snapsOverflow > 1) {
          bad(p, `快照条横向溢出 ${r0.snapsOverflow}px（这一步应当排满一行）`, r0);
        }
        if (r0.miniCounts.some(n => !n)) {
          bad(p, '有快照台面是空的（克隆没填进去）', r0.miniCounts);
        } else if (r0.visibleParts !== r0.parts) {
          bad(p, `初始状态就藏掉了 ${r0.parts - r0.visibleParts} 个部件`, r0);
        } else {
          // 点中间那一步：主模型上可见的部件数必须正好等于第 k 张快照里克隆下来的部件数。
          // 这是**两条独立路径的交叉验证**——一边是运行期按 data-g 过滤 .off，
          // 一边是构建期按同一步切出来的面片集合，两边算错了就会对不上。
          const mid = Math.floor(r0.steps / 2);
          await page.evaluate((i) => {
            document.querySelectorAll('#model .m3d .m3d-rs')[i].click();
          }, mid);
          await page.waitForTimeout(800);
          const rk = await page.evaluate(ROAD_IN_PAGE);
          const want = rk.miniCounts[mid];
          if (rk.visibleParts !== want) {
            bad(p, `点第 ${mid + 1} 步后应显示 ${want} 个部件，实际 ${rk.visibleParts}`,
                { want, rk });
          } else if (rk.visibleParts >= rk.parts) {
            bad(p, `点第 ${mid + 1} 步没有藏掉任何部件（逐步装配没生效）`, rk);
          } else {
            good(p, `逐步装配正常（第 ${mid + 1} 步 ${rk.visibleParts}/${rk.parts} 个部件，`
                    + `编号点收至 ${rk.visiblePins} 个、图例禁用 ${rk.legendDisabled} 项）`);
          }
          if (rk.legendDisabled !== rk.legendShouldDisable) {
            bad(p, `图例禁用项数不对：该禁 ${rk.legendShouldDisable} 项、实际禁了 `
                   + `${rk.legendDisabled} 项（藏起来的部件的图例必须一起禁用，`
                   + '否则点它会「放大」到一个看不见的东西）', rk);
          }
          if (rk.miniOut > 2) bad(p, `快照里的模型出框 ${rk.miniOut}px`, rk);
          else good(p, `快照模型全在台面内（最小台面宽 ${rk.miniW}px、出框 ${rk.miniOut}px）`);
          if (!rk.miniRy.length || !rk.miniRy.every(v => v === rk.ry)) {
            bad(p, '快照的视角没有跟主模型同步', rk);
          } else {
            good(p, `快照视角与主模型同步（--ry ${rk.ry}）`);
          }
          await page.evaluate(() => document.querySelector('#model .m3d .m3d-road-all').click());
          await page.waitForTimeout(500);
          const ra = await page.evaluate(ROAD_IN_PAGE);
          if (ra.visibleParts !== ra.parts) bad(p, '点「全貌」没有把部件全恢复', ra);
          else good(p, '「全貌」恢复全部部件');

          // 拖动任意一张快照，所有快照与主模型一起转
          const miniBox = await page.evaluate(() => {
            const m = document.querySelector('#model .m3d-mini');
            if (!m) return null;
            const b = m.getBoundingClientRect();
            return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
          });
          if (miniBox) {
            const before = (await page.evaluate(ROAD_IN_PAGE)).ry;
            await page.mouse.move(miniBox.x, miniBox.y);
            await page.mouse.down();
            await page.mouse.move(miniBox.x + 70, miniBox.y, { steps: 6 });
            await page.mouse.up();
            await page.waitForTimeout(400);
            const after = await page.evaluate(ROAD_IN_PAGE);
            if (after.ry === before) bad(p, '拖动快照没有带动主模型旋转', after);
            else if (!after.miniRy.every(v => v === after.ry)) {
              bad(p, '拖动之后快照与主模型的视角不一致', after);
            } else {
              good(p, `拖动快照同步旋转（--ry ${before} → ${after.ry}）`);
            }
          }

          // 窄屏：快照条建完之后，路线图与快照条都不许比容器宽
          //（快照本身在 .m3d-snaps 里横滚，那是设计好的）
          for (const w of [390, 700]) {
            await page.setViewportSize({ width: w, height: 844 });
            await page.evaluate(() => document.querySelector('#model .m3d-road')
              .scrollIntoView({ block: 'start' }));
            await page.waitForTimeout(400);
            const rn = await page.evaluate(ROAD_IN_PAGE);
            if (rn.roadOver > 1) {
              bad(p, `${w}px 下路线图比容器宽 ${rn.roadOver}px`
                     + '（快照条必须能缩到容器宽，横向滚动交给它自己的 overflow-x——'
                     + '少了 min-width:0 时这里会是 790px 量级的差）', rn);
            } else {
              good(p, `${w}px 下路线图与快照条都没涨出容器`);
            }
          }
        }
      }
    }

    await page.close();
    console.log('');
  }

  await browser.close();
  console.log(fail ? `==> 视觉校验失败 ${fail} 项` : '==> 视觉校验全部通过');
  process.exit(fail ? 1 : 0);
})();
