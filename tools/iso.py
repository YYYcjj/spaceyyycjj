# -*- coding: utf-8 -*-
"""等轴测（isometric）SVG 生成器。

把 3D 的长方体 / 圆柱 / 圆台 / 标注投影成矢量图，供 build.py 内联进页面。
九张 3D 图共用同一套几何与配色，且是矢量、可打印、无外部依赖。

坐标约定：
    x 轴向右下方（与水平成 30°），y 轴向左下方（30°），z 轴竖直向上。
    屏幕坐标：  sx = ox + (x - y) * cos30 * s
                sy = oy + ((x + y) * sin30 - z) * s
    可见的三个面：顶面（z 最大）、右侧面（x 最大）、左侧面（y 最大）。

三段式工作：
    1. add_* 只记录几何/绘制指令，并采集用到的 3D 点与文字；
    2. auto_fit() 解一组线性不等式，同时保证「几何体放得下」且「文字不被裁掉」；
    3. svg() 在最终缩放与原点下统一渲染。

**标注必须往屏幕水平方向延伸**：用 R(d, z) / L(d, z) 取锚点。
因为文字宽度会参与 auto_fit，往竖直方向拉长会把整图压小。

图注（caption）不要画进 SVG——放到 <figcaption> 里让浏览器自动换行。
"""

import math

CO = math.cos(math.radians(30))      # 0.8660
SI = math.sin(math.radians(30))      # 0.5
_SQ2 = math.sqrt(2)

# 调色板：(顶面, 左侧面, 右侧面)。左侧面比右侧面亮，对应左上方打光。
C = {
    'white':  ('#ffffff', '#f4f4f1', '#e3e3de'),
    'steel':  ('#f2f3f5', '#d9dce1', '#c3c7ce'),
    'gray':   ('#f1efe8', '#e2dfd6', '#cbc8bf'),
    'ink':    ('#43464d', '#2b2d33', '#1e2024'),
    'dark':   ('#5a5e66', '#43464d', '#34373d'),
    'blue':   ('#e6f1fb', '#c6dcf4', '#a3c8ea'),
    'blue2':  ('#cfe2f7', '#a9caf0', '#83b2e1'),
    'green':  ('#eaf3de', '#cfe5b4', '#b2d68c'),
    'amber':  ('#faeeda', '#f3d7a9', '#e9be7b'),
    'red':    ('#fcebeb', '#f5cccc', '#eaa9a9'),
    'gold':   ('#fdf6e3', '#f1e2b5', '#ddc077'),
}

INK = '#1c1c1a'
MUTED = '#6f6f69'
FAINT = '#9a9992'


def _f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def _tw(text, size):
    """粗略估算文字像素宽度：CJK 按 1em、ASCII 按 0.55em。"""
    u = 0.0
    for ch in text:
        u += 1.0 if ord(ch) > 0x2E7F else 0.55
    return u * size


