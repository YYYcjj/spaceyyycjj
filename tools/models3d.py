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
EDGE = -0.47          # 描边 = 基色再压暗，保证浅色件在浅色底上也有轮廓。
# 别压得太狠：圆柱一周十几个面片，每条边都算一条竖线，深了就是一层网格。

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
    if axis is None:
        return v
    a = math.radians(deg)
    x, y, z = v
    if axis == 'X':
        return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))
    if axis == 'Y':
        return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)


def _rots_css(rots):
    """[(轴, 角度)] → CSS 片段，顺序即 CSS 书写顺序（左侧先作用于最终结果）。"""
    return ''.join(f'rotate{ax}({_f(dg)}deg) ' for ax, dg in rots if ax)


def _rots_apply(rots, v):
    """把同一串旋转作用到向量 v 上。

    ⚠️ 必须**逆序**：CSS 的 `rotateX(a) rotateY(b)` 表示矩阵 Rx·Ry，点 p 先被 Ry 作用。
    所以这里也要从右往左套。_emitted_bbox 用它对渲染参数做反解，顺序错了会算出
    完全不同的朝向，而「包围盒与几何对不上」那条断言会立刻报出来。
    """
    for ax, dg in reversed(rots):
        v = _rot1(ax, dg, v)
    return v


def _tf(face, k):
    """把「偏移 + 一串旋转 + 距离」拼成 CSS 变换字符串。

    三个部分都要乘 k：
      · **距离**必须乘。第一版把整串变换在 box() 里就拼好了，于是面片的长宽
        按 k 缩放了、translateZ 的位移没有——k≈1 时看不出来（星舰 k=1.14 完全正常），
        k=3.44 的机器人直接崩成一个十字展开图。别再把变换字符串提前拼死。
      · **偏移**（off）是面片相对部件原点的额外位移，同样要乘——环面片段、法兰螺栓、
        斜撑这些全靠它摆位。
      · 偏移写在最左侧（最先作用于最终结果=最后生效），所以它是在**世界轴**上平移的，
        不受后面旋转影响。这正是「把这一小片放到那个坐标」想要的行为。
    """
    off = face.get('off')
    pre = ''
    if off and any(off):
        pre = (f'translate3d({_f(off[0] * k)}px,{_f(-off[1] * k)}px,'
               f'{_f(off[2] * k)}px) ')
    return (f'{pre}{_rots_css(face["rots"])}'
            f'translateZ({_f(face["z"] * k)}px)')


# ---------------------------------------------------------------- 面片纹理
#
# 纹理是「精细度」里最便宜的一档：不用多一个面片，只在面上叠一层 CSS 渐变，
# 就能把「一块光板」变成「有焊缝/瓦缝/加强筋/格栅的蒙皮」。
#
# 两个约定：
#   1. **周期按世界单位给，渲染时才乘 k**。否则同一个纹理在大模型上是密麻点、
#      在小模型上是大格子，模型之间就不像一套东西了。
#   2. 线条一律半透明黑 + 半透明白。这样纹理叠加在六面明暗之上时，仍然是
#      「同一块材料在不同受光下」，而不是贴了一层死色。
# 对比度刻意压得比较低：这些线是**成百上千条**叠在一起的，一条线看着不重，
# 密起来就是一层网。第一版用 .30/.34，截图里整个箭体像贴了瓷砖。
DKG, WHT = 'rgba(20,24,32,.19)', 'rgba(255,255,255,.24)'


def _tex_css(name, pv, ph):
    """返回 (background-image, background-size)。

    pv / ph 是**渲染像素**周期：pv 沿面片高度（横线之间的间距），
    ph 沿面片宽度（竖线之间的间距）。两者分开传，是因为回转体的侧面片要把周期
    **对齐到自身的宽高**（见下面 _faces_html 里的说明），否则每张面片各自从左上角
    起铺，相邻面片之间会错半个周期，一整圈看过去就是一片砖墙。
    """
    if not name:
        return '', ''
    p = max(3.0, pv)
    q = max(3.0, ph)
    if name == 'seam':
        # 环向焊缝的**细纹**层。主要的几条环缝是几何分段做出来的（cyl 的 segs），
        # 纹理只负责补上更细的那一层。
        #
        # ⚠️ 别指望纹理能当主结构线：相邻面片的倾斜角不同，屏幕上的周期就不同，
        # 一条横线穿过十几个面片之后会累计错开好几个像素，看着像砖墙。
        # 几何棱线没有这个问题（它是真的 3D 边），所以该用几何的地方别用纹理。
        return (f'repeating-linear-gradient(180deg,rgba(20,24,32,.16) 0 1.4px,'
                f'transparent 1.4px {_f(p)}px)', '')
    if name == 'rib':           # 纵向加强筋：竖线，左侧压暗、右侧提亮
        return (f'repeating-linear-gradient(90deg,{DKG} 0 1.4px,{WHT} 1.4px 2.8px,'
                f'transparent 2.8px {_f(q)}px)', '')
    if name == 'tile':          # 热盾瓦片：正交砖缝
        return (f'repeating-linear-gradient(180deg,{DKG} 0 1.2px,transparent 1.2px '
                f'{_f(p)}px),'
                f'repeating-linear-gradient(90deg,{DKG} 0 1.2px,transparent 1.2px '
                f'{_f(q * .82)}px)', '')
    if name == 'plate':         # 蒙皮拼板：稀疏方格，缝很淡
        return (f'repeating-linear-gradient(180deg,rgba(20,24,32,.14) 0 1px,'
                f'transparent 1px {_f(p)}px),'
                f'repeating-linear-gradient(90deg,rgba(20,24,32,.14) 0 1px,'
                f'transparent 1px {_f(q * 1.35)}px)', '')
    if name == 'grid':          # 太阳能板格栅：密格
        return (f'repeating-linear-gradient(180deg,{DKG} 0 1px,transparent 1px '
                f'{_f(p)}px),'
                f'repeating-linear-gradient(90deg,{DKG} 0 1px,transparent 1px '
                f'{_f(q)}px)', '')
    if name == 'slat':          # 百叶散热板：单向粗条纹
        return (f'repeating-linear-gradient(180deg,rgba(20,24,32,.18) 0 2px,'
                f'transparent 2px {_f(p)}px)', '')
    if name == 'tube':          # 喷管再生冷却管束：极密的竖条
        return (f'repeating-linear-gradient(90deg,rgba(20,24,32,.24) 0 1.2px,'
                f'transparent 1.2px {_f(q)}px)', '')
    if name == 'dot':           # 点阵：舷窗、指示灯、螺栓环
        return (f'radial-gradient(circle at 50% 50%,rgba(24,30,40,.32) 0 1.5px,'
                f'transparent 2.1px)', f'{_f(q)}px {_f(p)}px')
    if name == 'stripe':        # 斜条纹：警示/检修带
        return (f'repeating-linear-gradient(45deg,rgba(20,24,32,.15) 0 3px,'
                f'transparent 3px {_f(p)}px)', '')
    return '', ''


# ---------------------------------------------------------------- 着色
#
# 每个面片一个平色是不够的：一圈十几个平面、相邻法线差二十几度，拼起来就是一根
# **棱柱**——第一版模型看着「像积木」的根因就在这里，而不是零件不够多。
# 真实 3D 的解法是平滑着色（Gouraud）：明暗按法线算，在面片内部插值。
# CSS 可以精确复刻这件事——给每个侧面片一条 linear-gradient，两端取相邻面片的
# 明暗、中间取自己的。一圈面片在视觉上就接成了连续曲面，而几何仍然只是平面。
#
# 三个分量：环境 + 漫反射 + 高光。**高光那一项是「金属感」的来源**：
# 没有它，模型看着像塑料；有一条窄亮的带子，才读得出是钢、是铝、是喷了漆的筒。
AMB, DIF, SPE = -0.26, 0.46, 0.42
# 高光宽窄（幂次）。**别调大**：一圈面片有限，窄到不足一个面片就会变成
# 「某一片特别亮」的亮斑，比没有高光更假。7 次幂的半宽约 ±26°，正好跨两三片，
# 落在片内的部分还能靠渐变插值补圆。实测 6 次幂的峰值只比正面亮 3%，看不出金属感。
SPEC_P = 7.0
SC_MAX, SC_MIN = 0.46, -0.30      # 明暗系数的上下限


