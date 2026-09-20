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
})();
