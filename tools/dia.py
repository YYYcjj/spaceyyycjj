# -*- coding: utf-8 -*-
"""二维概念图图元库。

和 iso.py 的分工：
    iso.py   画**立体**（装置、结构）——等轴测投影
    dia.py   画**关系**（过程、数值、层级）——二维示意

两类图共用同一套配色与版式规矩，所以放在一起看是一致的。
所有图都是固定画布的内联 SVG（默认 680×280），无外部依赖、可打印。

版式规矩（改图前必读）：
    1. 坐标直接用像素，左上角为原点，x 向右、y 向下。
       画布 680 宽在页面里会被缩放到容器宽度，所以**别指望按像素精确对齐**，
       留白宁多勿少。
    2. 每个 text 都要显式给 color；颜色用下面的语义常量，不要临时调色。
    3. 文字包围盒会被记录进 self._txt，交给 check_designs.py 自检
       「出框」与「互相重叠」——**手写像素坐标时最容易出的就是这两种错**。
    4. 图注不画进 SVG，放到外面的 <figcaption>（浏览器会换行，SVG 里不会）。
"""

MUTED = '#6f6f69'
INK = '#1c1c1a'
FAINT = '#9a9992'
LINE = '#e6e5e0'
LINE_S = '#cfcec8'

GREEN, GREEN_B, GREEN_BR = '#3b6d11', '#eaf3de', '#97c459'
BLUE, BLUE_B, BLUE_BR = '#185fa5', '#e6f1fb', '#85b7eb'
AMBER, AMBER_B, AMBER_BR = '#854f0b', '#faeeda', '#ef9f27'
RED, RED_B, RED_BR = '#a32d2d', '#fcebeb', '#f09595'
GRAY, GRAY_B, GRAY_BR = '#5f5e5a', '#f1efe8', '#b4b2a9'

# 语义色组：(主色, 填充, 边线)
S = {
    'ink':   (INK,   '#ffffff', INK),
    'gray':  (GRAY,  GRAY_B,  GRAY_BR),
    'blue':  (BLUE,  BLUE_B,  BLUE_BR),
    'green': (GREEN, GREEN_B, GREEN_BR),
    'amber': (AMBER, AMBER_B, AMBER_BR),
    'red':   (RED,   RED_B,   RED_BR),
}


def _f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def tw(text, size):
    """粗估文字像素宽度：CJK 按 1em、ASCII 按 0.55em。"""
    u = 0.0
    for ch in text:
        u += 1.0 if ord(ch) > 0x2E7F else 0.55
    return u * size


