# -*- coding: utf-8 -*-
"""可拖拽旋转的 CSS 3D 模型生成器（零依赖、可打印）。

和另外两个图元库的分工：

    iso.py     静态等轴测投影 —— 角度写死，适合工程示意
    dia.py     二维关系图 —— 过程 / 数值 / 层级
    models3d   真三维（CSS transform + preserve-3d）—— 读者自己转，找自己的角度

为什么是 CSS 3D 而不是 WebGL：全站立着「纯静态、零依赖、可打印」这条线。
Three.js 是 600 KB 的外部库，离线会退化、打印会变黑框，而且和手绘矢量图不是一套质感。
CSS 3D 用浏览器自带的变换管线，产出就是 div，顺带白拿打印、缩放、可访问性与
prefers-reduced-motion 的支持。

---------------------------------------------------------------- 坐标与投影

建模坐标沿用 iso.py 的习惯：**x 向右、y 向上、z 朝向观察者**，单位是「设计单位」。
CSS 里 y 向下，所以落到样式时统一取负：`translate3d(x, -y, z)`。

世界变换是 CSS 的 `rotateX(rx) rotateY(ry)`，即矩阵 `Rx·Ry`。屏幕投影带透视：

    v  = Rx(rx) · Ry(ry) · (X, Y, Z)        # (X, Y, Z) = (x, -y, z)
    sx = X · P / (P − Z)      sy = Y · P / (P − Z)

---------------------------------------------------------------- 三个设计决定

1. **只画轴对齐的长方体与竖直圆柱，不做旋转部件。**
   一旦允许部件自身带旋转，包围盒、自适配、标注投影全都要跟着做矩阵运算，
   收益（几根斜撑）远小于风险（算错的图不会报错，只会静默地画歪）。
   着陆腿做成四片竖板、太阳帆做成水平薄板——工程示意里这样反而更清楚。

2. **编号点（pin）是 2D 覆盖层，不是 3D 里的元素。**
   放进 3D 世界的话，转到背面会被不透明的面片挡住，而且包围盒要外扩一圈。
   做成 2D 覆盖层则永远在最上层可读，位置由**同一套投影公式**算出来：
   构建期按默认角度写死在 `left/top`（所以没有 JS 时也正确、打印也正确），
   运行期由 site.js 按当前角度逐帧更新。

3. **自适配不是「按包围盒缩」，而是按旋转范围采样求解。**
   模型要转，转到任何角度都得待在台面里。所以对 rx∈[−52,8]、ry∈[0,360) 采样，
   把每个部件的极值点投到屏幕，取最大横向/纵向半宽，再反解除缩放系数。
   顺带在同一批采样里断言「两个编号点不会重叠」——和 check_figs.py 一个思路：
   这类问题截图上很难发现（要在特定角度才重叠），只能算。

运行自检：

    python3 tools/models3d.py            # 打印每个模型的自适配结果与断言
"""

import math
import re

# ---------------------------------------------------------------- 颜色

# 与 iso.py 同一套色名的「中间调」。iso.py 给的是 (顶面, 左侧面, 右侧面) 三元组，
# 这里只存一个基色，六面明暗在下面按固定光照表算——不然同一个颜色要维护六个值。
PAL = {
    'white': '#eef0eb',
    'steel': '#c5ccd7',
    'gray':  '#cfccc0',
    'ink':   '#33363c',
    'dark':  '#4b4f57',
    'blue':  '#a8cbee',
    'blue2': '#84b4e0',
    'green': '#b6d890',
    'amber': '#ebc88e',
    'red':   '#e8a5a5',
    'gold':  '#e4ce8c',
}

# 六面明暗（与 iso.py 同一个打光方向：光从左上前方来）。
# 顶面最亮、底面最暗、左侧比右侧亮。
# 明暗差要拉开：台面是浅色的，明暗差小的话浅色件会糊在背景里（截图看过，
# 第一版顶面 +0.24 / 右侧 −0.15 的两档几乎分不出来）。
LIGHT = {'fr': 0.06, 'bk': -0.30, 'rt': -0.24, 'lf': 0.15, 'tp': 0.31, 'bt': -0.44}
EDGE = -0.55          # 描边 = 基色再压暗，保证浅色件在浅色底上也有轮廓

