# -*- coding: utf-8 -*-
"""深色「舷窗」背景：星场 + 坐标网格 + 轨道弧 + 星舰剪影。

设计意图：站点正文保持浅色（可读性、打印），只把**关键面**做成深色舷窗——
首屏、板块卡片里收口的那张、以及若干仪表条。星场就是这些深色面的底。

两条硬约束：

1. **必须确定性。** 用固定种子的 LCG，不用 random。星位每次构建都要完全一样，
   否则「构建产物可复现、按字节比对校验」这条流水线会失效。
2. **输出成独立 SVG 文件，不要内联。** 用 CSS 的 background-image 引用
   （路径相对 site.css 解析，所以首页写 `url(space.svg)`、板块页也解析到同一个文件）。
   内联的话 11 个页面各背一份十几 KB 的星场，白涨 150KB。
"""

import math
import os

# 深色面的调色（与 site.css 里的 --void* / --signal* 保持一致）
VOID = '#0a0e14'
SIGNAL = '#4ad9e4'
SIGNAL_DIM = '#2f8f9c'
AMBER = '#f0b03c'
STAR = '#dce6f2'

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


def _grid():
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
        f'<g stroke="{SIGNAL}" stroke-width="1" opacity=".05">{fine}</g>'
        f'<g stroke="{SIGNAL}" stroke-width="1" opacity=".09">{"".join(coarse)}</g>'
    )


def _stars(rng, n=230, safe=None):
    """星场。safe 是「文字安全区」(x0,y0,x1,y1)，落在里面的星压暗，保证标题可读。"""
    out = []
    bright = []
    for _ in range(n):
        x, y = rng.f(0, W), rng.f(0, H)
        r = rng.f(0.5, 1.5)
        op = rng.f(0.22, 0.82)
        if safe and safe[0] < x < safe[2] and safe[1] < y < safe[3]:
            op = min(op, 0.26)
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


def _orbits():
    """几条轨道弧，压得很淡——只用来暗示「这里有个天体系统」。"""
    out = []
    for cx, cy, rx, ry, rot, op in (
            (1180, 150, 300, 96, -22, .16),
            (1180, 150, 420, 150, -22, .10),
            (300, 470, 340, 110, 16, .09)):
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" '
                   f'fill="none" stroke="{SIGNAL}" stroke-width="1" stroke-dasharray="7 9" opacity="{op}"/>')
    return ''.join(out)


def _vessel(scale=1.0):
    """一艘极简星舰剪影：细长船体 + 两片尾翼 + 尾焰。朝右上方。"""
    hull = ('M0,0 L46,-3.2 Q55,-3.2 58,0 Q55,3.2 46,3.2 Z')
    fin_t = 'M34,-2.6 L44,-11 L49,-2.4 Z'
    fin_b = 'M34,2.6 L44,11 L49,2.4 Z'
    return (
        f'<g transform="translate(1188,104) rotate(-24) scale({_f(scale)})">'
        f'<path d="{hull}" fill="{STAR}" opacity=".92"/>'
        f'<path d="{fin_t}" fill="{SIGNAL}" opacity=".85"/>'
        f'<path d="{fin_b}" fill="{SIGNAL}" opacity=".85"/>'
        f'<circle cx="4" cy="0" r="3.4" fill="{AMBER}" opacity=".9"/>'
        # 尾焰：两条递减的短线，够表达「在推进」就停，别做成一团火
        f'<line x1="-6" y1="0" x2="-30" y2="0" stroke="{AMBER}" stroke-width="1.6" opacity=".5"/>'
        f'<line x1="-6" y1="0" x2="-20" y2="0" stroke="#fff7e6" stroke-width=".9" opacity=".7"/>'
        f'</g>'
    )


def _trajectory():
    return (f'<path d="M96,508 C420,470 700,330 1148,124" fill="none" '
            f'stroke="{SIGNAL}" stroke-width="1.2" stroke-dasharray="3 7" opacity=".38"/>')


def space_svg(stars=230, seed=20260915, safe=(60, 90, 900, 470), vessel=True):
    """舷窗背景。默认尺寸 1600×560，供 CSS 以 cover 方式铺满深色面板。"""
    rng = Rng(seed)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">']
    parts.append(_grid())
    parts.append(_orbits())
    parts.append(_stars(rng, stars, safe))
    if vessel:
        parts.append(_trajectory())
        parts.append(_vessel())
    parts.append('</svg>')
    return ''.join(parts)


def tile_svg(stars=150, seed=777001):
    """小尺寸星场瓦片，给板块卡片等小面积深色面用（无网格、无星舰）。"""
    rng = Rng(seed)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" '
            f'viewBox="0 0 900 420">{_stars(rng, stars, safe=(0, 0, 900, 210))}</svg>')


def write_assets(out_dir):
    """把两张背景图写到 assets/。由 build.py 每次构建时调用，保证与代码同步。"""
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name, svg in (('space.svg', space_svg()), ('space-tile.svg', tile_svg())):
        p = os.path.join(out_dir, name)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(svg)
        made.append((p, len(svg.encode())))
    return made


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    for p, n in write_assets(os.path.join(os.path.dirname(here), 'assets')):
        print(f'  {os.path.basename(p):<18} {n:>7,} B')