class Dia:
    def __init__(self, w=680, h=280):
        self.w, self.h = w, h
        self._ops = []
        self._txt = []          # 文字包围盒 (x0, y0, x1, y1)

    # ------------------------------------------------------------ 基础图元
    def rect(self, x, y, w, h, fill='#ffffff', stroke=LINE, sw=1, rx=7, op=None):
        o = f' opacity="{op}"' if op is not None else ''
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
        self._ops.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
                         f'rx="{_f(rx)}" fill="{fill}"{st}{o}/>')
        return self

    def line(self, x1, y1, x2, y2, color=MUTED, sw=1, dash=None, op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self._ops.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
                         f'stroke="{color}" stroke-width="{sw}"{d}{o} stroke-linecap="round"/>')
        return self

    def arrow(self, x1, y1, x2, y2, color=MUTED, sw=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self._ops.append(f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
                         f'stroke="{color}" stroke-width="{sw}"{d} marker-end="url(#da)" '
                         f'stroke-linecap="round"/>')
        return self

    def poly(self, pts, fill='#ffffff', stroke=LINE, sw=1, op=None):
        p = ' '.join(f'{_f(a)},{_f(b)}' for a, b in pts)
        st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ''
        o = f' opacity="{op}"' if op is not None else ''
        self._ops.append(f'<polygon points="{p}" fill="{fill}"{st}{o}/>')
        return self

    def curve(self, pts, color=BLUE, sw=1.8, dash=None, op=None):
        p = ' '.join(f'{_f(a)},{_f(b)}' for a, b in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self._ops.append(f'<polyline points="{p}" fill="none" stroke="{color}" '
                         f'stroke-width="{sw}"{d}{o} stroke-linejoin="round" stroke-linecap="round"/>')
        return self

    def area(self, pts, fill=BLUE_B, op=0.75, stroke=None):
        p = ' '.join(f'{_f(a)},{_f(b)}' for a, b in pts)
        st = f' stroke="{stroke}" stroke-width="1"' if stroke else ''
        self._ops.append(f'<polygon points="{p}" fill="{fill}"{st} opacity="{op}"/>')
        return self

    def dot(self, x, y, r=3.2, color=BLUE, ring='#ffffff'):
        self._ops.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="{color}" '
                         f'stroke="{ring}" stroke-width="1.4"/>')
        return self

    def text(self, x, y, s, size=11, color=INK, anchor='start', weight=400):
        if not s:
            return self
        wt = tw(s, size)
        x0 = x if anchor == 'start' else (x - wt if anchor == 'end' else x - wt / 2)
        self._txt.append((x0, y - size * 0.82, x0 + wt, y + size * 0.28))
        self._ops.append(f'<text x="{_f(x)}" y="{_f(y)}" fill="{color}" font-size="{_f(size)}" '
                         f'font-weight="{weight}" text-anchor="{anchor}">{s}</text>')
        return self

    # ------------------------------------------------------------ 高层模板
    def hbars(self, x0, y0, w, items, row=44, bar=13, cap=None):
        """横向条形对比。items: [(标签, 值文字, 0..1, 色键, 说明)]

        两个布局要点（都是踩过的）：
        - `row` 是**含说明行的总行高**，不是条的间距。传 38 时说明行会顶到下一行。
        - 数值右对齐到 x0+w（右侧预留 74px），不要紧跟条尾——条一长数值就被推出画布。
        """
        if cap:
            self.text(x0, y0 - 12, cap, 10.5, FAINT)
        y = y0
        for lab, val, frac, ck, note in items:
            main, fill, bd = S[ck]
            self.text(x0, y + 10, lab, 11.5, INK)
            bx = x0 + 150
            bw = w - 150 - 74
            self.rect(bx, y, bw, bar, '#fafaf8', LINE, 1, 3)
            self.rect(bx, y, max(bw * frac, 3), bar, fill, bd, 1, 3)
            self.text(x0 + w, y + 10.5, val, 11.5, main, 'end', 600)
            if note:
                self.text(x0, y + 26, note, 10.5, FAINT)
            y += row
        return self

    def series(self, x0, y0, w, h, xlabels, ylabels, lines, xname='', yname='',
               ymax=None, xlog=False, ylog=False):
        """折线图。lines: [(标签, [y...], 色键, dash)]；ylabels 为 y 轴刻度文字。

        底部占位：xlabels 在 y0+h+16、xname 在 y0+h+30，
        所以调用方要放说明文字时，y 必须 ≥ y0+h+48，否则会与 xname 叠在一起。
        """
        n = len(xlabels)
        ys = [v for _l, vs, _c, _d in lines for v in vs if v is not None]
        top = ymax if ymax else max(ys) * 1.12
        bot = 0

        def px(i):
            return x0 + (w * i / max(n - 1, 1))

        def py(v):
            return y0 + h - (v - bot) / (top - bot) * h

        # 网格与刻度
        for i, yl in enumerate(ylabels):
            yy = y0 + h * i / max(len(ylabels) - 1, 1)
            self.line(x0, yy, x0 + w, yy, LINE, 1, dash='3 3' if i else None)
            self.text(x0 - 8, yy + 4, yl, 10, FAINT, anchor='end')
        for i, xl in enumerate(xlabels):
            self.text(px(i), y0 + h + 16, xl, 10, FAINT, anchor='middle')
        if xname:
            self.text(x0 + w, y0 + h + 30, xname, 10, FAINT, anchor='end')
        if yname:
            # y 轴名默认右对齐到轴左侧；太长会伸到画布外，此时改为画布左边缘左对齐
            if x0 - 8 - tw(yname, 10) < 2:
                self.text(2, y0 - 10, yname, 10, FAINT)
            else:
                self.text(x0 - 8, y0 - 8, yname, 10, FAINT, anchor='end')

        for lab, vs, ck, dash in lines:
            main, _f2, _b = S[ck]
            pts = [(px(i), py(v)) for i, v in enumerate(vs) if v is not None]
            self.curve(pts, main, 2.0, dash=dash)
            for x, y in pts:
                self.dot(x, y, 2.6, main)
        # 图例
        lx = x0
        for lab, _vs, ck, dash in lines:
            main, _f2, _b = S[ck]
            self.line(lx, y0 - 14, lx + 16, y0 - 14, main, 2, dash=dash)
            self.text(lx + 21, y0 - 10.5, lab, 10.5, MUTED)
            lx += 21 + tw(lab, 10.5) + 18
        return self

    def flow(self, y, steps, x0=14, w=None, bh=42, gap=16, note_size=10):
        """横向流程链。steps: [(标题, 副标题, 色键)]"""
        w = (w or self.w - x0 * 2)
        n = len(steps)
        bw = (w - gap * (n - 1)) / n
        for i, (t, sub, ck) in enumerate(steps):
            main, fill, bd = S[ck]
            bx = x0 + i * (bw + gap)
            self.rect(bx, y, bw, bh, fill, bd, 1, 7)
            self.text(bx + bw / 2, y + 18, t, 11.5, main, 'middle', 600)
            if sub:
                self.text(bx + bw / 2, y + 33, sub, 10, MUTED, 'middle')
            if i < n - 1:
                self.arrow(bx + bw + 3, y + bh / 2, bx + bw + gap - 3, y + bh / 2, LINE_S, 1.4)
        return self

    def stack(self, x0, y0, w, h, groups, segs, cap=None, base_note=''):
        """堆叠柱。groups: [柱名]；segs: [(段名, [各柱比例0..1], 色键)]

        标题与图例分两行放（标题 y0-34、图例 y0-16），别都挤在 y0-10 附近——
        实测两者会叠在一起。
        """
        if cap:
            self.text(x0, y0 - 34, cap, 10.5, FAINT)
        n = len(groups)
        bw = w / n * 0.46
        for gi, g in enumerate(groups):
            bx = x0 + w * (gi + 0.5) / n - bw / 2
            acc = 0.0
            for name, vals, ck in segs:
                v = vals[gi] * h
                main, fill, bd = S[ck]
                self.rect(bx, y0 + h - acc - v, bw, v, fill, bd, 1, 3)
                if v > 13:
                    self.text(bx + bw / 2, y0 + h - acc - v / 2 + 4, f'{vals[gi]*100:.0f}%',
                              10, main, 'middle', 600)
                acc += v
            self.text(bx + bw / 2, y0 + h + 16, g, 10.5, MUTED, 'middle')
        # 图例（与标题分两行）
        lx = x0
        for name, _v, ck in segs:
            main, fill, bd = S[ck]
            self.rect(lx, y0 - 24, 11, 9, fill, bd, 1, 2)
            self.text(lx + 15, y0 - 16, name, 10.5, MUTED)
            lx += 15 + tw(name, 10.5) + 16
        if base_note:
            self.text(x0 + w, y0 + h + 16, base_note, 10, FAINT, anchor='end')
        return self

    def logscale(self, y, marks, x0=30, w=None, lo=0, hi=9, note=''):
        """对数刻度尺。marks: [(标签, 指数, 色键)]，指数即 10 的幂。

        标签锚点必须按位置自适应：靠右端的标记若仍用 middle，文字会越过画布右边界
        （实测 10^11 处的「100 吉瓦（Starshot）」被裁掉一截）。
        note 固定放在左上角，不要放右上——右上正是高指数标记的标签区。
        """
        w = (w or self.w - x0 * 2)
        self.line(x0, y, x0 + w, y, LINE_S, 1.6)
        for i in range(lo, hi + 1):
            xx = x0 + w * (i - lo) / (hi - lo)
            self.line(xx, y - 5, xx, y + 5, LINE_S, 1)
            self.text(xx, y + 19, f'10{_sup(i)}', 9.5, FAINT, 'middle')
        if note:
            self.text(x0, y - 46, note, 10, FAINT)
        rows = {}
        for lab, e, ck in marks:
            main, fill, bd = S[ck]
            xx = x0 + w * (e - lo) / (hi - lo)
            self.dot(xx, y, 4.4, main)
            lvl = rows.get(round(e * 2) / 2, 0)
            rows[round(e * 2) / 2] = lvl + 1
            wt = tw(lab, 10.5)
            anchor = 'middle'
            if xx + wt / 2 > self.w - 2:
                anchor = 'end'
            elif xx - wt / 2 < 2:
                anchor = 'start'
            self.text(xx, y - 15 - lvl * 15, lab, 10.5, main, anchor, 600)
        return self

    def timeline(self, x0, y0, w, rows, xlabels, cap=None):
        """时间条。rows: [(标签, 起, 止, 色键, 条内文字)]，起止为 xlabels 的下标（可小数）。"""
        if cap:
            self.text(x0, y0 - 10, cap, 10.5, FAINT)
        n = len(xlabels)
        span = max(n - 1, 1)
        for i, xl in enumerate(xlabels):
            xx = x0 + w * i / span
            self.line(xx, y0, xx, y0 + len(rows) * 30 + 6, LINE, 1, dash='3 3')
            self.text(xx, y0 + len(rows) * 30 + 22, xl, 10, FAINT, 'middle')
        for ri, (lab, a, b, ck, inner) in enumerate(rows):
            main, fill, bd = S[ck]
            yy = y0 + 6 + ri * 30
            self.text(x0 - 12, yy + 12, lab, 11, INK, 'end')
            bx = x0 + w * a / span
            bw = max(w * (b - a) / span, 6)
            self.rect(bx, yy, bw, 18, fill, bd, 1, 4)
            if inner:
                self.text(bx + bw / 2, yy + 13, inner, 10, main, 'middle', 600)
        return self

    def scatter(self, x0, y0, w, h, pts, xlab, ylab, quad=None, xr=(0, 1), yr=(0, 1)):
        """散点/象限图。pts: [(x, y, 标签, 色键)]，x/y 为归一化 0..1。"""
        self.line(x0, y0 + h, x0 + w, y0 + h, LINE_S, 1.2)
        self.line(x0, y0, x0, y0 + h, LINE_S, 1.2)
        self.text(x0 + w, y0 + h + 18, xlab, 10.5, FAINT, 'end')
        self.text(x0 - 6, y0 - 8, ylab, 10.5, FAINT, 'end')
        if quad:
            self.line(x0 + w / 2, y0, x0 + w / 2, y0 + h, LINE, 1, dash='4 3')
            self.line(x0, y0 + h / 2, x0 + w, y0 + h / 2, LINE, 1, dash='4 3')
            self.text(x0 + w / 2 + 6, y0 + 12, quad, 10, FAINT)
        for x, y, lab, ck in pts:
            main, fill, bd = S[ck]
            px, py = x0 + w * x, y0 + h * (1 - y)
            self.dot(px, py, 4.4, main)
            self.text(px, py - 10, lab, 10.5, main, 'middle', 600)
        return self

    def layers(self, x0, y0, w, items, row=34, thick=24):
        """分层剖面/层级条。items: [(层名, 厚度文字, 色键, 说明)]"""
        y = y0
        for lab, th, ck, note in items:
            main, fill, bd = S[ck]
            self.rect(x0, y, w, thick, fill, bd, 1, 4)
            self.text(x0 + 12, y + 16, lab, 11.5, main, weight=600)
            self.text(x0 + w - 12, y + 16, th, 11, main, 'end', 600)
            if note:
                self.text(x0, y + thick + 13, note, 10.5, FAINT)
                y += 14
            y += row
        return self

    def annot(self, x, y, text, color=MUTED, size=10.5, anchor='start'):
        return self.text(x, y, text, size, color, anchor)

    def leader(self, x1, y1, x2, y2, text='', color=MUTED, size=10.5, anchor='start'):
        """引线标注：从图形上一点拉到文字锚点。"""
        self.line(x1, y1, x2, y2, color, 0.8)
        if text:
            off = 5 if anchor == 'start' else -5
            self.text(x2 + off, y2 + 3.5, text, size, color, anchor)
        return self

    # ------------------------------------------------------------ 输出
    def svg(self, aria=''):
        defs = ('<defs><marker id="da" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="5.5" '
                'markerHeight="5.5" orient="auto-start-reverse">'
                f'<path d="M1 1 L7 4 L1 7" fill="none" stroke="{MUTED}" stroke-width="1.2" '
                'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>')
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{aria}">'
                + defs + ''.join(self._ops) + '</svg>')


def _sup(n):
    """把指数写成上标形式（SVG 里没有 <sup>，用 Unicode 上标字符）。"""
    m = {'0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3', '4': '\u2074',
         '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
         '-': '\u207b'}
    return ''.join(m.get(c, c) for c in str(n))
