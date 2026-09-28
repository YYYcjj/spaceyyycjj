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

  /* ---------- 8. 可拖拽旋转的 3D 模型 ----------
     渐进增强，三条底线：

       · **不跑 JS 也是对的。** 编号点的 left/top 是构建期按默认角度算好写进 HTML 的，
         所以禁用脚本、爬虫、以及**打印**看到的都是正确的一帧；JS 只负责让它能转。
       · **打印前必须复位。** 自转是 rAF 驱动的，不拦的话会打出转到一半的样子。
       · **编号点会互压，得自己解。** 模型转到背面时，前后两个标注必然擦肩而过——
         这在坐标上无解。所以每帧按序号优先级把撞上的点淡出（序号小的留下），
         阈值 20px 与 CSS 里的圆点直径一致。

     投影公式与 tools/models3d.py 里的 _proj() 必须保持同一套，改一处要改两处。 */
  (function () {
    var roots = Array.prototype.slice.call(document.querySelectorAll('[data-m3d]'));
    if (!roots.length) return;

    var PERSP = 1500;                       // 与 .m3d-stage 的 perspective 一致
    var RX_MIN = -52, RX_MAX = 8;           // 与 models3d.py 一致
    var RX_DEF = -18, RY_DEF = -32;
    var PIN_D = 20;                         // 与 .m3d-pin 的直径一致
    var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
    var spin = !(mq && mq.matches);

    function clamp(v) { return v < RX_MIN ? RX_MIN : (v > RX_MAX ? RX_MAX : v); }
    function dist(ax, ay, bx, by) { return Math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by)); }

    roots.forEach(function (root) {
      var stage = root.querySelector('.m3d-stage');
      var world = root.querySelector('.m3d-world');
      var pinBox = root.querySelector('.m3d-pins');
      if (!stage || !world) return;

      var pins = pinBox
        ? Array.prototype.slice.call(pinBox.querySelectorAll('.m3d-pin')).map(function (el) {
            var a = (el.getAttribute('data-a') || '0,0,0').split(',');
            return { el: el, v: [parseFloat(a[0]), parseFloat(a[1]), parseFloat(a[2])] };
          })
        : [];

      var rx = RX_DEF, ry = RY_DEF, vry = 0, vrx = 0;
      var drag = null, hover = false, live = false, raf = 0;

      function project(v) {
        var a = ry * Math.PI / 180, b = rx * Math.PI / 180;
        var x = v[0], y = v[1], z = v[2];
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
        if (!pins.length) return;
        var placed = [];
        for (var i = 0; i < pins.length; i++) {
          var s = project(pins[i].v);
          var clash = false;
          for (var j = 0; j < placed.length; j++) {
            if (dist(s[0], s[1], placed[j][0], placed[j][1]) < PIN_D) { clash = true; break; }
          }
          pins[i].el.style.left = 'calc(50% + ' + s[0].toFixed(1) + 'px)';
          pins[i].el.style.top = 'calc(50% + ' + s[1].toFixed(1) + 'px)';
          if (clash !== pins[i].el.classList.contains('off')) {
            pins[i].el.classList.toggle('off', clash);
          }
          if (!clash) placed.push(s);
        }
      }

      function loop() {
        raf = 0;
        if (!live) return;
        if (Math.abs(vry) > 0.02 || Math.abs(vrx) > 0.02) {
          ry += vry;
          rx = clamp(rx + vrx);
          vry *= 0.93;
          vrx *= 0.93;
        } else if (spin && !drag && !hover) {
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
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { stop(); } else { live = true; start(); }
      });

      stage.addEventListener('mouseenter', function () { hover = true; });
      stage.addEventListener('mouseleave', function () { hover = false; });
      // 键盘用户聚焦时也停自转，否则一边按键一边被动画推走
      stage.addEventListener('focus', function () { hover = true; });
      stage.addEventListener('blur', function () { hover = false; });

      stage.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        drag = { x: e.clientX, y: e.clientY, id: e.pointerId };
        vry = 0; vrx = 0;
        stage.classList.add('dragging');
        if (stage.setPointerCapture) {
          try { stage.setPointerCapture(e.pointerId); } catch (_e) { /* 忽略 */ }
        }
        e.preventDefault();
      });
      stage.addEventListener('pointermove', function (e) {
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

      // 打印前回到默认视角（打印看到的必须是构建期算好的那一帧）
      window.addEventListener('beforeprint', function () {
        rx = RX_DEF; ry = RY_DEF; vry = 0; vrx = 0;
        paint();
      });

      paint();
    });
  })();
})();
