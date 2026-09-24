# -*- coding: utf-8 -*-
"""深色「舷窗」背景：星场 + 坐标网格 + 轨道弧 + 星云 + 星舰剪影。

**每个板块一张**：色相取自 tools/boardskin.py 的板块色族，星位种子由 slug 派生，
所以十个板块的舷窗各不相同（星云颜色、星位、轨道位置都不同），但都是同一套画法。


设计意图：站点正文保持浅色（可读性、打印），只把**关键面**做成深色舷窗——
首屏、板块卡片里收口的那张、以及若干仪表条。星场就是这些深色面的底。

两条硬约束：

1. **必须确定性。** 用固定种子的 LCG，不用 random。星位每次构建都要完全一样，
   否则「构建产物可复现、按字节比对校验」这条流水线会失效。
2. **输出成独立 SVG 文件，不要内联。** 用 CSS 的 background-image 引用
   （路径相对 site.css 解析，所以首页写 `url(space.svg)`、板块页也解析到同一个文件）。
   内联的话 11 个页面各背一份十几 KB 的星场，白涨 150KB。
"""

import os
import zlib

# 深色面的调色。SIGNAL 现在只是「默认板块色」，真正的色相由调用方按板块传入。
VOID = '#2b3a4b'
SIGNAL = '#63d8e4'
AMBER = '#f2bd63'
STAR = '#f0f6fc'

# 画布。给足尺寸后由 CSS 的 background-size:cover 去裁，圆形不会被拉成椭圆。
W, H = 1600, 560


class Rng:
    """固定种子的线性同余发生器——只为「每次构建结果一致」，不做密码学用途。"""

    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def f(self, a=0.0, b=1.0):
        return a + (b - a) * (self.next() / 0x7FFFFFFF)


def _f(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def _grid(ink=SIGNAL):
    """坐标网格。刻意两条不同密度，读起来像工程图而不是稿纸。"""
    out = []
    for x in range(0, W + 1, 80):
        out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>')
    for y in range(0, H + 1, 80):
        out.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    fine = ''.join(out)
    coarse = []
    for x in range(0, W + 1, 400):
        coarse.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>')
    for y in range(0, H + 1, 400):
        coarse.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    return (
        f'<g stroke="{ink}" stroke-width="1" opacity=".05">{fine}</g>'
        f'<g stroke="{ink}" stroke-width="1" opacity=".09">{"".join(coarse)}</g>'
    )


def _stars(rng, n=230, safe=None):
    """星场。safe 是「文字安全区」(x0,y0,x1,y1)。

    ⚠️ 安全区里要做两件事，只做一件不够（实测过）：
    ① 星点压暗到 0.18 以下；
    ② **不画十字光芒**——光芒是白色、可以亮到 0.95，一个 16×16 的小块里只要落一颗，
       这块底色的对比度就从 5.4:1 掉到 3.9:1。压暗星点但不砍光芒，数字几乎不动。
    """
    out = []
    bright = []
    for _ in range(n):
        x, y = rng.f(0, W), rng.f(0, H)
        r = rng.f(0.5, 1.5)
        op = rng.f(0.30, 0.88)
        in_safe = bool(safe) and safe[0] < x < safe[2] and safe[1] < y < safe[3]
        if in_safe:
            out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" '
                       f'fill="{STAR}" opacity="{_f(min(op, 0.18))}"/>')
            continue
        if r > 1.32:
            bright.append((x, y, r, min(op + 0.15, 0.95)))
        else:
            out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" '
                       f'fill="{STAR}" opacity="{_f(op)}"/>')
    # 亮星加十字光芒，星场的层次就出来了
    flare = []
    for x, y, r, op in bright:
        a = r * 5.2
        flare.append(
            f'<g opacity="{_f(op * 0.55)}" stroke="{STAR}" stroke-width=".7">'
            f'<line x1="{_f(x - a)}" y1="{_f(y)}" x2="{_f(x + a)}" y2="{_f(y)}"/>'
            f'<line x1="{_f(x)}" y1="{_f(y - a)}" x2="{_f(x)}" y2="{_f(y + a)}"/></g>'
            f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="#ffffff" opacity="{_f(op)}"/>')
    return ''.join(out) + ''.join(flare)


def _orbits(ink=SIGNAL, dx=0, dy=0):
    """几条轨道弧，压得很淡——只用来暗示「这里有个天体系统」。
    dx/dy 让十个板块的弧心错开，避免十张图长得一样。"""
    out = []
    for cx, cy, rx, ry, rot, op in (
            (1180 + dx, 150 + dy, 300, 96, -22, .16),
            (1180 + dx, 150 + dy, 420, 150, -22, .10),
            (300 + dx, 470 + dy, 340, 110, 16, .09)):
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" '
                   f'fill="none" stroke="{ink}" stroke-width="1" stroke-dasharray="7 9" opacity="{op}"/>')
    return ''.join(out)