def _half_vec():
    """视线与光线的半程向量（模型空间，视线取 +z）。

    两个向量都固定，意味着光照是**烘进模型**的：转模型时光跟着转。这与物理不符，
    但和已有的做法一致（六面明暗表同样是烘死的），而且省掉每帧重算上千个面片的代价——
    真要每帧重算，就得把着色从 CSS 挪进 canvas，那就不是这套方案了。
    """
    hx, hy, hz = LX, LY, LZ + 1.0
    m = math.sqrt(hx * hx + hy * hy + hz * hz) or 1.0
    return hx / m, hy / m, hz / m


HX, HY, HZ = _half_vec()


def _sc3(nx, ny, nz):
    """给定**外法线**的明暗系数（环境 + 漫反射 + 高光）。

    法线会被归一化，所以调用点可以传未经归一化的方向（椭球面法线那种写法很啰嗦）。

    ⚠️ 法线的 y 分量必须参与。第一版只用 nx/nz 算，于是所有圆锥面——鼻锥、
    喷管扩张段、抛物面天线——都是「一圈一样亮」，看着是平的纸片而不是回转体。
    """
    m = math.sqrt(nx * nx + ny * ny + nz * nz)
    if m > 1e-9:
        nx, ny, nz = nx / m, ny / m, nz / m
    lam = nx * LX + ny * LY + nz * LZ
    if lam < 0.0:
        lam = 0.0
    d = nx * HX + ny * HY + nz * HZ
    sp = d ** SPEC_P if d > 0.0 else 0.0
    v = AMB + DIF * lam + SPE * sp
    return SC_MIN if v < SC_MIN else (SC_MAX if v > SC_MAX else v)


def _grad(dir_deg, c, s0, sm, s1, op=None):
    """把一个面片从「单色」升级成「跨面渐变」——这就是平滑着色。

    dir_deg 是 CSS 渐变角，**起点必须落在 θ 小的那一侧**。三个朝向的对应关系
    在各自图元里注明（axis='x' 是 0deg，其余是 90deg），写反的后果是明暗倒过来：
    不难看，但高光会跑到背光面去，而且不会报错。

    中间那一档单独传，不是两端平均——高光正好落在面片中央时，线性插值会把它抹平，
    而「高光被抹平」恰恰是最容易发生的情况（一圈 14 片、高光半宽 27°，总有一片正对着）。
    """
    def col(s):
        return _alpha(shade(c, s), op) if op else shade(c, s)
    return (dir_deg,
            f'linear-gradient({_f(dir_deg)}deg,{col(s0)} 0%,'
            f'{col(sm)} 50%,{col(s1)} 100%)')