# 圆柱侧面的光照方向（由外法线算 lambert）
LX, LY, LZ = -0.42, 0.70, 0.58

# 画布与自适配目标（px）。台面比目标大一圈——留出转动的余量。
#
# ⚠️ 台面**不能太宽**。第一版是 560×420 + 目标 340×330，模型只占到台面宽度的
# 三成，1px 的描边在小尺寸下糊成一片噪点（机器人那台尤其明显，看着像半透明）。
# 现在台面收到 460×400、目标放大到 400×350，模型能占到台面的 55%～80%。
STAGE_W, STAGE_H = 460, 400
FIT_W, FIT_H = 400, 350
PERSP = 1500          # 与 site.css 的 .m3d-stage{perspective} 保持一致

# 交互允许的俯仰范围，自适配必须按这个范围采样（site.js 里也夹同样的值）
RX_MIN, RX_MAX = -52.0, 8.0
RX_DEF, RY_DEF = -18.0, -32.0

PIN_D = 20            # 编号点直径（px），构建期按它断言「不重叠」

# 「点一下放大」时，被聚焦的部件要占到台面的多大。0.62 是留白后的手感值：
# 再大就会顶到台面边缘（旋转时一旦有透视放大就出框），再小又看不出「放大」。
FOCUS_W, FOCUS_H = STAGE_W * 0.62, STAGE_H * 0.62
FOCUS_MAX = 6.0       # 放大倍数上限：极小的部件（栅格舵之类）不要放到离谱


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hx(t):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in t)


def shade(c, t):
    """t > 0 往白走，t < 0 往黑走。"""
    r, g, b = _rgb(c)
    if t >= 0:
        return _hx((r + (255 - r) * t, g + (255 - g) * t, b + (255 - b) * t))
    t = -t
    return _hx((r * (1 - t), g * (1 - t), b * (1 - t)))


def _alpha(c, a):
    r, g, b = _rgb(c)
    return f'rgba({r},{g},{b},{a:g})'


def _f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


# ---------------------------------------------------------------- 旋转

def _rot(v, rx, ry):
    """CSS `rotateX(rx) rotateY(ry)` 作用到向量 v（度）。"""
    a, b = math.radians(ry), math.radians(rx)
    x, y, z = v
    # Ry
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    # Rx
    y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
    return (x, y, z)


def _proj(v, rx, ry):
    """投到屏幕：返回相对台面中心的 (sx, sy)。"""
    x, y, z = _rot(v, rx, ry)
    k = PERSP / max(PERSP - z, 1.0)
    return (x * k, y * k)


def _rot1(axis, deg, v):
    """单个 CSS 轴旋转（与 _rot 同样的约定），作用于向量 v。"""
    a = math.radians(deg)
    x, y, z = v
    if axis == 'X':
        return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))
    if axis == 'Y':
        return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))
    return (x, y, z)


def _rot_css(axis, deg):
    return '' if axis is None else f'rotate{axis}({_f(deg)}deg) '


def _tf(face, k):
    """把「(轴, 角度) + 距离」拼成 CSS 变换字符串。

    ⚠️ **距离必须在这里乘 k**。第一版把整串变换在 box() 里就拼好了，于是面片的长宽
    按 k 缩放了、translateZ 的位移没有——k≈1 时看不出来（星舰 k=1.14 完全正常），
    k=3.44 的机器人直接崩成一个十字展开图。别再把变换字符串提前拼死。
    """
    return f'{_rot_css(face["ax"], face["deg"])}translateZ({_f(face["z"] * k)}px)'


def _face(axis, deg, z, w, h, col, sc, nm=''):
    return dict(nm=nm, ax=axis, deg=deg, z=z, w=w, h=h, col=col, sc=sc)


# ---------------------------------------------------------------- 模型