class Iso:
    def __init__(self, w=680, h=380, pad=16, padx=28):
        self.w, self.h, self.pad, self.padx = w, h, pad, padx
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0
        self._bounds = (0.0, 1.0, 0.0, 1.0)
        self._du = self._dv = 1.0
        self._ops = []      # (排序键, z序, 渲染闭包)
        self._seq = 0
        self._raw = []      # 几何 3D 点，决定基本 bbox
        self._txt = []      # 文字约束：(u, v, dxl, dxr, dyt, dyb)

    # ---------------------------------------------------------------- 内部
    def _u(self, x, y, z):
        return ((x - y) * CO, (x + y) * SI - z)

    def _p(self, x, y, z):
        u, v = self._u(x, y, z)
        return (self.ox + u * self.s, self.oy + v * self.s)

    def _add(self, key, fn, raw=()):
        self._seq += 1
        self._raw.extend(raw)
        self._ops.append((key, self._seq, fn))

    def _rec_text(self, u, v, text, size, anchor, dx=0, dy=0):
        if not text:
            return
        wt = _tw(text, size)
        if anchor == 'end':
            dxl, dxr = dx - wt, dx
        elif anchor == 'middle':
            dxl, dxr = dx - wt / 2, dx + wt / 2
        else:
            dxl, dxr = dx, dx + wt
        self._txt.append((u, v, dxl, dxr, dy - size * 0.78, dy + size * 0.26))

    def _poly_svg(self, pts, fill, stroke, sw, op):
        p = ' '.join(f'{_f(a)},{_f(b)}' for a, b in (self._p(*q) for q in pts))
        st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ''
        o = f' opacity="{op}"' if op is not None else ''
        return f'<polygon points="{p}" fill="{fill}"{st}{o}/>'

    def _ellipse_svg(self, cx, cy, z, r, fill, stroke, sw):
        x, y = self._p(cx, cy, z)
        rx, ry = r * CO * _SQ2 * self.s, r * SI * _SQ2 * self.s
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
        return f'<ellipse cx="{_f(x)}" cy="{_f(y)}" rx="{_f(rx)}" ry="{_f(ry)}" fill="{fill}"{st}/>'

    # ---------------------------------------------------------------- 几何体
    def box(self, x, y, z, dx, dy, dz, c='steel', stroke=INK, sw=0.7, op=None, zkey=None):
        top, left, right = C[c] if isinstance(c, str) else c
        x1, y1, z1 = x + dx, y + dy, z + dz
        raw = [(x, y, z), (x1, y, z), (x, y1, z), (x, y1, z1),
               (x, y, z1), (x1, y, z1), (x1, y1, z), (x1, y1, z1)]
        for pts, col in (
            ([(x, y, z1), (x1, y, z1), (x1, y1, z1), (x, y1, z1)], top),
            ([(x, y1, z1), (x1, y1, z1), (x1, y1, z), (x, y1, z)], left),
            ([(x1, y, z1), (x1, y1, z1), (x1, y1, z), (x1, y, z)], right),
        ):
            self._add(zkey if zkey is not None else (x + y + z),
                      (lambda p=pts, f=col: self._poly_svg(p, f, stroke, sw, op)), raw)

    def cyl(self, cx, cy, z, r, dz, c='steel', stroke=INK, sw=0.7):
        top, _l, right = C[c] if isinstance(c, str) else c
        raw = [(cx - r, cy - r, z), (cx + r, cy + r, z + dz)]
        key = cx + cy + z

        def side():
            xa, ya = self._p(cx, cy, z + dz)
            xb, yb = self._p(cx, cy, z)
            rx, ry = r * CO * _SQ2 * self.s, r * SI * _SQ2 * self.s
            return (f'<path d="M {_f(xa - rx)} {_f(ya)} L {_f(xa - rx)} {_f(yb)} '
                    f'A {_f(rx)} {_f(ry)} 0 0 0 {_f(xa + rx)} {_f(yb)} '
                    f'L {_f(xa + rx)} {_f(ya)} A {_f(rx)} {_f(ry)} 0 0 1 {_f(xa - rx)} {_f(ya)} Z" '
                    f'fill="{right}" stroke="{stroke}" stroke-width="{sw}"/>')

        self._add(key, lambda: self._ellipse_svg(cx, cy, z, r, right, stroke, sw), raw)
        self._add(key, side, raw)
        self._add(key, lambda: self._ellipse_svg(cx, cy, z + dz, r, top, stroke, sw), raw)

    def cone(self, cx, cy, z0, z1, r0, r1, c='blue', op=0.45, stroke=None, sw=0.8, sw_key=None):
        _t, _l, right = C[c] if isinstance(c, str) else c
        raw = [(cx - r0, cy - r0, z0), (cx + r0, cy + r0, z0),
               (cx - r1, cy - r1, z1), (cx + r1, cy + r1, z1)]

        def draw():
            xa, ya = self._p(cx, cy, z0)
            xb, yb = self._p(cx, cy, z1)
            rax, ray = r0 * CO * _SQ2 * self.s, r0 * SI * _SQ2 * self.s
            rbx, rby = r1 * CO * _SQ2 * self.s, r1 * SI * _SQ2 * self.s
            st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
            return (f'<path d="M {_f(xa - rax)} {_f(ya)} L {_f(xb - rbx)} {_f(yb)} '
                    f'A {_f(rbx)} {_f(rby)} 0 0 1 {_f(xb + rbx)} {_f(yb)} '
                    f'L {_f(xa + rax)} {_f(ya)} A {_f(rax)} {_f(ray)} 0 0 0 {_f(xa - rax)} {_f(ya)} Z" '
                    f'fill="{right}"{st} opacity="{op}"/>')

        self._add(cx + cy + z0 if sw_key is None else sw_key, draw, raw)

    def surface(self, pts, fill, op=0.6, stroke=None, sw=0.8, key=None):
        self._add(9999 if key is None else key,
                  (lambda: self._poly_svg(pts, fill, stroke, sw, op)), pts)

    def line3(self, a, b, color=INK, sw=0.9, dash=None, op=None, key=None):
        def draw():
            x1, y1 = self._p(*a)
            x2, y2 = self._p(*b)
            d = f' stroke-dasharray="{dash}"' if dash else ''
            o = f' opacity="{op}"' if op is not None else ''
            return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
                    f'stroke="{color}" stroke-width="{sw}"{d}{o}/>')
        self._add(9999 if key is None else key, draw, (a, b))

    # ---------------------------------------------------------------- 标注
    def dim(self, a, b, label='', color=MUTED, side=1, sw=0.8, gap=15):
        def draw():
            x1, y1 = self._p(*a)
            x2, y2 = self._p(*b)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L * gap * side, dx / L * gap * side
            out = [f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
                   f'stroke="{color}" stroke-width="{sw}" marker-start="url(#ar)" marker-end="url(#ar)"/>']
            if label:
                out.append(f'<text x="{_f(mx + nx)}" y="{_f(my + ny)}" fill="{color}" '
                           f'font-size="10.5" text-anchor="middle" dominant-baseline="middle">{label}</text>')
            return ''.join(out)
        self._add(9999, draw, (a, b))
        if label:
            ua, va = self._u(*a)
            ub, vb = self._u(*b)
            wt = _tw(label, 10.5)
            self._txt.append(((ua + ub) / 2, (va + vb) / 2,
                              -gap - wt / 2, gap + wt / 2, -gap - 12, gap + 12))

    def label(self, x, y, z, text, anchor='start', color=INK, size=11, weight=400, dx=0, dy=0, op=None):
        u, v = self._u(x, y, z)

        def draw():
            px, py = self._p(x, y, z)
            o = f' opacity="{op}"' if op is not None else ''
            return (f'<text x="{_f(px + dx)}" y="{_f(py + dy)}" fill="{color}" font-size="{size}" '
                    f'font-weight="{weight}" text-anchor="{anchor}"{o}>{text}</text>')
        self._add(9999, draw)
        self._rec_text(u, v, text, size, anchor, dx, dy)

    def leader(self, a, b, text, anchor='start', color=MUTED, size=10.5, elbow=0.45):
        """引线标注。a 指对象上一点，b 是文字锚点，**都用 3D 坐标**（会参与自适应）。"""
        u, v = self._u(*b)
        off = 5 if anchor == 'start' else -5

        def draw():
            ax, ay = self._p(*a)
            bx, by = self._p(*b)
            cxp = ax + (bx - ax) * elbow
            out = [f'<polyline points="{_f(ax)},{_f(ay)} {_f(cxp)},{_f(by)} {_f(bx)},{_f(by)}" '
                   f'fill="none" stroke="{color}" stroke-width="0.7" stroke-linejoin="round"/>']
            if text:
                out.append(f'<text x="{_f(bx + off)}" y="{_f(by - 4)}" fill="{color}" '
                           f'font-size="{size}" text-anchor="{anchor}">{text}</text>')
            return ''.join(out)
        self._add(9999, draw, (a, b))
        self._rec_text(u, v, text, size, anchor, off, -4)

    # ---------------------------------------------------------------- 自适应
    def _fit_bounds(self):
        us = [self._u(*p) for p in self._raw]
        return (min(a for a, _ in us), max(a for a, _ in us),
                min(b for _, b in us), max(b for _, b in us))

    def _place(self, s):
        U0, U1, V0, V1 = self._bounds
        du, dv = self._du, self._dv
        self.s = s
        self.ox = (self.w - du * s) / 2 - U0 * s
        self.oy = (self.h - dv * s) / 2 - V0 * s

    def _all_inside(self):
        """当前缩放/原点下，几何外框与所有文字是否都在画布内。"""
        U0, U1, V0, V1 = self._bounds
        if self.ox + U0 * self.s < 1 or self.ox + U1 * self.s > self.w - 1:
            return False
        if self.oy + V0 * self.s < 1 or self.oy + V1 * self.s > self.h - 1:
            return False
        for (u, v, dxl, dxr, dyt, dyb) in self._txt:
            x = self.ox + u * self.s
            y = self.oy + v * self.s
            if x + dxl < 1 or x + dxr > self.w - 1:
                return False
            if y + dyt < 1 or y + dyb > self.h - 1:
                return False
        return True

    def auto_fit(self):
        """从几何上限出发逐步收缩，直到几何体与所有文字都落进画布。

        之所以用迭代而不是解析解：文字约束是关于 s 的分式不等式，当锚点偏到
        图形极右/极左时不等式方向会翻转，手写分支很容易漏（实测漏掉后右边缘文字会出框）。
        迭代法只有一个条件「全都进框」，必然收敛（s→0 时一切聚到画布中心）。
        """
        if not self._raw:
            return
        self._bounds = self._fit_bounds()
        U0, U1, V0, V1 = self._bounds
        self._du, self._dv = max(U1 - U0, 1e-6), max(V1 - V0, 1e-6)
        s = min((self.w - 2 * self.padx) / self._du,
                (self.h - 2 * self.pad) / self._dv)
        self._place(max(s, 1e-6))
        for _ in range(80):
            if self._all_inside():
                break
            s *= 0.96
            self._place(s)
        self.s = max(self.s, 1e-4)

    def svg(self, aria=''):
        self.auto_fit()
        objs = [fn() for _k, _s, fn in sorted(self._ops, key=lambda o: (o[0], o[1]))]
        defs = ('<defs><marker id="ar" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="5" '
                'markerHeight="5" orient="auto-start-reverse">'
                f'<path d="M1 1 L7 4 L1 7" fill="none" stroke="{MUTED}" stroke-width="1.1" '
                'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>')
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{aria}">'
                + defs + ''.join(objs) + '</svg>')