def _vessel(scale=1.0, glow=SIGNAL, tx=1188, ty=104, rot=-24):
    """一艘极简星舰剪影：细长船体 + 两片尾翼 + 尾焰。朝右上方。"""
    hull = ('M0,0 L46,-3.2 Q55,-3.2 58,0 Q55,3.2 46,3.2 Z')
    fin_t = 'M34,-2.6 L44,-11 L49,-2.4 Z'
    fin_b = 'M34,2.6 L44,11 L49,2.4 Z'
    return (
        f'<g transform="translate({tx},{ty}) rotate({rot}) scale({_f(scale)})">'
        f'<path d="{hull}" fill="{STAR}" opacity=".92"/>'
        f'<path d="{fin_t}" fill="{glow}" opacity=".85"/>'
        f'<path d="{fin_b}" fill="{glow}" opacity=".85"/>'
        f'<circle cx="4" cy="0" r="3.4" fill="{AMBER}" opacity=".9"/>'
        # 尾焰：两条递减的短线，够表达「在推进」就停，别做成一团火
        f'<line x1="-6" y1="0" x2="-30" y2="0" stroke="{AMBER}" stroke-width="1.6" opacity=".5"/>'
        f'<line x1="-6" y1="0" x2="-20" y2="0" stroke="#fff7e6" stroke-width=".9" opacity=".7"/>'
        f'</g>'
    )


def _trajectory(ink=SIGNAL, dy=0):
    return (f'<path d="M96,{508 + dy} C420,{470 + dy} 700,{330 + dy} 1148,{124 + dy}" fill="none" '
            f'stroke="{ink}" stroke-width="1.2" stroke-dasharray="3 7" opacity=".38"/>')


def _nebula(uid, glow, dx=0, dy=0, scale=1.0):
    """星云辉光：只用径向渐变，不用 feGaussianBlur（滤镜在大尺寸背景上很贵）。

    ⚠️ **光只留在右半。** 首屏的文字（眉标/标题/导语/遥测标签）占左侧约 60%，
    星云如果铺到左边，文字就压在亮底上——实测过：光铺满全图时，
    暗底本身有 10.4:1，但 99.9% 分位（星云核心）只有 3.4:1，标题区直接不达标。
    现在的两个光斑都在右半：主光斑在右上，副光斑在右下，左侧保持纯暗底。
    """
    def blob(cx, cy, r, op):
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.62}" fill="url(#{uid})" '
                f'opacity="{_f(op)}"/>')
    return (
        f'<defs><radialGradient id="{uid}">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity=".50"/>'
        f'<stop offset="52%" stop-color="{glow}" stop-opacity=".14"/>'
        f'<stop offset="100%" stop-color="{glow}" stop-opacity="0"/>'
        f'</radialGradient></defs>'
        + blob(1290 + dx, 110 + dy, 430 * scale, .50)
        + blob(1120 + dx * 0.6, 500 + dy * 0.6, 300 * scale, .26)
    )


def _seed_of(slug, base=20260915):
    """由 slug 派生种子。**不能用内置 hash()**——它每个进程都会变（PYTHONHASHSEED），
    星位就不确定了，「构建可复现 + 按字节校验」这条流水线会失效。"""
    return (base + zlib.crc32(slug.encode()) % 9973) & 0x7FFFFFFF


def space_svg(stars=230, seed=20260915, safe=(0, 0, 1080, H), vessel=True,
              glow=SIGNAL, slug='hub'):
    """舷窗背景。默认尺寸 1600×560，供 CSS 以 cover 方式铺满深色面板。

    glow 是板块的亮色档；slug 用来派生「星位 + 星云位置 + 轨道偏移」，让十个板块各不同。
    """
    rng = Rng(seed)
    j = _seed_of(slug) % 60 - 30          # 每板块 ±30px 的错位
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">']
    parts.append(_nebula(f'neb-{slug}', glow, dx=j, dy=-j // 2))
    parts.append(_grid(glow))
    parts.append(_orbits(glow, dx=j))
    parts.append(_stars(rng, stars, safe))
    if vessel:
        parts.append(_trajectory(glow, dy=j // 2))
        parts.append(_vessel(glow=glow, ty=104 + j // 3, rot=-24 + (j % 9)))
    parts.append('</svg>')
    return ''.join(parts)


def tile_svg(stars=150, seed=777001, glow=SIGNAL, slug='hub'):
    """小尺寸星场瓦片，给 KPI 仪表条这类小面积深色面用（无网格、无星舰）。"""
    rng = Rng(seed + _seed_of(slug) % 977)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" '
            f'viewBox="0 0 900 420">'
            f'{_nebula(f"nebt-{slug}", glow, dx=0, dy=0, scale=.6)}'
            f'{_stars(rng, stars, safe=(0, 0, 900, 420))}</svg>')


def write_assets(out_dir, skins=None):
    """把背景图写到 assets/：首页两张 + 每个板块两张。由 build.py 每次构建时调用。"""
    os.makedirs(out_dir, exist_ok=True)
    made = []

    def emit(name, svg):
        p = os.path.join(out_dir, name)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(svg)
        made.append((p, len(svg.encode())))

    emit('space.svg', space_svg())
    emit('space-tile.svg', tile_svg())
    for slug, sk in (skins or {}).items():
        emit(f'space-{slug}.svg', space_svg(glow=sk['glow'], slug=slug))
        emit(f'space-tile-{slug}.svg', tile_svg(glow=sk['glow'], slug=slug))
    return made


if __name__ == '__main__':
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from boardskin import SKINS
    for p, n in write_assets(os.path.join(os.path.dirname(here), 'assets'), SKINS):
        print(f'  {os.path.basename(p):<26} {n:>7,} B')
