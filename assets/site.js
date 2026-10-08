/* ==========================================================================
   可回收火箭全景 · 交互脚本（无依赖）
   ========================================================================== */
(function () {
  'use strict';

  /* ---------- 1. 阅读进度条 ---------- */
  var bar = document.getElementById('progress');
  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var p = max > 0 ? (h.scrollTop || document.body.scrollTop) / max : 0;
    if (bar) bar.style.width = (p * 100).toFixed(2) + '%';

    var top = document.getElementById('totop');
    if (top) top.classList.toggle('show', (h.scrollTop || document.body.scrollTop) > 600);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- 2. 目录高亮（滚动监听） ---------- */
  var links = Array.prototype.slice.call(document.querySelectorAll('[data-toc]'));
  var sections = links
    .map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); })
    .filter(Boolean);

  function setActive(id) {
    links.forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('href') === '#' + id);
    });
  }

  if ('IntersectionObserver' in window && sections.length) {
    var visible = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting ? e.intersectionRatio : 0; });
      var best = null, bestR = 0;
      Object.keys(visible).forEach(function (k) {
        if (visible[k] > bestR) { bestR = visible[k]; best = k; }
      });
      if (best) setActive(best);
    }, { rootMargin: '-72px 0px -55% 0px', threshold: [0, 0.15, 0.4, 0.75, 1] });
    sections.forEach(function (s) { io.observe(s); });
  }

  /* ---------- 3. 首屏数字滚动 ---------- */
  var nums = Array.prototype.slice.call(document.querySelectorAll('[data-count]'));
  if ('IntersectionObserver' in window && nums.length) {
    var io2 = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        obs.unobserve(el);
        var target = parseFloat(el.getAttribute('data-count'));
        var dec = (el.getAttribute('data-dec') | 0);
        var dur = 900, t0 = null;
        function step(ts) {
          if (t0 === null) t0 = ts;
          var k = Math.min((ts - t0) / dur, 1);
          var eased = 1 - Math.pow(1 - k, 3);
          el.textContent = (target * eased).toFixed(dec);
          if (k < 1) requestAnimationFrame(step);
          else el.textContent = target.toFixed(dec);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    nums.forEach(function (n) { n.textContent = '0'; io2.observe(n); });
  }

  /* ---------- 4. 表格筛选（国际 / 国内 通用） ---------- */
  Array.prototype.slice.call(document.querySelectorAll('[data-filtergroup]')).forEach(function (group) {
    var name = group.getAttribute('data-filtergroup');
    var buttons = Array.prototype.slice.call(group.querySelectorAll('button[data-val]'));
    var targets = Array.prototype.slice.call(document.querySelectorAll('[data-group="' + name + '"]'));

    function apply(val) {
      buttons.forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-val') === val));
      });
      var shown = 0;
      targets.forEach(function (t) {
        var ok = val === 'all' || (t.getAttribute('data-val') || '').split(' ').indexOf(val) > -1;
        t.hidden = !ok;
        if (ok) shown++;
      });
      var empty = group.querySelector('.empty-hint');
      if (empty) empty.hidden = shown !== 0;
    }

    buttons.forEach(function (b) {
      b.addEventListener('click', function () { apply(b.getAttribute('data-val')); });
    });
    apply('all');

    // 支持 URL 锚点直接带筛选，例如 #cn?stage=5
    var m = /[?&]f=([a-z0-9]+)/i.exec(location.search);
    if (m) apply(m[1]);
  });

  /* ---------- 5. 回到顶部 ---------- */
  var top = document.getElementById('totop');
  if (top) {
    top.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ---------- 6. 图表入场动画 ---------- */
  var figs = Array.prototype.slice.call(document.querySelectorAll('[data-animate]'));
  if ('IntersectionObserver' in window && figs.length) {
    var io3 = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        obs.unobserve(e.target);
      });
    }, { threshold: 0.25 });
    figs.forEach(function (f) { io3.observe(f); });
  } else {
    figs.forEach(function (f) { f.classList.add('in'); });
  }

  /* ---------- 7. 进场动效（渐进增强，可关）----------
     两条安全线：
       · 类名是 JS 加的 —— 脚本没跑起来时页面照常全部可见；
       · 加一个兜底定时器 —— IntersectionObserver 万一不触发，也不能把内容永久藏起来。
     prefers-reduced-motion 下直接跳过，什么都不做。 */
  (function () {
    var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq && mq.matches) return;
    if (!('IntersectionObserver' in window)) return;

    var sel = '.hero, .kpis, .figure, .note, .board-grid, ol.judge, table.req';
    var targets = Array.prototype.slice.call(document.querySelectorAll(sel))
      .concat(Array.prototype.slice.call(document.querySelectorAll('section > h2, section > h3')));
    if (!targets.length) return;

    targets.forEach(function (el) { el.classList.add('reveal'); });

    function showAll() {
      targets.forEach(function (el) { el.classList.add('in'); });
    }

    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        obs.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.06 });

    targets.forEach(function (t) { io.observe(t); });

    // 兜底：4 秒后无论如何全部显示
    setTimeout(showAll, 4000);
    // 打印前也全部显示，免得打出半透明的图
    window.addEventListener('beforeprint', showAll);
  })();

  /* ---------- 7b. 打印前展开所有折叠块 ----------
     「零基础起步」通用手册是一块 <details>：屏幕上有折叠的理由（六千多字，
     展开会把领域内容淹掉），但纸上没有——打出一根点不开的标题条毫无意义。
     所以 beforeprint 全部展开、afterprint 还原用户原来的开合状态。 */
  (function () {
    var boxes = Array.prototype.slice.call(document.querySelectorAll('details'));
    if (!boxes.length) return;
    var was = [];
    window.addEventListener('beforeprint', function () {
      was = boxes.map(function (d) { return d.open; });
      boxes.forEach(function (d) { d.open = true; });
    });
    window.addEventListener('afterprint', function () {
      boxes.forEach(function (d, i) {
        if (typeof was[i] === 'boolean') d.open = was[i];
      });
      was = [];
    });
  })();

  /* ---------- 8. 可拖拽旋转的 3D 模型（含「点一下放大」） ----------
     渐进增强，四条底线：

       · **不跑 JS 也是对的。** 编号点的 left/top 是构建期按默认角度算好写进 HTML 的，
         所以禁用脚本、爬虫、以及**打印**看到的都是正确的一帧；JS 只负责让它能转。
       · **打印前必须复位视角。** 自转是 rAF 驱动的，不拦的话会打出转到一半的样子。
         （聚焦状态**不**复位——那是用户主动选的，打印应该与屏幕一致。）
       · **编号点会互压，得自己解。** 模型转到背面时，前后两个标注必然擦肩而过——
         这在坐标上无解。所以每帧按序号优先级把撞上的点淡出（序号小的留下），
         阈值 20px 与 CSS 里的圆点直径一致。
       · **拖动与点击要分开。** 位移超过 TAP 像素就按拖动处理，click 不再触发放大，
         否则每次转完模型都会顺手把某个部件放大，很烦。

     投影公式与 tools/models3d.py 里的 _proj() 必须保持同一套，改一处要改两处。 */
  (function () {
    var roots = Array.prototype.slice.call(document.querySelectorAll('[data-m3d]'));
    if (!roots.length) return;

    var PERSP = 1500;                       // 与 .m3d-stage 的 perspective 一致
    var RX_MIN = -52, RX_MAX = 8;           // 与 models3d.py 一致
    var RX_DEF = -18, RY_DEF = -32;
    var PIN_D = 20;                         // 与 .m3d-pin 的直径一致
    var TAP = 6;                            // 位移小于它才算「点击」
    var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    var spin = !(mq && mq.matches);

    function clamp(v) { return v < RX_MIN ? RX_MIN : (v > RX_MAX ? RX_MAX : v); }
    function dist(ax, ay, bx, by) { return Math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by)); }
    function num(s, d) { var v = parseFloat(s); return isNaN(v) ? d : v; }

    roots.forEach(function (root) {
      var stage = root.querySelector('.m3d-stage');
      var world = root.querySelector('.m3d-world');
      var pinBox = root.querySelector('.m3d-pins');
      var back = root.querySelector('.m3d-back');
      if (!stage || !world) return;
      var parts = Array.prototype.slice.call(world.querySelectorAll('.m3d-p'));
      var links = Array.prototype.slice.call(root.querySelectorAll('.m3d-lb'));
      if (!parts.length) return;

      // 聚焦参数是构建期算好写在 data 上的：data-c 是部件中心（CSS px 坐标）、data-f 是放大倍数
      var focus = parts.map(function (el) {
        var c = (el.getAttribute('data-c') || '0,0,0').split(',');
        return { c: [num(c[0], 0), num(c[1], 0), num(c[2], 0)],
                 f: num(el.getAttribute('data-f'), 1),
                 base: el.style.transform };   // 未聚焦时的定位，退出时要还原
      });

      var pins = (pinBox
        ? Array.prototype.slice.call(pinBox.querySelectorAll('.m3d-pin'))
        : []).map(function (el) {
          var a = (el.getAttribute('data-a') || '0,0,0').split(',');
          return { el: el, v: [num(a[0], 0), num(a[1], 0), num(a[2], 0)],
                   part: num(el.getAttribute('data-part'), 0), show: true, vis: true };
        });

      // ---------------- 3D 演示路线图 ----------------
      // 里程碑条：第 i 步显示「前 i 步涉及的分组」。分组名写死在构建期（每个
      // .m3d-p 上的 data-g），运行期只做查表——不在这里做任何几何推算，
      // 所以「哪一步出现哪些零件」这件事只有一个来源，不会和构建期说的不一样。
      var road = root.querySelector('[data-road]');
      var stepBtns = road ? Array.prototype.slice.call(road.querySelectorAll('.m3d-rs')) : [];
      var allBtn = road ? road.querySelector('.m3d-road-all') : null;
      var playBtn = road ? road.querySelector('.m3d-road-play') : null;
      var strip = root.querySelector('[data-strip]');
      var stepGroups = stepBtns.map(function (b) {
        return (b.getAttribute('data-g') || '').split('|');
      });
      // 每个部件属于第几步。-1 = 不属于任何一步；没有路线图的模型会全是 -1，
      // 那时 visibleAt() 永远返回 true，整套过滤等于不发生。
      var stepOf = parts.map(function (el) {
        var g = el.getAttribute('data-g') || '';
        for (var s = 0; s < stepGroups.length; s++) {
          if (stepGroups[s].indexOf(g) >= 0) return s;
        }
        return -1;
      });
      var step = -1;                        // -1 = 全貌
      var playT = 0;
      var miniWorlds = [];
      var built = false;

      function visibleAt(j, i) {
        return i < 0 || (stepOf[j] >= 0 && stepOf[j] <= i);
      }

      function stopPlay() {
        if (playT) { clearInterval(playT); playT = 0; }
        if (playBtn) playBtn.setAttribute('aria-pressed', 'false');
      }

      function applyStep(i, animate) {
        if (!stepBtns.length) return;
        step = (i >= 0 && i < stepBtns.length) ? i : -1;
        var newly = [];
        parts.forEach(function (el, j) {
          var vis = visibleAt(j, step);
          el.classList.toggle('off', !vis);
          el.classList.remove('new');
          if (animate && step >= 0 && stepOf[j] === step) newly.push(el);
        });
        // 新增的那一批错开一帧再加 .new：同一帧里「加类 + 起动画」在有些浏览器上
        // 不会重新开始动画（元素还带着上一轮的样式缓存），差一帧最省事。
        if (newly.length) {
          requestAnimationFrame(function () {
            newly.forEach(function (el) { el.classList.add('new'); });
          });
        }
        stepBtns.forEach(function (b, k) {
          b.setAttribute('aria-pressed', k === step ? 'true' : 'false');
        });
        if (allBtn) allBtn.setAttribute('aria-pressed', step < 0 ? 'true' : 'false');
        // 图例项要跟着禁用：点一个还没装上的部件的图例，会「放大」到一个看不见的东西
        links.forEach(function (b) {
          var vis = visibleAt(num(b.getAttribute('data-part'), 0), step);
          b.disabled = !vis;
        });
        pins.forEach(function (p) { p.vis = visibleAt(p.part, step); });
        // 正在放大的那个部件如果被这一步藏起来了，退回全貌——不然会卡在空台面上
        if (idx >= 0 && !visibleAt(idx, step)) setFocus(-1);
        paint();
      }

      // 各步快照：**从主模型的 world 克隆**，按步过滤。默认 hidden（没有 JS 时
      // 只是一排空台面），第一次进入视口或打印前才建。
      function buildStrip() {
        if (built || !strip || !stepBtns.length) return;
        built = true;
        var shadow = stage.querySelector('.m3d-shadow');
        Array.prototype.slice.call(strip.querySelectorAll('.m3d-mini'))
          .forEach(function (mini) {
            var si = num(mini.getAttribute('data-snap'), 0);
            var w = world.cloneNode(true);
            // 角度与缩放交回 CSS：--rx/--ry 落回 var() 的默认值，--m3d-k 取 .m3d-mini 的那一档
            w.removeAttribute('style');
            Array.prototype.slice.call(w.querySelectorAll('.m3d-p'))
              .forEach(function (el, j) {
                el.className = 'm3d-p';
                el.removeAttribute('data-f');
                el.removeAttribute('data-c');
                // ⚠️ transform 取 focus[j].base，不能抄 el.style.transform ——
                // 克隆时主模型可能正停在「放大某个部件」的状态上，那个部件的
                // transform 已经被换成 scale3d 了，照抄会让快照里少一个部件的形状。
                el.style.transform = (focus[j] && focus[j].base) || '';
                if (!visibleAt(j, si)) el.parentNode.removeChild(el);
              });
            if (shadow) mini.appendChild(shadow.cloneNode(true));
            mini.appendChild(w);
            miniWorlds.push(w);
            bindSpin(mini);
          });
        strip.removeAttribute('hidden');
      }

      // 拖动任意一个快照 = 转所有快照 + 转主模型：角度是同一份状态，
      // 只是 paint() 把它广播给每一个 world。
      function bindSpin(el) {
        var d = null;
        el.addEventListener('pointerdown', function (e) {
          if (e.pointerType === 'mouse' && e.button !== 0) return;
          d = { x: e.clientX, y: e.clientY, id: e.pointerId };
          vry = 0; vrx = 0;
          el.classList.add('dragging');
          if (el.setPointerCapture) {
            try { el.setPointerCapture(e.pointerId); } catch (_e) { /* 忽略 */ }
          }
        });
        el.addEventListener('pointermove', function (e) {
          if (!d || e.pointerId !== d.id) return;
          ry += (e.clientX - d.x) * 0.45;
          rx = clamp(rx - (e.clientY - d.y) * 0.35);
          d.x = e.clientX;
          d.y = e.clientY;
          paint();
        });
        function up(e) {
          if (!d || (e && e.pointerId !== d.id)) return;
          d = null;
          el.classList.remove('dragging');
        }
        el.addEventListener('pointerup', up);
        el.addEventListener('pointercancel', up);
        el.addEventListener('lostpointercapture', up);
      }

      stepBtns.forEach(function (b, k) {
        b.addEventListener('click', function () {
          stopPlay();
          applyStep(step === k ? -1 : k, true);
        });
      });
      if (allBtn) allBtn.addEventListener('click', function () { stopPlay(); applyStep(-1, false); });
      if (playBtn) {
        playBtn.addEventListener('click', function () {
          if (playT) { stopPlay(); return; }
          playBtn.setAttribute('aria-pressed', 'true');
          var n = 0;
          applyStep(0, true);
          playT = setInterval(function () {
            n += 1;
            if (n >= stepBtns.length) { stopPlay(); return; }
            applyStep(n, true);
          }, 1600);
        });
      }

      var rx = RX_DEF, ry = RY_DEF, vry = 0, vrx = 0;
      var drag = null, hover = false, live = false, raf = 0;
      var idx = -1;                         // -1 = 全貌；否则是聚焦的部件序号
      var tap = null, animT = 0, downEl = null;

      function project(v) {
        var x = v[0], y = v[1], z = v[2];
        // 聚焦：先把点相对部件中心缩放平移，与 .m3d-world 的 transform 完全对应。
        // 编号点那一层只负责乘 --m3d-k（它的 scale），所以这里不能再乘 k。
        if (idx >= 0) {
          var f = focus[idx];
          x = (x - f.c[0]) * f.f;
          y = (y - f.c[1]) * f.f;
          z = (z - f.c[2]) * f.f;
        }
        var a = ry * Math.PI / 180, b = rx * Math.PI / 180;
        var x2 = x * Math.cos(a) + z * Math.sin(a);
        var z2 = -x * Math.sin(a) + z * Math.cos(a);
        var y2 = y * Math.cos(b) - z2 * Math.sin(b);
        var z3 = y * Math.sin(b) + z2 * Math.cos(b);
        var k = PERSP / Math.max(PERSP - z3, 1);
        return [x2 * k, y2 * k];
      }

      function paint() {
        world.style.setProperty('--rx', rx.toFixed(2) + 'deg');
        world.style.setProperty('--ry', ry.toFixed(2) + 'deg');
        // 快照跟着一起转：角度只有这一份，广播出去，所以「拖任意一个，全都同步」
        for (var m = 0; m < miniWorlds.length; m++) {
          miniWorlds[m].style.setProperty('--rx', rx.toFixed(2) + 'deg');
          miniWorlds[m].style.setProperty('--ry', ry.toFixed(2) + 'deg');
        }
        if (!pins.length) return;
        var placed = [];
        // 聚焦时编号点也会跟着放大倍数往外推：小部件（采掘头、栅格舵）的放大倍数被
        // 上限截到 6，锚点又离部件中心远，乘完就飞出台面了。所以给屏幕半径设个上限，
        // 超了就沿同一方向拉回来——标注留在看得见的地方，指哪算哪。
        var maxR = idx >= 0
          ? Math.min(stage.clientWidth, stage.clientHeight) / 2 - 26 : 0;
        for (var i = 0; i < pins.length; i++) {
          var p = pins[i];
          // show 是「聚焦过滤」，vis 是「路线图过滤」——两个条件都成立才画出来
          var ok = p.show && p.vis;
          var s = ok ? project(p.v) : [0, 0];
          if (maxR > 0) {
            var rr = Math.sqrt(s[0] * s[0] + s[1] * s[1]);
            if (rr > maxR) { s = [s[0] * maxR / rr, s[1] * maxR / rr]; }
          }
          var clash = false;
          if (ok) {
            for (var j = 0; j < placed.length; j++) {
              if (dist(s[0], s[1], placed[j][0], placed[j][1]) < PIN_D) { clash = true; break; }
            }
          }
          p.el.style.left = 'calc(50% + ' + s[0].toFixed(1) + 'px)';
          p.el.style.top = 'calc(50% + ' + s[1].toFixed(1) + 'px)';
          p.el.classList.toggle('hid', !ok);
          p.el.classList.toggle('off', ok && clash);
          // 收起来的点必须退出 Tab 序列，否则键盘用户会 Tab 到一个看不见的按钮上
          p.el.tabIndex = (ok && !clash) ? 0 : -1;
          if (ok && !clash) placed.push(s);
        }
      }

      function setFocus(i) {
        if (!(i >= 0 && i < parts.length)) i = -1;
        idx = i;
        var f = i >= 0 ? focus[i] : null;
        root.classList.toggle('focus', i >= 0);
        parts.forEach(function (el, j) { el.classList.toggle('on', j === i); });
        links.forEach(function (b) {
          b.setAttribute('aria-pressed',
            (+b.getAttribute('data-part') === i && i >= 0) ? 'true' : 'false');
        });
        pins.forEach(function (p) {
          p.show = i < 0 || p.part === i;
          p.el.setAttribute('aria-pressed', (i >= 0 && p.part === i) ? 'true' : 'false');
        });
        // 放大 = 把目标部件自己的 transform 从「摆到自己的位置」换成「缩放到台面中心」。
        // 部件的几何是绕自身原点建的，所以丢掉 translate 就等于把中心挪到世界原点。
        parts.forEach(function (el, j) {
          el.style.transform = (j === i) ? 'scale3d(' + f.f + ',' + f.f + ',' + f.f + ')'
                                         : focus[j].base;
        });
        if (back) back.hidden = i < 0;
        vry = 0; vrx = 0;
        // 过渡只在这一下打开：常驻的话拖动时每帧都要追一个 0.5s 动画，手感会很黏
        root.classList.add('anim');
        if (animT) clearTimeout(animT);
        animT = setTimeout(function () { root.classList.remove('anim'); animT = 0; }, 560);
        paint();
      }
      function toggle(i) { setFocus(i === idx ? -1 : i); }

      function loop() {
        raf = 0;
        if (!live) return;
        if (Math.abs(vry) > 0.02 || Math.abs(vrx) > 0.02) {
          ry += vry;
          rx = clamp(rx + vrx);
          vry *= 0.93;
          vrx *= 0.93;
        } else if (spin && !drag && !hover && idx < 0) {
          ry += 0.16;                       // 自转：慢到不干扰阅读，快到看得出是 3D
        }
        paint();
        raf = requestAnimationFrame(loop);
      }
      function start() { if (live && !raf) raf = requestAnimationFrame(loop); }
      function stop() { live = false; if (raf) { cancelAnimationFrame(raf); raf = 0; } }

      // 只在可见时跑动画；切走标签页也停
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (es) {
          es.forEach(function (e) {
            if (e.isIntersecting) { live = true; start(); }
            else { stop(); }
          });
        }, { rootMargin: '120px 0px', threshold: 0 }).observe(stage);
      } else {
        live = true; start();
      }
      // 快照那一层懒建：要克隆五个模型的全部面片，放在首屏会白白拖慢加载。
      // ⚠️ 观察的是 root 而不是 strip —— strip 默认 hidden，hidden 的元素没有盒子，
      // 观察它永远不会触发（IntersectionObserver 对 display:none 的目标不报交集）。
      if (strip && stepBtns.length) {
        if ('IntersectionObserver' in window) {
          var ioStrip = new IntersectionObserver(function (es) {
            es.forEach(function (e) {
              if (e.isIntersecting) { buildStrip(); ioStrip.disconnect(); }
            });
          }, { rootMargin: '320px 0px', threshold: 0 });
          ioStrip.observe(root);
        } else {
          buildStrip();
        }
      }
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { stop(); } else { live = true; start(); }
      });

      stage.addEventListener('mouseenter', function () { hover = true; });
      stage.addEventListener('mouseleave', function () { hover = false; });
      // 键盘用户聚焦时也停自转，否则一边按键一边被动画推走
      stage.addEventListener('focus', function () { hover = true; });
      stage.addEventListener('blur', function () { hover = false; });

      // 点在按钮上时不启动拖动、也不 preventDefault——
      // preventDefault 会连带把 click 一起吃掉，编号点就点不动了
      function isCtrl(t) {
        return !!(t && t.closest && (t.closest('.m3d-pin') || t.closest('.m3d-back')));
      }

      stage.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        tap = { x: e.clientX, y: e.clientY, moved: false };
        // ⚠️ 必须记下 pointerdown 时的目标。下面一旦 setPointerCapture，
        // pointerup 会被重定向到 stage，于是 click 的目标也变成 stage——
        // 光看 e.target 就再也认不出点的是哪张面片了（实测「点部件放大」整条路径失效）。
        downEl = e.target;
        if (isCtrl(e.target)) return;
        drag = { x: e.clientX, y: e.clientY, id: e.pointerId };
        vry = 0; vrx = 0;
        stage.classList.add('dragging');
        if (stage.setPointerCapture) {
          try { stage.setPointerCapture(e.pointerId); } catch (_e) { /* 忽略 */ }
        }
        // ⚠️ **不要在这里 preventDefault()**。取消 pointerdown 会让浏览器连带抑制掉
        // 后续的兼容鼠标事件（mousedown / mouseup / **click**），于是「点部件放大」
        // 整条路径直接失效——而且不报任何错，只是点了没反应。
        // 拖动时不想选中文字的话，用 CSS 的 user-select:none 就够了。
      });
      stage.addEventListener('pointermove', function (e) {
        if (tap && dist(e.clientX, e.clientY, tap.x, tap.y) > TAP) tap.moved = true;
        if (!drag || e.pointerId !== drag.id) return;
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        drag.x = e.clientX; drag.y = e.clientY;
        ry += dx * 0.45;
        rx = clamp(rx - dy * 0.35);          // 往下拖 = 把顶面拉向自己
        vry = dx * 0.25; vrx = -dy * 0.19;   // 松手后的惯性
        paint();
      });
      function release(e) {
        if (!drag || (e && e.pointerId !== drag.id)) return;
        drag = null;
        stage.classList.remove('dragging');
      }
      stage.addEventListener('pointerup', release);
      stage.addEventListener('pointercancel', release);
      stage.addEventListener('lostpointercapture', release);

      // 点编号点 / 点部件 / 点图例 = 放大看它；再点一次或点空白 = 返回全貌
      stage.addEventListener('click', function (e) {
        var moved = tap && tap.moved;
        tap = null;
        var t = downEl || e.target;
        downEl = null;
        if (moved) return;
        if (t.closest && t.closest('.m3d-back')) return;   // 由按钮自己的监听处理
        var pin = t.closest && t.closest('.m3d-pin');
        if (pin) { toggle(num(pin.getAttribute('data-part'), 0)); return; }
        var part = t.closest && t.closest('.m3d-p');
        if (part) { toggle(num(part.getAttribute('data-i'), 0)); return; }
        if (idx >= 0) setFocus(-1);
      });

      links.forEach(function (b) {
        b.addEventListener('click', function () {
          toggle(num(b.getAttribute('data-part'), 0));
        });
      });
      if (back) back.addEventListener('click', function () { setFocus(-1); });

      // Esc 退出聚焦。绑在外层容器上——焦点可能落在编号点或图例按钮上
      root.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && idx >= 0) { setFocus(-1); }
      });

      stage.addEventListener('keydown', function (e) {
        var s = e.shiftKey ? 15 : 6;
        if (e.key === 'ArrowLeft') { ry -= s; }
        else if (e.key === 'ArrowRight') { ry += s; }
        else if (e.key === 'ArrowUp') { rx = clamp(rx + s); }
        else if (e.key === 'ArrowDown') { rx = clamp(rx - s); }
        else return;
        e.preventDefault();
        vry = 0; vrx = 0;
        paint();
      });

      var reset = root.querySelector('.m3d-reset');
      if (reset) {
        reset.addEventListener('click', function () {
          rx = RX_DEF; ry = RY_DEF; vry = 0; vrx = 0;
          paint();
        });
      }

      // 打印前回到默认视角（打印看到的必须是构建期算好的那一帧），
      // 并把默认藏着的快照条补出来——否则打出来少一整块内容
      window.addEventListener('beforeprint', function () {
        buildStrip();
        rx = RX_DEF; ry = RY_DEF; vry = 0; vrx = 0;
        paint();
      });

      paint();
    });
  })();
})();