class M3D:
    """一个可旋转模型。

    用法和 iso.Iso 一致：先 add_* 记录几何，最后 html() 一次性渲染。
    区别是这里没有 auto_fit()——自适配在 html() 内部做，因为标注投影也要用到缩放。
    """

    def __init__(self, title='', aria=''):
        self.title = title
        self.aria = aria
        self._parts = []      # dict(anchor, faces, pts, op)
        self._pins = []       # dict(n, at, label)

    # ------------------------------------------------------------ 几何体
    def box(self, x, y, z, w, h, d, c='steel', op=None):
        """轴对齐长方体，参数是**左下后角**与三边长度（y 向上）。"""
        c = PAL.get(c, c)          # 色名 → 十六进制。渲染时只认十六进制，别把色名传下去
        cx, cy, cz = x + w / 2.0, y + h / 2.0, z + d / 2.0
        hw, hh, hd = w / 2.0, h / 2.0, d / 2.0
        faces = [
            _face(None, 0, hd, w, h, c, LIGHT['fr'], 'fr'),
            _face('Y', 180, hd, w, h, c, LIGHT['bk'], 'bk'),
            _face('Y', 90, hw, d, h, c, LIGHT['rt'], 'rt'),
            _face('Y', -90, hw, d, h, c, LIGHT['lf'], 'lf'),
            _face('X', 90, hh, w, d, c, LIGHT['tp'], 'tp'),
            _face('X', -90, hh, w, d, c, LIGHT['bt'], 'bt'),
        ]
        pts = [(cx + sx * hw, cy + sy * hh, cz + sz * hd)
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        self._parts.append(dict(anchor=(cx, cy, cz), faces=faces, pts=pts, op=op))
        return self

    def cyl(self, x, y0, z, r, h, c='steel', n=16, op=None):
        """竖直圆柱。y0 是底面高度，h 是高度，轴线在 (x, z)。"""
        c = PAL.get(c, c)          # 同上：色名在这一层就解掉
        cy = y0 + h / 2.0
        chord = 2 * r * math.sin(math.pi / n) * 1.08   # 弦长 ×1.08，相邻面带一点重叠，免得漏缝
        faces = []
        for i in range(n):
            th = 360.0 * i / n
            t = math.radians(th)
            nx, nz = math.sin(t), math.cos(t)
            lam = max(0.0, nx * LX + nz * LZ + LY * 0.0)
            sc = min(max(-0.34 + 0.64 * lam, -0.34), 0.30)
            faces.append(_face('Y', th, r, chord, h, c, sc, f's{i}'))
        faces.append(_face('X', 90, h / 2, 2 * r, 2 * r, c, LIGHT['tp'], 'cap'))
        faces.append(_face('X', -90, h / 2, 2 * r, 2 * r, c, LIGHT['bt'], 'cb'))
        pts = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            pts.append((x + r * math.sin(t), y0, z + r * math.cos(t)))
            pts.append((x + r * math.sin(t), y0 + h, z + r * math.cos(t)))
        self._parts.append(dict(anchor=(x, cy, z), faces=faces, pts=pts, op=op,
                                cap=True))
        return self

    def plate(self, x, y, z, w, d, c='blue2', t=1.6, op=None):
        """水平薄板（太阳帆板、热辐射板、光帆）。"""
        return self.box(x - w / 2, y, z - d / 2, w, t, d, c, op)

    # ------------------------------------------------------------ 编号点
    def pin(self, n, x, y, z, part=None):
        """编号点（可点击，点了就放大它指向的那个部件）。

        位置要落在部件**外面**——它是 2D 覆盖层，压在模型中间会看不清指向谁。

        `part` 是「这个点指向第几个部件」，不填就按「到部件包围盒的距离」自动判定。
        自动判定在大多数情况下对，但当 pin 摆在一个大部件和小部件之间时会认错
        （实测 55 个点里错了 10 个），所以这几处显式指定。
        ⚠️ 显式指定的是**部件在建模代码里的调用序号**——调整几何顺序时这里要跟着改，
        构建期会校验序号不越界，但顺序对不对只能靠人看。
        """
        self._pins.append(dict(n=n, at=(x, y, z), part=part))
        return self

    # ------------------------------------------------------------ 聚焦
    def _nearest_part(self, at):
        """编号点归属哪个部件：取「到部件包围盒」距离最小的那个。

        用 AABB 距离而不是中心距离——编号点都放在部件**外侧**，
        到盒面的距离才反映它贴着谁（用中心距离时，小部件经常被旁边的大部件抢走）。
        """
        best, bi = 1e18, 0
        for i, part in enumerate(self._parts):
            xs = [p[0] for p in part['pts']]
            ys = [p[1] for p in part['pts']]
            zs = [p[2] for p in part['pts']]
            d = 0.0
            for v, lo, hi in ((at[0], min(xs), max(xs)), (at[1], min(ys), max(ys)),
                              (at[2], min(zs), max(zs))):
                d += (lo - v) ** 2 if v < lo else (v - hi) ** 2 if v > hi else 0.0
            if d < best:
                best, bi = d, i
        return bi

    def _focus(self, i, k):
        """带缓存地取聚焦参数——渲染、自检、反解校验都会反复要同一批值。"""
        if getattr(self, '_fc_k', None) != k:
            self._fc, self._fc_k = {}, k
        if i not in self._fc:
            self._fc[i] = self._focus_of(i, k)
        return self._fc[i]

    def _pin_parts(self):
        """每个编号点归属的部件索引。"""
        return [p['part'] if p.get('part') is not None else self._nearest_part(p['at'])
                for p in self._pins]

    def _focus_of(self, i, k):
        """聚焦第 i 个部件时需要的「平移量」与「放大倍数」。

        放大倍数不是拍脑袋的常数：对**该部件自己**的极值点再跑一遍旋转采样，
        保证它转到任何角度都还装得进聚焦框。所以扁平的部件能放得更大，细长的部件小一些。
        """
        o, part = self.origin, self._parts[i]
        xs = [p[0] for p in part['pts']]
        ys = [p[1] for p in part['pts']]
        zs = [p[2] for p in part['pts']]
        cx, cy, cz = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                      (min(zs) + max(zs)) / 2)
        c = ((cx - o[0]) * k, -(cy - o[1]) * k, (cz - o[2]) * k)
        pts = [((p[0] - o[0]) * k - c[0], -(p[1] - o[1]) * k - c[1],
                (p[2] - o[2]) * k - c[2]) for p in part['pts']]
        mx = my = 1e-6
        for a in range(int((RX_MAX - RX_MIN) / 8) + 1):
            rx = RX_MIN + a * 8
            for b in range(0, 360, 8):
                for v in pts:
                    sx, sy = _proj(v, rx, b)
                    mx, my = max(mx, abs(sx)), max(my, abs(sy))
        f = min(FOCUS_W / 2 / mx, FOCUS_H / 2 / my)
        return c, min(max(f, 1.0), FOCUS_MAX)

    # ------------------------------------------------------------ 自适配
    def _fit(self):
        """解出缩放系数 k，使模型在允许的旋转范围内始终待在自适配目标框里。"""
        pts = [p for part in self._parts for p in part['pts']]
        pts += [p['at'] for p in self._pins]
        # 先平移到 bbox 中心，让模型绕自身中心转（否则转起来会甩出画面）
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        zs = [p[2] for p in pts]
        o = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        self.origin = o
        P = [(p[0] - o[0], p[1] - o[1], p[2] - o[2]) for p in pts]
        css = [(p[0], -p[1], p[2]) for p in P]

        mx = my = 1e-6
        for i in range(int((RX_MAX - RX_MIN) / 8) + 1):
            rx = RX_MIN + i * 8
            for j in range(0, 360, 8):
                for v in css:
                    sx, sy = _proj(v, rx, j)
                    mx = max(mx, abs(sx))
                    my = max(my, abs(sy))
        # 编号点自身有直径，边缘那 12px 也要留出来
        mx += PIN_D / 2 + 4
        my += PIN_D / 2 + 4
        return min(FIT_W / 2 / mx, FIT_H / 2 / my)

    # ------------------------------------------------------------ 断言
    _RE_PART = re.compile(r'translate3d\(([-\d.]+)px,([-\d.]+)px,([-\d.]+)px\)')
    # 聚焦参数：从生成的容器标签里反解（自检只认吐出来的文本，理由见 _emitted_bbox）
    _RE_HDR = re.compile(
        r'data-i="(\d+)" data-f="([-\d.]+)" data-c="([-\d.]+),([-\d.]+),([-\d.]+)"')
    _RE_FACE = re.compile(
        r'width:([-\d.]+)px;height:([-\d.]+)px;margin:([-\d.]+)px 0 0 ([-\d.]+)px;'
        r'(?:border-radius:50%;)?transform:(?:rotate([XY])\(([-\d.]+)deg\) )?'
        r'translateZ\(([-\d.]+)px\)')

    def _emitted_bbox(self, k):
        """**从生成的 HTML 字符串反解**出浏览器实际会画出的包围盒。

        这是端到端断言，不是把同一份数算两遍：它只认 _faces_html() 真正吐出来的
        `width/height/margin/transform` 文本。渲染路径上任何一步写错——长宽没缩放、
        translateZ 没缩放、面片没对中到部件原点——这里都会和几何包围盒对不上。

        之所以必须是「反解文本」而不是「复用内部变量」：第一版复用变量的写法，
        我把 translateZ 的缩放故意去掉、断言照样全绿（负向测试验过），等于白写。

        顺带查两件事：margin 必须正好是 -w/2 / -h/2（面片中心落在部件原点上），
        以及面片不能小到看不见。
        """
        o = self.origin
        lo, hi = [1e9] * 3, [-1e9] * 3
        bad_center = 0
        seen = 0                     # 反解到的面片数，必须与几何定义对得上
        self._seen_focus = []        # 顺带把聚焦参数采集出来给 problems() 校验
        for i, part in enumerate(self._parts):
            chunk = self._faces_html(part, k, i)
            h = self._RE_HDR.search(chunk)
            if h:
                self._seen_focus.append(h.groups())
            m = self._RE_PART.search(chunk)
            if not m:
                return None, None, ['部件容器没有 translate3d']
            base = tuple(float(m.group(i)) for i in (1, 2, 3))
            for fm in self._RE_FACE.finditer(chunk):
                seen += 1
                w, h, mt, ml = (float(fm.group(i)) for i in (1, 2, 3, 4))
                axis, deg, z = fm.group(5), fm.group(6), float(fm.group(7))
                deg = float(deg) if deg else 0.0
                if abs(ml + w / 2) > 0.02 or abs(mt + h / 2) > 0.02:
                    bad_center += 1
                    continue
                c = _rot1(axis, deg, (0.0, 0.0, z))
                ex = _rot1(axis, deg, (w / 2, 0.0, 0.0))
                ey = _rot1(axis, deg, (0.0, h / 2, 0.0))
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        v = tuple(base[i] + c[i] + sx * ex[i] + sy * ey[i] for i in range(3))
                        for i in range(3):
                            lo[i] = min(lo[i], v[i])
                            hi[i] = max(hi[i], v[i])
        want = sum(len(p['faces']) for p in self._parts)
        err = []
        if seen != want:
            err.append(f'{self.title}：几何定义了 {want} 张面片，'
                       f'但渲染出来的 HTML 里只反解到 {seen} 张'
                       f'（有面片的 style 写法变了，自检会漏掉它们）')
        if bad_center:
            err.append(f'{self.title}：{bad_center} 张面片没有对中到部件原点'
                       f'（margin 必须是 -w/2 / -h/2）')
        if err:
            return None, None, err
        return lo, hi, []

    def _scaled(self):
        k, o = self.k, self.origin
        pts = [((p[0] - o[0]) * k, -(p[1] - o[1]) * k, (p[2] - o[2]) * k)
               for part in self._parts for p in part['pts']]
        pins = [((p['at'][0] - o[0]) * k, -(p['at'][1] - o[1]) * k, (p['at'][2] - o[2]) * k)
                for p in self._pins]
        return pts, pins

    def problems(self):
        """构建期自检。

        查两类：**任何角度下几何体与编号点都必须待在台面里**；以及
        **默认角度下编号点不重叠**——默认角度这一条是硬要求，因为它同时是
        没有 JS 时的样子和打印出来的样子。

        至于「转到某个角度两个编号点撞上」：那是自由旋转与固定标注的固有矛盾
        （模型转到背面时，前后两个点必然交换位置并擦肩而过），靠挪坐标解决不了。
        所以交给运行期——site.js 每帧按序号优先级把撞上的点淡出，序号小的留下。
        这里只统计最坏情况，作为「这个模型标注密不密」的参考值。
        """
        out = []
        if not self._parts:
            return [f'{self.title}：没有任何部件']
        self.k = self._fit()
        pts, pins = self._scaled()
        worst = (999.0, '', '')

        # 端到端：渲染参数还原出来的包围盒，必须和自适配用的几何包围盒对得上。
        # 容差给了 5% + 1.5px——圆柱是用内接多边形近似的，本来就会略小于真圆。
        elo, ehi, eerr = self._emitted_bbox(self.k)
        out += eerr
        if elo is None:
            return out
        for i, axis in enumerate('xyz'):
            ilo = min(p[i] for p in pts)
            ihi = max(p[i] for p in pts)
            tol = (ihi - ilo) * 0.05 + 1.5
            if abs(elo[i] - ilo) > tol or abs(ehi[i] - ihi) > tol:
                out.append(
                    f'{self.title}：{axis} 轴的渲染包围盒 [{elo[i]:.1f}, {ehi[i]:.1f}] '
                    f'与几何包围盒 [{ilo:.1f}, {ihi:.1f}] 对不上 '
                    f'（差 {max(abs(elo[i] - ilo), abs(ehi[i] - ihi)):.1f}px，'
                    f'容差 {tol:.1f}px）——多半是某处忘了乘缩放系数 k')
        self.bbox_gap = max(
            max(abs(elo[i] - min(p[i] for p in pts)), abs(ehi[i] - max(p[i] for p in pts)))
            for i in range(3))

        # ---- 「点一下放大」的端到端校验 ----
        # 同样只认反解出来的 data-f / data-c：放大倍数算错、中心写错、或倍数被上限截断到
        # 部件装不下台面，都要在这里拦住——这些在默认视角的截图上完全看不出来。
        seen = getattr(self, '_seen_focus', [])
        if len(seen) != len(self._parts):
            out.append(f'{self.title}：{len(self._parts)} 个部件里只反解到 {len(seen)} 个'
                       f'带聚焦参数的容器（改了 .m3d-p 的写法会让放大功能静默失效）')
        else:
            for i, (si, sf, sx, sy, sz) in enumerate(seen):
                if int(si) != i:
                    out.append(f'{self.title}：第 {i} 个部件容器写着 data-i="{si}"')
                    continue
                f = float(sf)
                c = (float(sx), float(sy), float(sz))
                part = self._parts[i]
                xs = [q[0] for q in part['pts']]
                ys = [q[1] for q in part['pts']]
                zs = [q[2] for q in part['pts']]
                want = (((min(xs) + max(xs)) / 2 - self.origin[0]) * self.k,
                        -((min(ys) + max(ys)) / 2 - self.origin[1]) * self.k,
                        ((min(zs) + max(zs)) / 2 - self.origin[2]) * self.k)
                if max(abs(c[j] - want[j]) for j in range(3)) > 0.6:
                    out.append(f'{self.title}：部件 {i} 的 data-c {c} 与它真实的中心 {want} 不符')
                    continue
                if f < 1.0:
                    out.append(f'{self.title}：部件 {i} 的放大倍数 {f:.2f} 小于 1（点开会变小）')
                    continue
                over = 0.0
                for rx in range(int(RX_MIN), int(RX_MAX) + 1, 6):
                    for ry in range(0, 360, 6):
                        for q in part['pts']:
                            v = (((q[0] - self.origin[0]) * self.k - c[0]) * f,
                                 (-(q[1] - self.origin[1]) * self.k - c[1]) * f,
                                 ((q[2] - self.origin[2]) * self.k - c[2]) * f)
                            px, py = _proj(v, rx, ry)
                            over = max(over, abs(px) - (STAGE_W / 2 - 8),
                                       abs(py) - (STAGE_H / 2 - 8))
                if over > 0:
                    out.append(f'{self.title}：放大部件 {i} 后转出台面 {over:.1f}px'
                               f'（倍数 {f:.2f} 太大，或该部件本身就装不下）')
        self.focus_zoom = [float(x[1]) for x in seen] if seen else []
        self.pin_parts = self._pin_parts()

        for i in range(int((RX_MAX - RX_MIN) / 6) + 1):
            rx = RX_MIN + i * 6
            for j in range(0, 360, 6):
                for v in pts:
                    sx, sy = _proj(v, rx, j)
                    if abs(sx) > STAGE_W / 2 - 16 or abs(sy) > STAGE_H / 2 - 16:
                        out.append(f'{self.title}：rx={rx:.0f} ry={j} 时几何体出框'
                                   f'（{sx:.0f},{sy:.0f}）')
                        break
                ss = [_proj(v, rx, j) for v in pins]
                for p in ss:
                    if abs(p[0]) > STAGE_W / 2 - 12 or abs(p[1]) > STAGE_H / 2 - 12:
                        out.append(f'{self.title}：rx={rx:.0f} ry={j} 时编号点出框'
                                   f'（{p[0]:.0f},{p[1]:.0f}）')
                        break
                for a in range(len(ss)):
                    for b in range(a + 1, len(ss)):
                        d = math.hypot(ss[a][0] - ss[b][0], ss[a][1] - ss[b][1])
                        if d < worst[0]:
                            worst = (d, f'{self._pins[a]["n"]}/{self._pins[b]["n"]}',
                                     f'rx={rx:.0f} ry={j}')

        # 默认角度：没有 JS、以及打印时看到的就是这一帧，不能有重叠
        exp = [(p['n'], _proj(v, RX_DEF, RY_DEF)) for p, v in zip(self._pins, pins)]
        for a in range(len(exp)):
            for b in range(a + 1, len(exp)):
                d = math.hypot(exp[a][1][0] - exp[b][1][0], exp[a][1][1] - exp[b][1][1])
                if d < PIN_D:
                    out.append(f'{self.title}：默认角度下编号点 {exp[a][0]} 与 {exp[b][0]} '
                               f'相距只有 {d:.1f}px')
        self.worst = worst
        return out

    # ------------------------------------------------------------ 渲染
    def _faces_html(self, part, k, idx=0):
        o = self.origin
        ax = (part['anchor'][0] - o[0]) * k
        ay = -(part['anchor'][1] - o[1]) * k
        az = (part['anchor'][2] - o[2]) * k
        # data-f / data-c 是「点一下放大」要用的：放大倍数与「把部件中心平移到台面中心」
        # 需要的位移。都由生成期按旋转范围采样解出来，运行期只读不算。
        c, f = self._focus(idx, k)
        out = [f'<span class="m3d-p" data-i="{idx}" data-f="{_f(f)}" '
               f'data-c="{_f(c[0])},{_f(c[1])},{_f(c[2])}" '
               f'style="transform:translate3d('
               f'{_f(ax)}px,{_f(ay)}px,{_f(az)}px)">']
        op = part['op']
        for fc in part['faces']:
            w, h = fc['w'] * k, fc['h'] * k
            bg = _alpha(shade(fc['col'], fc['sc']), op) if op else shade(fc['col'], fc['sc'])
            bd = _alpha(shade(fc['col'], EDGE), min(1.0, op * 1.6) if op else 1)
            # ⚠️ 结尾的分号不能少。少了它，整条内联样式会变成
            # `border-radius:50%transform:rotateX(...)`——border-radius 吃掉了整个
            # 非法值，**后面的 transform 声明整条丢失**，端盖就变成贴在部件原点的方块。
            # 这个错是「反解 HTML 数面片」那条断言抓出来的（几何 52 张、只反解到 48 张）。
            r = 'border-radius:50%;' if part.get('cap') and fc['nm'] in ('cap', 'cb') else ''
            out.append(
                f'<span class="m3d-f" style="width:{_f(w)}px;height:{_f(h)}px;'
                f'margin:{_f(-h / 2)}px 0 0 {_f(-w / 2)}px;{r}'
                f'transform:{_tf(fc, k)};background:{bg};border-color:{bd}"></span>')
        out.append('</span>')
        return ''.join(out)

    def _pins_html(self, k):
        """编号点。

        做成 <button> 而不是 <span>：点了要放大某个部件，那它本身就是个可操作控件，
        用按钮就白拿键盘可达与焦点环。所以容器不能再写 role=\"img\"（图片里放按钮是非法的），
        改成 role=\"group\"。
        """
        o = self.origin
        names = getattr(self, '_pin_names', {})
        out = []
        for p, pi in zip(self._pins, self._pin_parts()):
            v = ((p['at'][0] - o[0]) * k, -(p['at'][1] - o[1]) * k, (p['at'][2] - o[2]) * k)
            sx, sy = _proj(v, RX_DEF, RY_DEF)
            nm = names.get(p['n']) or f'编号 {p["n"]}'
            out.append(
                f'<button type="button" class="m3d-pin" '
                f'data-a="{_f(v[0])},{_f(v[1])},{_f(v[2])}" data-part="{pi}" '
                f'style="left:calc(50% + {_f(sx)}px);top:calc(50% + {_f(sy)}px)" '
                f'title="放大：{nm}" aria-label="放大并查看：{nm}" '
                f'aria-pressed="false">{p["n"]}</button>')
        return ''.join(out)

    def legend(self, items):
        """编号图例。每一项都带着对应的部件索引——点图例与点编号点是同一个操作。

        顺手把编号→名称记下来给 _pins_html 用（按钮的 aria-label 要念得出「放大什么」，
        光念「1」对读屏用户没有意义）。
        """
        pp = dict(zip([p['n'] for p in self._pins], self._pin_parts()))
        self._pin_names = {n: t for n, t, _d in items}
        out = ['<ol class="m3d-lg">']
        for n, t, d in items:
            pi = pp.get(n, 0)
            out.append(f'  <li><button type="button" class="m3d-lb" data-part="{pi}" '
                       f'aria-pressed="false"><i>{n}</i><b>{t}</b>'
                       f'<span>{d}</span></button></li>')
        out.append('  </ol>')
        return '\n'.join(out)

    def html(self, legend='', hint=''):
        """产出模型 + 图例 + 拖拽提示。

        DOM 顺序是「台面 → 图例 → 提示」，桌面端靠 grid 把图例摆到右栏、提示留在台面下；
        窄屏时退回单列，顺序正好是「模型 → 图例 → 提示」——这也是手机上更顺的读法。
        """
        k = self.k = self._fit()
        body = ''.join(self._faces_html(p, k, i) for i, p in enumerate(self._parts))
        pins = self._pins_html(k)
        return (
            f'<div class="m3d" data-m3d>\n'
            # role=group 而不是 img：里面有编号点按钮，role=img 会把它整棵子树当图片读掉
            f'  <div class="m3d-stage" role="group" aria-label="{self.aria}" tabindex="0">\n'
            f'    <div class="m3d-world" style="--rx:{_f(RX_DEF)}deg;--ry:{_f(RY_DEF)}deg;'
            f'--m3d-f:1;--m3d-tx:0px;--m3d-ty:0px;--m3d-tz:0px">{body}</div>\n'
            f'    <div class="m3d-pins">{pins}</div>\n'
            f'    <button type="button" class="m3d-back" hidden>返回全貌</button>\n'
            f'  </div>\n'
            f'  {legend}\n'
            f'  {hint}\n'
            f'</div>\n')


def legend_html(items):
    return ('<ol class="m3d-lg">\n'
            + '\n'.join(f'    <li><i>{n}</i><b>{t}</b><span>{d}</span></li>'
                        for n, t, d in items)
            + '\n  </ol>')


HINT = ('<p class="m3d-hint"><span>拖动旋转</span><span class="sep">·</span>'
        '<span>点编号或部件放大</span><span class="sep">·</span>'
        '<span>方向键微调</span><span class="sep">·</span><span>Esc 返回全貌</span>'
        '<button type="button" class="m3d-reset">重置视角</button></p>')