def _face(rots, z, w, h, col, sc, nm='', tex=None, tp=None, clip=None, off=None,
          noedge=False, grad=None, flat=False):
    """一张面片。

    rots 是 [(轴, 角度)]，按 CSS 书写顺序（左起先作用于最终结果）。
    z 是沿面片法线的位移；off 是相对部件原点的**世界轴**额外位移（环面、螺栓、斜撑用它）。
    clip 是 clip-path 的 polygon 百分比串（把矩形裁成梯形，锥面靠它精确）。
    tex / tp 是纹理名与周期（世界单位；渲染时乘 k）。
    """
    return dict(nm=nm, rots=tuple(rots), z=z, w=w, h=h, col=col, sc=sc,
                tex=tex, tp=tp, clip=clip, off=off, noedge=noedge, grad=grad,
                flat=flat)


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
    def box(self, x, y, z, w, h, d, c='steel', op=None, tex=None, tp=None):
        """轴对齐长方体，参数是**左下后角**与三边长度（y 向上）。"""
        c = PAL.get(c, c)          # 色名 → 十六进制。渲染时只认十六进制，别把色名传下去
        cx, cy, cz = x + w / 2.0, y + h / 2.0, z + d / 2.0
        hw, hh, hd = w / 2.0, h / 2.0, d / 2.0
        faces = [
            _face([], hd, w, h, c, LIGHT['fr'], 'fr', tex, tp),
            _face([('Y', 180)], hd, w, h, c, LIGHT['bk'], 'bk', tex, tp),
            _face([('Y', 90)], hw, d, h, c, LIGHT['rt'], 'rt', tex, tp),
            _face([('Y', -90)], hw, d, h, c, LIGHT['lf'], 'lf', tex, tp),
            _face([('X', 90)], hh, w, d, c, LIGHT['tp'], 'tp', tex, tp),
            _face([('X', -90)], hh, w, d, c, LIGHT['bt'], 'bt', tex, tp),
        ]
        pts = [(cx + sx * hw, cy + sy * hh, cz + sz * hd)
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        self._parts.append(dict(anchor=(cx, cy, cz), faces=faces, pts=pts, op=op))
        return self

    def _cyl_side(self, c, n, r_of, y_of, segs, tex, tp):
        """回转体侧面：按轮廓分段，每段是一块**真的倾斜**的梯形面片。

        cyl / frustum / nozzle / dome / sphere 都是「半径随高度变」的回转体，
        只是 r_of(t) 不同，所以共用这一份实现。

        ⚠️ **`y_of(t)` 必须返回相对部件锚点的高度**（不是绝对高度）：它直接进 off，
        而 off 是相对 anchor 的。传绝对高度会让整圈侧面片整体平移掉一个 anchor 的量。

        ## 为什么面片必须倾斜（这一段是这一版最关键的修正）

        最初的做法是：面片永远是**竖直平面**，放在平均半径 rm=(r0+r1)/2 处，
        再用 clip-path 把上边裁窄，假装它是个锥面。看起来能糊过去，但只要轮廓收得快
        就露馅——因为**裁剪只让顶边变窄，没有让它往轴心靠**：顶边仍然停在半径 rm 上。
        于是一段一段叠起来，每段顶端都停在自己那个 rm 上，段与段之间留下明显的径向空隙，
        整个穹顶变成一层层带缺口的「婚礼蛋糕」。穹顶、鼻锥、喷管、抛物面碗全都是这个问题。

        正解是让面片自己的平面沿轮廓倾斜：
          · tilt = atan2(dr, dy)（在「半径—高度」平面里的轮廓倾角）
          · 面片高度取**斜边长** L=hypot(dr,dy)，于是局部 +y 正好沿着轮廓走
          · 局部 +y 经过 tilt 后是 (0,cosθ,sinθ)，即「往上走也往外走」，顶边自然落到 r1
          · translateZ 沿倾斜后的法线走，所以要除 cos(tilt)，再把多出来的竖直分量用 off 补回来

        倾斜后局部法线正好等于锥面的真实法线 (dy·sinθ, −dr, dy·cosθ)，
        所以高光、明暗、穹顶的「顶上亮」全部自动正确——不用再单独算一遍。

        ## 别把 y 递减的段直接丢进来

        轮廓必须**从下往上**遍历（dy>0）。面片局部 +y 在屏幕上就是「上」，
        传一个 dy<0 的段会让法线朝内、明暗反掉。所以下面先做一次交换，
        让每个段都满足 y0<y1；球体的下半球因此会自动变成 dr<0 的段。
        """
        faces = []
        half = math.pi / n
        for i in range(n):
            th = 360.0 * i / n
            a = math.radians(th)
            for si in range(max(1, segs)):
                t0, t1 = si / float(segs), (si + 1) / float(segs)
                r0, r1 = r_of(t0), r_of(t1)
                y0, y1 = y_of(t0), y_of(t1)
                if y1 < y0:                       # 统一成「从下往上」，见上面那段说明
                    r0, r1, y0, y1 = r1, r0, y1, y0
                dr, dy = r1 - r0, y1 - y0
                base = max(r0, r1)
                if dy < 1e-6 or base < 1e-6:
                    continue                      # 退化段（极点、零长度）直接跳过
                # ⚠️ 是 atan2(**−dr**, dy)，不是 atan2(dr, dy)。CSS 里元素局部 +y 是**向下**的，
                # 而"沿轮廓往上"在 CSS 的 +y 里是往下的方向，所以倾斜角要取反号。
                # 写反的症状很有欺骗性：面片位置大致还对，只是**法线上下颠倒**——
                # 穹顶变成"底下亮、顶上暗"，锥面看着像倒扣的碗，而所有包围盒断言都是绿的。
                tilt = math.degrees(math.atan2(-dr, dy))
                rm = (r0 + r1) / 2.0
                tr = math.radians(tilt)
                L = math.hypot(dr, dy)
                # 顶边/底边各自按自己的半径算宽度，两侧都要收：
                # 取较大的半径作基准宽，两端分别内收 (1−r/base)×50%。
                w = 2 * base * math.sin(math.pi / n) * 1.10
                itop, ibot = (1 - r1 / base) * 50.0, (1 - r0 / base) * 50.0
                clip = None
                if itop > 0.05 or ibot > 0.05:
                    clip = (f'polygon({_f(itop)}% 0,{_f(100 - itop)}% 0,'
                            f'{_f(100 - ibot)}% 100%,{_f(ibot)}% 100%)')
                # translateZ 是沿**倾斜后**的法线走的，竖直分量要补回来，
                # 否则整个部件的侧面会整体偏移 rm·tan(tilt)（穹顶能偏出好几个单位）。
                z = rm / math.cos(tr) if abs(tr) > 1e-9 else rm
                # translateZ 沿倾斜后的法线走，在世界上多出 z·sin(tilt) 的竖直位移，
                # 要在这里减掉（同一条符号约定：世界 y 与 CSS y 相反）。
                off = (0.0, (y0 + y1) / 2.0 - rm * math.tan(tr), 0.0)
                # 真实法线：轮廓切线 (dr, dy) 的外法线是 (dy, −dr)，绕轴铺开即
                # (dy·sinθ, −dr, dy·cosθ)。_sc3 会归一化，所以不用在这里除长度。
                nrm = lambda ang, _y=dy, _d=dr: (                # noqa: E731
                    _y * math.sin(ang), -_d, _y * math.cos(ang))
                rots = [('Y', th), ('X', tilt)]
                grad = _grad(90.0, c, _sc3(*nrm(a - half)), _sc3(*nrm(a)),
                             _sc3(*nrm(a + half)))
                faces.append(_face(rots, z, w, L * 1.03, c, _sc3(*nrm(a)),
                                   f's{i}_{si}', tex, tp, clip=clip, off=off,
                                   noedge=True, grad=grad))
        return faces

    def _tube_faces(self, c, n, r, h, axis, tex, tp, caps=True, segs=1):
        """绕给定轴的圆筒侧面 + 两个端盖。

        三种朝向都只用到**一个**轴旋转，所以 _emitted_bbox 那套单轴反解照样成立：
          · axis='y'：法线在 x-z 平面 → rotateY(th)
          · axis='x'：法线在 y-z 平面 → rotateX(th)
          · axis='z'：法线在 x-y 平面 → 需要 rotateZ(th) rotateX(90deg)
            （rotateZ 不动 z 轴，所以必须先把面片转平再绕 z 铺开）
        三种的本地 x / y 轴落点不同，宽度与高度要跟着换位置，这个别照抄。
        """
        faces = []
        half = math.pi / n              # 面片跨越的半个角（弧度）
        for i in range(n):
            th = 360.0 * i / n
            t = math.radians(th)
            if axis == 'y':
                nrm = lambda a: (math.sin(a), 0.0, math.cos(a))          # noqa: E731
                rots = [('Y', th)]
                # 渐变起点在 θ 小的一侧：axis='y' 的局部 +x 就是切向（切向 = dn/dθ），
                # 90deg 的起点在左 → 左 = θ−δ/2。
                gdir = 90.0
            elif axis == 'x':
                nrm = lambda a: (0.0, -math.sin(a), math.cos(a))         # noqa: E731
                rots = [('X', th)]
                # axis='x' 的局部 +x 是**轴向**、+y 才是切向，而局部 +y 在屏幕上是向下的，
                # 所以「θ 增大」的方向是向上的 → 渐变角要写 0deg（起点在下）。
                gdir = 0.0
            else:
                nrm = lambda a: (math.sin(a), -math.cos(a), 0.0)         # noqa: E731
                rots = [('Z', th), ('X', 90)]
                gdir = 90.0
            grad = _grad(gdir, c, _sc3(*nrm(t - half)), _sc3(*nrm(t)),
                         _sc3(*nrm(t + half)))
            sc = _sc3(*nrm(t))
            chord = 2 * r * math.sin(math.pi / n) * 1.10    # ×1.10 重叠，免得漏缝
            for si in range(max(1, segs)):
                f0, f1 = si / float(segs) - 0.5, (si + 1) / float(segs) - 0.5
                a_mid = (f0 + f1) / 2.0 * h
                segh = abs(f1 - f0) * h * 1.04              # 纵向也留 4% 重叠
                # ⚠️ 面片的宽/高与轴的关系每种朝向都不同，别照抄：
                #   axis='x'：局部 x = 轴向（宽给段高），局部 y = 切向（高给 chord）
                #   axis='y' / 'z'：局部 x = 切向（宽给 chord），局部 y = 轴向（高给段高）
                # 传反了不会报错、也不会崩，只是整根圆柱会变成一个「薄片十字」，
                # 靠「渲染包围盒 == 几何包围盒」那条断言才会漏出来（cyl-z 就这么被抓到）。
                if axis == 'x':
                    w, hh, off = segh, chord, (a_mid, 0.0, 0.0)
                elif axis == 'y':
                    w, hh, off = chord, segh, (0.0, a_mid, 0.0)
                else:
                    w, hh, off = chord, segh, (0.0, 0.0, a_mid)
                faces.append(_face(rots, r, w, hh, c, sc, f's{i}_{si}', tex, tp,
                                   noedge=True, off=off, grad=grad))
        if caps:
            if axis == 'y':
                faces.append(_face([('X', 90)], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['tp'], 'cap', tex, tp))
                faces.append(_face([('X', -90)], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['bt'], 'cb', tex, tp))
            elif axis == 'x':
                faces.append(_face([('Y', 90)], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['rt'], 'cap', tex, tp))
                faces.append(_face([('Y', -90)], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['lf'], 'cb', tex, tp))
            else:
                faces.append(_face([], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['fr'], 'cap', tex, tp))
                faces.append(_face([('Y', 180)], h / 2.0, 2 * r, 2 * r, c,
                                   LIGHT['bk'], 'cb', tex, tp))
        return faces

    def cyl(self, x, y0, z, r, h, c='steel', n=16, op=None, axis='y',
            tex=None, tp=None, caps=True, segs=1):
        """圆柱。默认竖直（y0 是底面高度，轴线在 (x, z)）；axis='x' / 'z' 可横放。

        横放是「精细度」的必要条件：滚轮、横置贮罐、铰链轴、滚筒这些全是躺着的，
        原先只能用竖直圆柱硬凑，看起来像钉子。
        """
        c = PAL.get(c, c)
        faces = self._tube_faces(c, n, r, h, axis, tex, tp, caps, segs)
        if axis == 'y':
            anchor = (x, y0 + h / 2.0, z)
            pts = [(x + r * math.sin(2 * math.pi * i / 12), yy,
                    z + r * math.cos(2 * math.pi * i / 12))
                   for i in range(12) for yy in (y0, y0 + h)]
        elif axis == 'x':
            anchor = (x, y0, z)
            pts = [(xx, y0 + r * math.sin(2 * math.pi * i / 12),
                    z + r * math.cos(2 * math.pi * i / 12))
                   for i in range(12) for xx in (x - h / 2.0, x + h / 2.0)]
        else:
            anchor = (x, y0, z)
            pts = [(x + r * math.cos(2 * math.pi * i / 12),
                    y0 + r * math.sin(2 * math.pi * i / 12),
                    zz) for i in range(12) for zz in (z - h / 2.0, z + h / 2.0)]
        self._parts.append(dict(anchor=anchor, faces=faces, pts=pts, op=op,
                                cap=bool(caps)))
        return self

    def frustum(self, x, y0, z, r0, r1, h, c='steel', n=16, segs=1, op=None,
                tex=None, tp=None, cap_top=True, cap_bot=True):
        """圆台 / 圆锥。r0 是底半径、r1 是顶半径（给 0 就是圆锥）。

        鼻锥、喷管扩张段、抛物面天线、过渡段全靠它——原先这些东西都是用等径
        圆柱硬凑的，所以看起来像个罐头。segs > 1 时半径分段线性，段缝正好
        成了「面板拼装」的视觉线索。
        """
        c = PAL.get(c, c)
        faces = self._cyl_side(c, n, lambda t: r0 + (r1 - r0) * t,
                               lambda t: h * (t - 0.5), max(1, segs), tex, tp)
        # 端盖**不给 off**：`rotateX(90) translateZ(h/2)` 已经把面片送到 anchor 上方 h/2，
        # 再补一个同样大小的 off 就是叠两次，整个顶盖会飞出去一倍高度。
        if cap_top and r1 > 0.01:
            faces.append(_face([('X', 90)], h / 2.0, 2 * r1, 2 * r1, c,
                               LIGHT['tp'], 'cap', tex, tp))
        if cap_bot and r0 > 0.01:
            faces.append(_face([('X', -90)], h / 2.0, 2 * r0, 2 * r0, c,
                               LIGHT['bt'], 'cb', tex, tp))
        pts = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            pts.append((x + r0 * math.sin(t), y0, z + r0 * math.cos(t)))
            if r1 > 0.01:
                pts.append((x + r1 * math.sin(t), y0 + h, z + r1 * math.cos(t)))
        self._parts.append(dict(anchor=(x, y0 + h / 2.0, z), faces=faces, pts=pts,
                                op=op, cap=True))
        return self

    def dome(self, x, y0, z, r, h, c='steel', n=12, segs=3, op=None,
             tex=None, tp=None):
        """穹顶 / 球冠。半径按 cos、高度按 sin 收口，用 segs 段圆台叠出来。

        贮箱端头、球罐、观察穹顶用它。segs=3 就已经看不出折线了。

        轮廓交给 `_cyl_side`，于是自动拿到**倾斜的面片**——穹顶是回转体里收口最快的
        （半径从 r 一路收到 0），用竖直面片 + 裁剪糊的话，段与段之间的径向空隙最大，
        整顶会变成一层层带缺口的「婚礼蛋糕」（第一版就是这样）。
        """
        c = PAL.get(c, c)
        # φ: 0（根部）→ π/2（顶点）；锚点在穹顶的几何中心 y0+h/2，所以高度要减 h/2
        faces = self._cyl_side(c, n,
                               lambda t: r * math.cos(math.pi / 2 * t),
                               lambda t: h * math.sin(math.pi / 2 * t) - h / 2.0,
                               max(1, segs), tex, tp)
        pts = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            for f in (0.0, 0.5, 1.0):
                rr = r * math.cos(math.pi / 2 * f)
                pts.append((x + rr * math.sin(t),
                            y0 + math.sin(math.pi / 2 * f) * h,
                            z + rr * math.cos(t)))
        self._parts.append(dict(anchor=(x, y0 + h / 2.0, z), faces=faces, pts=pts,
                                op=op, cap=True))
        return self

    def nozzle(self, x, y0, z, rc, re, h, c='dark', n=14, segs=4, op=None,
               tex='tube', tp=3.2):
        """钟形喷管：从喉部 rc 扩到出口 re，半径按指数曲线走。

        真实喷管不是圆锥（前段收得快、后段平缓），用 t**1.7 近似。
        tex 默认给管束纹理——再生冷却的管束本来就是喷管最好认的特征。
        """
        c = PAL.get(c, c)
        r_of = lambda t: rc + (re - rc) * (t ** 1.7)     # noqa: E731
        faces = self._cyl_side(c, n, r_of, lambda t: h * (t - 0.5), max(1, segs), tex, tp)
        if rc > 0.01:
            faces.append(_face([('X', -90)], h / 2.0, 2 * rc, 2 * rc, c,
                               LIGHT['bt'], 'cb'))
        pts = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            for f in (0.0, 0.5, 1.0):
                rr = rc + (re - rc) * (f ** 1.7)
                pts.append((x + rr * math.sin(t), y0 + h * f, z + rr * math.cos(t)))
        self._parts.append(dict(anchor=(x, y0 + h / 2.0, z), faces=faces, pts=pts,
                                op=op, cap=True))
        return self

    def taper(self, x, y0, z, w0, d0, w1, d1, h, c='steel', op=None, tex=None, tp=None):
        """四棱台（下大上小）。翼面、头锥、整流罩、渐缩过渡段用它。

        四个侧面用 clip-path 裁成**精确梯形**，并且和回转体一样**真的倾斜**——
        矩形硬拼会让翼面看起来是块砖，而竖直平面 + 裁剪会让上下端错开
        （顶边停在平均半宽处，跟顶盖对不上，出一圈台阶）。

        倾斜角的推法与 `_cyl_side` 完全一致，只是"半径"换成"半宽/半深"：
        `t = atan2(-Δ半尺寸, h)`。四个面都是这个式子（左右两面镜像，但符号抵消了）。
        符号同样按 CSS 的 y 向下取：写反的话法线会上下颠倒。
        """
        c = PAL.get(c, c)
        hw0, hd0, hw1, hd1 = w0 / 2.0, d0 / 2.0, w1 / 2.0, d1 / 2.0

        def side(a0, a1, base, rm, sc, rots, off_x, off_z):
            """一块倾斜的梯形侧面片。a0/a1 是下/上端的宽度（x 或 z 方向）。"""
            lo, hi = min(a0, a1), max(a0, a1)
            ins = (1.0 - lo / hi) * 50.0 if hi > 0.01 else 0.0
            top, bot = (ins, 0.0) if a1 < a0 else (0.0, ins)
            clip = (f'polygon({_f(top)}% 0,{_f(100 - top)}% 0,'
                    f'{_f(100 - bot)}% 100%,{_f(bot)}% 100%)')
            dd = (a1 - a0) / 2.0                      # 上端相对下端的半尺寸变化
            tilt = math.degrees(math.atan2(-dd, h))
            tr = math.radians(tilt)
            L = math.hypot(dd, h)
            # off_y 只用来抵消 translateZ 沿倾斜法线带来的竖直位移；面片中心就在锚点上，
            # 所以没有 (y0+y1)/2 那一项（回转体那边才有）。加错了的后果是整个面片
            # 整体下移 h/2，翼面和顶盖错开一大截——包围盒断言会报「超出几何范围」。
            return _face(rots + [('X', tilt)],
                         rm / math.cos(tr) if abs(tr) > 1e-9 else rm,
                         hi, L * 1.015, c, sc, 'sd', tex, tp, clip=clip,
                         off=(off_x, -rm * math.tan(tr), off_z))

        rmx, rmz = (hw0 + hw1) / 2.0, (hd0 + hd1) / 2.0
        faces = [
            side(w0, w1, hw0, rmz, LIGHT['fr'], [], 0.0, 0.0),               # 前
            side(w0, w1, hw0, rmz, LIGHT['bk'], [('Y', 180)], 0.0, 0.0),     # 后
            side(d0, d1, hd0, rmx, LIGHT['rt'], [('Y', 90)], 0.0, 0.0),      # 右
            side(d0, d1, hd0, rmx, LIGHT['lf'], [('Y', -90)], 0.0, 0.0),     # 左
            _face([('X', 90)], h / 2.0, w1, d1, c, LIGHT['tp'], 'cap', tex, tp),
            _face([('X', -90)], h / 2.0, w0, d0, c, LIGHT['bt'], 'cb', tex, tp),
        ]
        pts = []
        for sx in (-1, 1):
            for sz in (-1, 1):
                pts.append((x + sx * hw0, y0, z + sz * hd0))
                pts.append((x + sx * hw1, y0 + h, z + sz * hd1))
        self._parts.append(dict(anchor=(x, y0 + h / 2.0, z), faces=faces, pts=pts,
                                op=op, cap=True))
        return self

    def ring(self, x, y0, z, ro, ri, h, c='steel', n=12, op=None, tex=None, tp=None,
             inner=True):
        """环形箍 / 法兰 / 对接环。外壁 + 内壁 + 上环面 + 下环面。

        原先的「级间段」「热分离环」都是一个实心短圆柱，转到侧面就露馅——
        环是**中空**的，内壁那圈暗面正是它区别于圆盘的地方。

        `inner=False` 只留「外壁 + 上环面」，面片数减半，用在**套在箭体外面**的箍上：
        那种地方内壁本来就被箭体挡住，底环面也永远看不到。
        """
        c = PAL.get(c, c)
        rm = (ro + ri) / 2.0
        wann = (ro - ri)
        faces = []
        half = math.pi / n
        for i in range(n):
            th = 360.0 * i / n
            t = math.radians(th)
            nx, nz = math.sin(t), math.cos(t)
            # 外壁走同一套着色（含高光）：法兰、对接环、监护环都是金属件，
            # 有没有那圈高光直接决定它像不像机加工出来的东西。
            sc = _sc3(nx, 0.0, nz)
            grad = _grad(90.0, c,
                         _sc3(math.sin(t - half), 0.0, math.cos(t - half)), sc,
                         _sc3(math.sin(t + half), 0.0, math.cos(t + half)))
            faces.append(_face([('Y', th)], ro, 2 * ro * math.sin(math.pi / n) * 1.10,
                               h, c, sc, f'o{i}', tex, tp, noedge=True, grad=grad))
            if inner:
                # 内壁法线朝**内**，永远背光 → 恒暗。这是中空环与实心盘的区别所在，
                # 所以不要给它加渐变，压平反而更像「里面是空的」。
                faces.append(_face([('Y', th)], ri, wann * 0.92, h, c,
                                   max(-0.62, sc - 0.34), f'i{i}', tex, tp,
                                   noedge=True))
            for s, d in (((1, h / 2.0),) if not inner else ((1, h / 2.0), (-1, h / 2.0))):
                # 环面片：水平（法线 ±y）且切向要与 th 对齐，所以是
                # `rotateY(th) rotateX(±90deg)`——只靠 rotateX 的话面片永远朝着世界 x 轴，
                # 一圈环面会变成一圈互相垂直的碎片。位置交给 off（径向）与 translateZ（轴向）。
                faces.append(_face([('Y', th), ('X', 90 * s)], s * h / 2.0,
                                   2 * rm * math.sin(math.pi / n) * 1.10, wann * 1.06,
                                   c, LIGHT['tp'] if s > 0 else LIGHT['bt'],
                                   f'a{i}{s}', tex, tp,
                                   off=(rm * nx, 0.0, rm * nz)))
        pts = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            for rr in (ri, ro):
                for yy in (y0, y0 + h):
                    pts.append((x + rr * math.sin(t), yy, z + rr * math.cos(t)))
        self._parts.append(dict(anchor=(x, y0 + h / 2.0, z), faces=faces, pts=pts,
                                op=op, cap=True))
        return self

    def arc(self, x, y0, z, r, h, a0, a1, c='steel', n=6, segs=1, op=None,
            tex=None, tp=None, cap_top=False, cap_bot=False, jitter=0.0, flat=False):
        """圆柱面上的一段**弧形贴片**（角度 a0→a1，度）。

        很多细节只占圆周的一段：迎风面的热盾瓦片区、一圈舷窗带、局部蒙皮补片、
        整流罩的半边。用整圈圆柱去凑会多出十几张永远看不见的面，用 box 去凑
        又贴不上曲面。

        ⚠️ 锚点取弧的几何中心（弦中点），所以面片的位置靠 off 给、translateZ 留 0。
        不能用「锚点在轴心 + translateZ(r)」那套——那样锚点就不在几何中心了，
        而锚点必须在几何中心是聚焦功能的前提（见 problems 里的断言）。
        """
        c = PAL.get(c, c)
        a0, a1 = float(a0), float(a1)
        dth = (a1 - a0) / n
        half = math.radians(abs(dth)) / 2.0
        faces, pts = [], []
        for i in range(n):
            th0, th1 = a0 + i * dth, a0 + (i + 1) * dth
            thm = (th0 + th1) / 2.0
            t = math.radians(thm)
            nx, nz = math.sin(t), math.cos(t)
            # 逐片微差：热盾瓦片、蒙皮补片这类东西**不可能一样深浅**，一圈完全均匀
            # 反而假。用面片序号的散列做扰动，**不能用 random**——构建必须逐字节可重复，
            # 否则「远端 blob SHA 与本地一致」那条校验会随机失败。
            jit0 = ((i * 2654435761) % 997) / 997.0 - 0.5
            sc = _sc3(nx, 0.0, nz) + jit0 * 2.0 * jitter
            # flat=True 时不给渐变：瓦片本身就是一块块平的，给它平滑过渡反而不像瓦片。
            grad = None if flat else _grad(
                90.0, c,
                _sc3(math.sin(t - half), 0.0, math.cos(t - half)) + jit0 * jitter,
                sc,
                _sc3(math.sin(t + half), 0.0, math.cos(t + half)) + jit0 * jitter)
            chord = 2 * r * math.sin(math.radians(abs(dth)) / 2.0) * 1.10
            faces.append(_face([('Y', thm)], 0.0, chord, h * 1.02, c, sc, f'a{i}',
                               tex, tp, noedge=True, grad=grad, flat=flat))
            pts.append((x + r * nx, y0, z + r * nz))
            pts.append((x + r * nx, y0 + h, z + r * nz))
        for th in (a0, a1):
            t = math.radians(th)
            pts.append((x + r * math.sin(t), y0, z + r * math.cos(t)))
            pts.append((x + r * math.sin(t), y0 + h, z + r * math.cos(t)))
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        zs = [q[2] for q in pts]
        ax, ay, az = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0,
                      (min(zs) + max(zs)) / 2.0)
        for i, fc in enumerate(faces):
            thm = a0 + (i + 0.5) * dth
            t = math.radians(thm)
            fc['off'] = (x + r * math.sin(t) - ax, y0 + h / 2.0 - ay,
                         z + r * math.cos(t) - az)
        self._parts.append(dict(anchor=(ax, ay, az), faces=faces, pts=pts, op=op))
        return self

    def sphere(self, x, y, z, r, c='steel', n=10, nv=4, op=None, tex=None, tp=None):
        """球（按纬向切带）。球罐、球形接头、关节用它；n×nv 就是面片数，别开太大。

        锚点取球心——这也是「部件锚点必须落在几何中心」那条断言的来源：
        聚焦是丢掉部件的 translate3d(锚点) 再把几何按锚点缩放，锚点一偏就飞。

        轮廓同样交给 `_cyl_side`：φ 从 0（北极）到 π（南极），
        半径 R·sinφ、高度 R·cosφ。注意下半球的 y 是递减的，
        `_cyl_side` 会自己把它翻成「从下往上」再算倾角，所以 dr 会自然变号。
        """
        c = PAL.get(c, c)
        faces = self._cyl_side(c, n,
                               lambda t: r * math.sin(math.pi * t),
                               lambda t: r * math.cos(math.pi * t),
                               max(1, nv), tex, tp)
        pts = []
        for i in range(8):
            t = 2 * math.pi * i / 8
            for v in range(nv + 1):
                fr = v / float(nv)
                rr = r * math.sin(math.pi * fr)
                pts.append((x + rr * math.sin(t), y + r * math.cos(math.pi * fr),
                            z + rr * math.cos(t)))
        self._parts.append(dict(anchor=(x, y, z), faces=faces, pts=pts, op=op))
        return self

    def plate(self, x, y, z, w, d, c='blue2', t=1.6, op=None, tex=None, tp=None):
        """水平薄板（太阳帆板、热辐射板、光帆）。"""
        return self.box(x - w / 2, y, z - d / 2, w, t, d, c, op, tex, tp)

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
    # 面片：宽/高/对中/（可选的偏移与一串旋转）/法线位移。
    # ⚠️ 组 5~7 是 off、组 8 是旋转串、组 9 是 translateZ——它们与 _faces_html 里的
    # 书写顺序一一对应。改了那边的拼接顺序，这里必须同改，否则反解会静默少认面片
    # （后面「反解到的面片数必须等于几何定义数」那条会报出来）。
    _RE_FACE = re.compile(
        r'width:([-\d.]+)px;height:([-\d.]+)px;margin:([-\d.]+)px 0 0 ([-\d.]+)px;'
        r'(?:border-radius:50%;)?'
        r'transform:(?:translate3d\(([-\d.]+)px,([-\d.]+)px,([-\d.]+)px\) )?'
        r'((?:rotate[XYZ]\([-\d.]+deg\) )*)translateZ\(([-\d.]+)px\)')
    _RE_ROT = re.compile(r'rotate([XYZ])\(([-\d.]+)deg\)')

    @staticmethod
    def _has_grad(css):
        """这段样式里有没有**平滑着色的那条** linear-gradient。

        ⚠️ 不能直接找 `linear-gradient` 子串：纹理用的是
        `repeating-linear-gradient(...)`，它**包含**这个子串。第一版就是这么写的，
        结果每张带纹理的面片都判成"有渐变"，负向测试（把渐变改成 None）照样全绿——
        断言等于没写。所以改成数差值：出现次数减去 repeating 的次数。
        """
        return (css.count('linear-gradient(') - css.count('repeating-linear-gradient(')) > 0
    # 梯形裁剪：四个百分比分别是 上左/上右/下右/下左
    _RE_CLIP = re.compile(
        r'clip-path:polygon\(([-\d.]+)% 0,([-\d.]+)% 0,'
        r'([-\d.]+)% 100%,([-\d.]+)% 100%\)')

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
        self._part_bbox = []         # 每个部件自己的渲染包围盒（逐件断言用，见 problems）
        self._gap = []               # 「渲染参数 vs 几何定义」的逐项差异
        self._seam = []              # 回转体分段的接缝记录（见 problems 里的接缝断言）
        self._n_noedge = self._n_grad = 0
        for i, part in enumerate(self._parts):
            p_lo, p_hi = [1e9] * 3, [-1e9] * 3
            chunk = self._faces_html(part, k, i)
            h = self._RE_HDR.search(chunk)
            if h:
                self._seen_focus.append(h.groups())
            m = self._RE_PART.search(chunk)
            if not m:
                return None, None, ['部件容器没有 translate3d']
            base = tuple(float(m.group(i)) for i in (1, 2, 3))
            # ⚠️ **物化**匹配列表，才能按面片切片取出**它自己的** clip-path。
            # 原来写的是 `self._RE_CLIP.search(chunk)`——搜的是整个部件，
            # 于是永远拿到第一张面片的裁剪、套到所有面片上。段数少、各段裁剪接近时
            # 侥幸不报错；现在每段的梯形内收量能差到 0% vs 50%，再这么写包围盒就是错的。
            _cn = _cg = 0
            _fms = list(self._RE_FACE.finditer(chunk))
            for _fi, fm in enumerate(_fms):
                _nx = _fms[_fi + 1].start() if _fi + 1 < len(_fms) else len(chunk)
                seen += 1
                w, h, mt, ml = (float(fm.group(i)) for i in (1, 2, 3, 4))
                off = tuple(float(fm.group(i) or 0.0) for i in (5, 6, 7))
                rots = [(r.group(1), float(r.group(2)))
                        for r in self._RE_ROT.finditer(fm.group(8) or '')]
                z = float(fm.group(9))
                if abs(ml + w / 2) > 0.02 or abs(mt + h / 2) > 0.02:
                    bad_center += 1
                    continue
                # off 是**世界轴**偏移（写在变换最左侧，在旋转之外），所以直接加在容器
                # 位移上。⚠️ 别复用 base——那会在循环里累加，越往后偏得越离谱。
                bp = tuple(base[i] + off[i] for i in range(3))
                c = _rots_apply(rots, (0.0, 0.0, z))
                ex = _rots_apply(rots, (w / 2, 0.0, 0.0))
                ey = _rots_apply(rots, (0.0, h / 2, 0.0))
                # ⚠️ 有 clip-path（锥面/球面的梯形）时必须按**裁完的四角**算，
                # 不能拿未裁的矩形算——圆锥顶段那个矩形的上边宽出好几倍，
                # 会让「渲染包围盒 == 几何包围盒」这条断言误报，而真实几何是对的。
                # ---- 逐项比对：文本里的每个数都必须等于「几何定义 × k」 ----
                # 包围盒比较抓不到的错用这一条兜底。例：面片的宽/高忘了乘 k，
                # 但该部件的极值恰好由位移（半径、off）主导时，包围盒几乎不变——
                # 负向测试里这个 case 就漏过了。所以直接逐项对。
                # 两个来源是**独立**的（一边读吐出来的文本，一边读几何定义的字段），
                # 所以这不是「把同一份数算两遍」，改坏任何一处都会红。
                if _fi < len(part['faces']):
                    _fc = part['faces'][_fi]
                    _wo = _fc.get('off') or (0.0, 0.0, 0.0)
                    for _nm, _got, _want in (
                            ('width', w, _fc['w'] * k),
                            ('height', h, _fc['h'] * k),
                            ('margin-left', ml, -_fc['w'] * k / 2.0),
                            ('margin-top', mt, -_fc['h'] * k / 2.0),
                            ('translateZ', z, _fc['z'] * k),
                            ('off-x', off[0], _wo[0] * k),
                            ('off-y', off[1], -_wo[1] * k),
                            ('off-z', off[2], _wo[2] * k)):
                        if abs(_got - _want) > 0.06:
                            self._gap.append(
                                f'{self.title}：部件 {i} 第 {_fi} 张面片的 {_nm} '
                                f'渲染成 {_got:g}，按几何定义乘 k 应为 {_want:.2f}'
                                f'——多半是渲染时漏乘（或多乘）了缩放系数 k')
                            break
                    _wrots = [(r.group(1), float(r.group(2)))
                              for r in self._RE_ROT.finditer(fm.group(8) or '')]
                    _drots = [tuple(t) for t in _fc['rots']]
                    # 逐项带容差比：角度在文本里只保留两位小数，直接比 tuple 会把
                    # 146.66666666666669 与 "146.67" 判成不同（第一版就这么误报了一堆）。
                    if (len(_wrots) != len(_drots)
                            or any(a[0] != b[0] or abs(a[1] - b[1]) > 0.02
                                   for a, b in zip(_wrots, _drots))):
                        self._gap.append(
                            f'{self.title}：部件 {i} 第 {_fi} 张面片的旋转序列渲染成 '
                            f'{_wrots}，与定义 {_fc["rots"]} 不一致')

                # ---- 平滑着色必须真的写进 HTML ----
                # noedge（回转体侧面片）靠 linear-gradient 做 Gouraud 插值。
                # 这个机制一旦失效，几何、包围盒、面片数全都还是对的——
                # 只有截图能看出来"圆柱又变回棱柱"。所以在这里把它变成可断言的。
                # 回转体侧面片的描边必须是透明的。硬描边一圈十几条，叠起来就是一层竖线，
                # 会把平滑着色的连续感切碎——而它是纯 CSS 值，最容易被"顺手改回来"。
                if (_fi < len(part['faces']) and part['faces'][_fi].get('noedge')
                        and 'border-color:transparent' not in chunk[fm.end():_nx]):
                    self._gap.append(
                        f'{self.title}：部件 {i} 第 {_fi} 张回转体侧面片的描边不是 transparent'
                        f'——一圈硬描边会把平滑着色切碎，圆柱看着又是棱柱')

                if _fi < len(part['faces']) and part['faces'][_fi].get('noedge'):
                    # 显式 flat 的面片（热盾瓦片这类"本来就该一块块平"的）不算在内
                    if not part['faces'][_fi].get('flat'):
                        self._n_noedge += 1
                        _cn += 1
                        if self._has_grad(chunk[fm.end():_nx]):
                            self._n_grad += 1
                            _cg += 1
                    elif part['faces'][_fi].get('grad') is not None:
                        self._gap.append(
                            f'{self.title}：部件 {i} 第 {_fi} 张面片标了 flat，却还带着渐变')

                # ---- 回转面分段的接缝记录 ----
                # 带 X 倾斜的面片就是「某段回转面」（_cyl_side / taper 的侧面）。
                # 记下它的上下边中点与半径，交给 problems 检查分段有没有接上。
                _tilt = None
                for _ax, _dg in rots:
                    if _ax == 'X':
                        _tilt = _dg
                if _tilt is not None and _fi < len(part['faces']):
                    _ey = _rots_apply(rots, (0.0, h / 2, 0.0))
                    _tm = tuple(bp[j] + c[j] - _ey[j] for j in range(3))
                    _bm = tuple(bp[j] + c[j] + _ey[j] for j in range(3))
                    _rad = lambda q: math.hypot(q[0] - base[0], q[2] - base[2])
                    _cl0 = self._RE_CLIP.search(chunk[fm.end():_nx])
                    _it = _ib = 0.0
                    if _cl0:
                        _it = float(_cl0.group(1))
                        _ib = float(_cl0.group(4))
                    self._seam.append(dict(
                        key=(i, rots[0][0], round(rots[0][1], 3)),
                        top=_tm, bot=_bm, r_top=_rad(_tm), r_bot=_rad(_bm),
                        w_top=w * (1 - 2 * _it / 100.0), w_bot=w * (1 - 2 * _ib / 100.0)))

                cl = self._RE_CLIP.search(chunk[fm.end():_nx])
                if cl:
                    g = [float(cl.group(i)) / 100.0 - 0.5 for i in (1, 2, 3, 4)]
                    ux = (g[0] * 2, g[1] * 2, g[2] * 2, g[3] * 2)
                    corners = ((-ux[0], -1), (-ux[1], -1), (ux[2], 1), (ux[3], 1))
                else:
                    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
                for ux2, uy2 in corners:
                    v = tuple(bp[j] + c[j] + ux2 * ex[j] + uy2 * ey[j] for j in range(3))
                    for j in range(3):
                        lo[j] = min(lo[j], v[j])
                        hi[j] = max(hi[j], v[j])
                        p_lo[j] = min(p_lo[j], v[j])
                        p_hi[j] = max(p_hi[j], v[j])
            self._part_bbox.append((p_lo, p_hi))
            # 逐部件记覆盖率：**只看整模的总覆盖率是不够的**——
            # 某一个图元（比如 _cyl_side）整体丢了渐变时，别的图元还带着，
            # 总比例照样很高，而喷管、穹顶这些部件其实已经变回棱柱了。
            if _cn >= 8 and _cg < _cn * 0.8:
                self._gap.append(
                    f'{self.title}：部件 {i} 的 {_cn} 张回转面片里只有 {_cg} 张带平滑着色的 '
                    f'linear-gradient（应 ≥80%）——这个部件的曲面会退回成棱柱')
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

    def shadow_css(self, k):
        """接地影的尺寸与位置（px，相对台面中心）。

        台面上原本铺的是一块**固定**的椭圆阴影，跟模型没有任何关系——
        高瘦的火箭和扁宽的采矿船用的是同一个椭圆，看着像模型浮在别人的影子上。
        这里改成按**默认视角下几何的真实投影**算：横向取投影宽度，
        纵向压扁（乘 0.13 再夹在 9–26px）。

        纵向压扁是必需的：真阴影是斜上方光线打在**地面**上的投影，
        从斜上方看天然比物体本身窄得多；照投影高度画会像一摊水。
        """
        o = self.origin
        xs, ys = [], []
        for part in self._parts:
            for q in part['pts']:
                sx, sy = _proj(((q[0] - o[0]) * k, -(q[1] - o[1]) * k,
                                (q[2] - o[2]) * k), RX_DEF, RY_DEF)
                xs.append(sx)
                ys.append(sy)
        w = max(xs) - min(xs)
        rx = w * 0.46 + 14.0
        ry = min(26.0, max(9.0, w * 0.13))
        return ((min(xs) + max(xs)) / 2.0, max(ys) + ry * 0.6, rx, ry)

    def _scaled(self):
        k, o = self.k, self.origin
        pts = [((p[0] - o[0]) * k, -(p[1] - o[1]) * k, (p[2] - o[2]) * k)
               for part in self._parts for p in part['pts']]
        pins = [((p['at'][0] - o[0]) * k, -(p['at'][1] - o[1]) * k, (p['at'][2] - o[2]) * k)
                for p in self._pins]
        return pts, pins

    def _seam_problems(self):
        """回转面分段的两个自洽性断言。

        这一版把回转体（cyl/frustum/nozzle/dome/sphere/taper 的侧面）从「竖直平面 + 裁剪」
        改成了**沿轮廓真正倾斜的面片**，才把穹顶那层层缺口消掉。代价是：倾斜角的符号、
        斜边长度、接缝的衔接这几处只要写错一处，包围盒是有可能照样通过的——
        因为包围盒只看极值，而"段与段之间开了条缝"、"整段反过来收口"都不改变极值。

        所以这里单独查两件事，都只认 `_emitted_bbox` 从 HTML 反解出来的数：

        1. **接缝必须接上。** 同一个方位角上，前一段的上边中点要与后一段的下边中点重合
           （3% 的斜边重叠会让它们略微交叠，所以容差按段高给）。这条抓的是
           「面片高度给成竖向高度而不是斜边」这类错——每段会短掉 cos(tilt) 那么多。
        2. **收口方向必须与裁剪一致。** 裁剪把上边裁窄了（w_top < w_bot），
           那上边的半径就必须更小。符号反了，说明这一整段是"倒扣"的：
           该收的地方在放，剖面会变成锯齿。这条抓的是倾斜角符号写反。
        """
        out = []
        groups = {}
        for rec in getattr(self, '_seam', []):
            groups.setdefault(rec['key'], []).append(rec)
        for key, rs in groups.items():
            if len(rs) < 2:
                continue
            # CSS 的 y 向下，所以 y 越大越靠世界低处；按 y 降序排 = 世界自下而上
            rs.sort(key=lambda r: -r['top'][1])
            for a, b in zip(rs, rs[1:]):
                d = math.dist(a['top'], b['bot'])
                hgt = abs(a['bot'][1] - a['top'][1])
                if d > max(1.2, hgt * 0.06):
                    out.append(
                        f'{self.title}：方位 {key[2]:.0f}° 上，第 {rs.index(a)} 段与 '
                        f'第 {rs.index(b)} 段之间有 {d:.1f}px 的缝（段高 {hgt:.1f}px）'
                        f'——回转面断了。多半是面片高度取了竖向高度而不是斜边长度')
                    break
                # 接缝处的**宽度**也要对上：两段在同一个半径上，弦长必须相等。
                # 这条抓的是裁剪基准写错（比如把 max(r0,r1) 写成 r0）——
                # 那样上边的中点还在原地（裁剪是对称收的），缝检查看不出来，
                # 但上边的宽度会错一大截，段与段之间露出明显的台阶。
                wa, wb = a['w_top'], b['w_bot']
                if abs(wa - wb) > 0.06 * max(wa, wb, 1e-6):
                    out.append(
                        f'{self.title}：方位 {key[2]:.0f}° 上，第 {rs.index(a)} 段的上边宽 '
                        f'{wa:.1f} 与第 {rs.index(b)} 段的下边宽 {wb:.1f} 对不上'
                        f'（同一半径处弦长应相等）——多半是裁剪的基准半径取错了')
                    break
        for rec in getattr(self, '_seam', []):
            dw = rec['w_top'] - rec['w_bot']
            dr = rec['r_top'] - rec['r_bot']
            if abs(dw) < 0.02 * max(rec['w_top'], rec['w_bot']):
                continue                      # 圆柱段：本来就没有收口
            if dw * dr < 0:
                out.append(
                    f'{self.title}：有段回转面是"倒扣"的——裁剪把上边收窄了 '
                    f'{rec["w_bot"]:.1f}→{rec["w_top"]:.1f}，但上边的半径却从 '
                    f'{rec["r_bot"]:.1f} 变成了 {rec["r_top"]:.1f}（该收的地方在放）。'
                    f'多半是倾斜角的符号写反了（CSS 的 y 向下，要 atan2(−Δr, Δy)）')
        return out

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

        # ---- 锚点必须在几何中心 ----
        # 这不是审美问题：聚焦（点一下放大）是把部件容器的 translate3d(锚点) 丢掉、
        # 换成 scale3d(f)，也就是「几何按锚点缩放到世界原点，再把世界平移 -c」。
        # 锚点一旦偏离几何中心，部件放大后就会整体偏出去，甚至出取景框。
        # 图元自己算错锚点是很容易的（dome / sphere 第一版都错），所以逐件断言。
        for _i, _p in enumerate(self._parts):
            _xs = [q[0] for q in _p['pts']]
            _ys = [q[1] for q in _p['pts']]
            _zs = [q[2] for q in _p['pts']]
            _ctr = ((min(_xs) + max(_xs)) / 2.0, (min(_ys) + max(_ys)) / 2.0,
                    (min(_zs) + max(_zs)) / 2.0)
            _gap = max(abs(_p['anchor'][k2] - _ctr[k2]) for k2 in range(3))
            if _gap > 0.4:
                out.append(
                    f'{self.title}：部件 {_i} 的锚点 {tuple(round(v, 2) for v in _p["anchor"])} '
                    f'偏离几何中心 {tuple(round(v, 2) for v in _ctr)} 达 {_gap:.2f}'
                    f'——聚焦是绕锚点缩放平移的，锚点不在中心，放大后一定会偏出取景框')
        if out:
            return out

        self.k = self._fit()
        pts, pins = self._scaled()
        worst = (999.0, '', '')

        # 端到端：渲染参数还原出来的包围盒，必须和自适配用的几何包围盒对得上。
        # 容差给了 5% + 1.5px——圆柱是用内接多边形近似的，本来就会略小于真圆。
        elo, ehi, eerr = self._emitted_bbox(self.k)
        _gap = self._gap
        out += eerr
        if elo is None:
            return out
        # **逐部件**比对（不是只比整模）。
        #
        # ⚠️ 只比整模是不够的：十来个零件里有一个写错，它往往还落在别的零件撑开的
        # 范围内，整模包围盒一动都不动。本轮把零件数翻了几倍之后，这类「被掩盖的错」
        # 就成了主要风险，所以改成一件一件比。
        #
        # 两个方向分开定容差：
        #   · **渲染超出几何**（外侧）严格——那是真错，面片跑到自适配没算到的地方去了。
        #   · **几何超出渲染**（内侧）放宽——回转体是用内接多边形近似的，几何的极值点
        #     与面片角点本来就不在同一个角度上（14 边形最接近 90° 的是 77°，半径要打
        #     0.975 折）；弦长还乘了 1.10 的重叠系数，角点会再鼓出 4%。
        #   两侧都要有界：只查外侧的话，「忘了乘 k」导致面片全塌到中心附近这种错就漏了。
        for pi, (plo, phi) in enumerate(getattr(self, '_part_bbox', [])):
            xs = [q[0] for q in self._parts[pi]['pts']]
            ys = [q[1] for q in self._parts[pi]['pts']]
            zs = [q[2] for q in self._parts[pi]['pts']]
            _o = self.origin
            gil = ((min(xs) - _o[0]) * self.k, -(max(ys) - _o[1]) * self.k,
                   (min(zs) - _o[2]) * self.k)
            gih = ((max(xs) - _o[0]) * self.k, -(min(ys) - _o[1]) * self.k,
                   (max(zs) - _o[2]) * self.k)
            for j, axis in enumerate('xyz'):
                span = gih[j] - gil[j]
                tol_out = span * 0.06 + 1.5
                tol_in = span * 0.10 + 4.0
                if plo[j] < gil[j] - tol_out or phi[j] > gih[j] + tol_out:
                    out.append(
                        f'{self.title}：部件 {pi} 在 {axis} 轴的渲染包围盒 '
                        f'[{plo[j]:.1f}, {phi[j]:.1f}] 超出了它的几何范围 '
                        f'[{gil[j]:.1f}, {gih[j]:.1f}]（容差 {tol_out:.1f}px）'
                        f'——多半是某处忘了乘缩放系数 k，或偏移/锚点的语义搞错了')
                elif plo[j] > gil[j] + tol_in or phi[j] < gih[j] - tol_in:
                    out.append(
                        f'{self.title}：部件 {pi} 在 {axis} 轴的渲染包围盒 '
                        f'[{plo[j]:.1f}, {phi[j]:.1f}] 比它的几何范围 '
                        f'[{gil[j]:.1f}, {gih[j]:.1f}] 小了一大截（容差 {tol_in:.1f}px）'
                        f'——面片没铺满，多半是长宽、偏移或旋转写错')
        for i, axis in enumerate('xyz'):
            ilo = min(p[i] for p in pts)
            ihi = max(p[i] for p in pts)
            tol_out = (ihi - ilo) * 0.05 + 1.5
            if elo[i] < ilo - tol_out or ehi[i] > ihi + tol_out:
                out.append(f'{self.title}：整模 {axis} 轴的渲染包围盒 '
                           f'[{elo[i]:.1f}, {ehi[i]:.1f}] 超出几何包围盒 '
                           f'[{ilo:.1f}, {ihi:.1f}]（容差 {tol_out:.1f}px）')
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
        out += _gap[:6]
        if len(_gap) > 6:
            out.append(f'{self.title}：另有 {len(_gap) - 6} 处渲染参数与几何定义不一致'
                       f'（同类问题，未逐条列出）')
        # 平滑着色（Gouraud）的覆盖率。这一条**必须按比例判**，不能按单张判：
        # 弧面片允许显式 flat（热盾瓦片就是要一块块平的），所以"没有渐变"本身
        # 不一定是错。但如果整个机制被删掉，覆盖率会一起掉到底——那才是要拦的。
        # ⚠️ 第一版写成了「该面片有 grad 却没渐变才报错」，于是 grad 被改成 None 时
        # 断言自己跳过了，负向测试里照样全绿——等于没写。
        if self._n_noedge >= 8 and self._n_grad < self._n_noedge * 0.8:
            out.append(
                f'{self.title}：回转面片只有 {self._n_grad}/{self._n_noedge} 张带平滑着色的 '
                f'linear-gradient（应 ≥80%）——平滑着色机制失效了，圆柱会退回成棱柱')

        out += self._seam_problems()
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
            # noedge：回转体的侧面片不要硬棱线。一周十几个面片，每条边都算一条竖线，
            # 叠起来就是一层网格，会把横向的环焊缝彻底盖掉。改成几乎同色的描边——
            # 只起「防止相邻面片之间漏出背景」的作用，看不出是条线。
            # noedge（回转体侧面片）的描边直接给**透明**。以前给的是「几乎同色的描边」，
            # 但一圈十几条边叠起来仍然是一层竖线，会把平滑着色的连续感切碎——
            # 而描边原本要解决的「相邻面片之间漏出背景」，靠 10% 的弦长重叠早就解决了。
            # 描边区域本身也会被 background 铺到（background-clip 默认是 border-box），
            # 所以透明描边不会留缝。
            bd = ('transparent' if fc.get('noedge')
                  else _alpha(shade(fc['col'], EDGE), min(1.0, op * 1.6) if op else 1))
            # ⚠️ 结尾的分号不能少。少了它，整条内联样式会变成
            # `border-radius:50%transform:rotateX(...)`——border-radius 吃掉了整个
            # 非法值，**后面的 transform 声明整条丢失**，端盖就变成贴在部件原点的方块。
            # 这个错是「反解 HTML 数面片」那条断言抓出来的（几何 52 张、只反解到 48 张）。
            r = 'border-radius:50%;' if part.get('cap') and fc['nm'] in ('cap', 'cb') else ''
            # ⚠️ `width;height;margin;[border-radius;]transform` 这一串必须**连续且同序**：
            # _RE_FACE 就是按这个顺序反解的。纹理与裁剪要加在后面，不能插进中间。
            css = (f'width:{_f(w)}px;height:{_f(h)}px;'
                   f'margin:{_f(-h / 2)}px 0 0 {_f(-w / 2)}px;{r}'
                   f'transform:{_tf(fc, k)};background-color:{bg};border-color:{bd}')
            # 纹理周期：先把世界周期换成像素，再**对齐到面片自身的宽高**。
            # 为什么必须对齐：每张面片的渐变都是从它自己的左上角起铺的，如果周期
            # 除不尽面片高度，相邻面片就会错开半个周期——一整圈看过去是「砖墙」
            # 而不是一圈环焊缝（第一版就是这样）。对齐之后，同一圈里所有面片
            # 尺寸相同、图案也完全相同，接缝处自然连成一条线。
            _tp = (fc.get('tp') or 8.0) * k
            _pv = _ph = _tp
            if fc.get('noedge'):
                _nv = max(2.0, round(h / _tp)) if h > 1 else 1.0
                _nh = max(2.0, round(w / _tp)) if w > 1 else 1.0
                _pv = h / _nv if h > 1 else _tp
                _ph = w / _nh if w > 1 else _tp
            tex_img, tex_size = _tex_css(fc.get('tex'), _pv, _ph)
            # background-image 是**多层**的，先列的在上面：纹理压住渐变（纹理是
            # 「涂在表面上的东西」，渐变是「表面自身的受光」），所以纹理在前。
            # ⚠️ 层数 >1 时 background-size 必须**逐层给全**。只给一个值会被复制到
            # 所有层，于是渐变层也会按纹理周期平铺——筒身会突然变成一格格色块。
            _layers, _sizes = [], []
            if tex_img:
                _layers.append(tex_img)
                _sizes.append(tex_size or 'auto')
            if fc.get('grad'):
                _layers.append(fc['grad'][1])
                _sizes.append('100% 100%')
            if _layers:
                css += ';background-image:' + ','.join(_layers)
                css += ';background-size:' + ','.join(_sizes)
            if fc.get('clip'):
                css += f';clip-path:{fc["clip"]}'
            out.append(f'<span class="m3d-f" style="{css}"></span>')
        out.append('</span>')
        return ''.join(out)

    def _shadow_html(self, k):
        """接地影那一层。

        单独做一层（而不是画在台面背景上）的理由：它要跟着 `--m3d-k` 一起缩。
        窄屏时台面变矮、模型按比例缩小，影子不缩就会拖出一大截。
        和 `.m3d-pins` 同一个套路：子元素用「50% + 设计像素」定位，外层整体 scale，
        于是只有像素部分被乘 k，中心对齐不受影响。
        """
        sx, sy, rx, ry = self.shadow_css(k)
        return (f'<div class="m3d-shadow"><i style="'
                f'left:calc(50% + {_f(sx)}px);top:calc(50% + {_f(sy)}px);'
                f'width:{_f(rx * 2)}px;height:{_f(ry * 2)}px;'
                f'margin:{_f(-ry)}px 0 0 {_f(-rx)}px"></i></div>')

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
            f'    {self._shadow_html(k)}\n'
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
