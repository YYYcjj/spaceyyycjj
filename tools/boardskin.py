# -*- coding: utf-8 -*-
"""十个板块各自的色族：**「这是哪个板块」的第三个性别维度**。

站点原本只有两套颜色语义，加板块色时必须先认清它们，否则三套会打架：

| 维度 | 回答的问题 | 值 |
|---|---|---|
| 状态色 | 这件事到哪一步了 | `--green/--blue/--amber/--red/--gray`（已实现 / 在验证 / 待突破 / 物理约束 / 仅纸上）|
| 位置色 | 这是第几层 | `--ly1..--ly5`（栏目序号） |
| **板块色** | 这是哪个板块 | `--bd-*`（本模块产出） |

三条纪律：

1. **板块色不参与状态表达。** 板块色只出现在「环境」上：页面底色的一抹渐变、
   深色舷窗的星云与暗角、眉标、进度条、栏目色阶。**绝不进小标签**——
   一枚绿色小标签必须永远是「已实现」的意思，不能因为换了板块就变味。
2. **同一个板块的五档栏目色仍是一族。** 板块色换了，`--ly1..5` 跟着换色相，
   但「同族、明度接近、靠序号区分」这条不变量保持。
3. **收口页刻意低饱和。** 板块十是综合页，不描述某个领域，所以它的色相最灰。

对比度全部在构建期用 WCAG 公式断言（在本模块底部），不靠眼睛看——
十个板块 × 四档色 × 两种底色，靠人眼核不过来。

色相是按主题挑的，不是等距分的：火箭技术是焰橙（发动机热）、生态圈是苔绿（生保与植物）、
外星交流是罗兰紫（射电与远方）、宇宙资源是赭金（金属矿）。
"""

import colorsys

# 浅色面与深色面的基准底（与 site.css 保持一致），对比度就按它们算
PAGE = '#edf1f5'      # --page
WHITE = '#ffffff'     # --bg
VOID = '#2b3a4b'      # --void（深色舷窗底）
VOID_TEXT = '#eef3f8'  # --void-text


# ---------------------------------------------------------------- 颜色工具

def hsl(h, s, l):
    """HSL(0-360, 0-1, 0-1) → #rrggbb"""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255))


def _srgb(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _lum(hexcolor):
    h = hexcolor.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def contrast(a, b):
    """WCAG 对比度。"""
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def lum_for_contrast(bg, want, lighter=False):
    """要在一个底色上达到 want 的对比度，前景该有多少亮度。

    ⚠️ 分方向：前景比底**深**时是 (L底+0.05)/want-0.05，比底**亮**时是
    want×(L底+0.05)-0.05。两者只写对一支是常见错——深色面上的亮色（眉标、进度条）
    要的正是「更亮」那一支，用错方向会算出负亮度。
    """
    base = lum_of(bg) + 0.05
    v = want * base - 0.05 if lighter else base / want - 0.05
    return min(max(v, 0.0), 1.0)


def lum_of(hexcolor):
    return _lum(hexcolor)


def at_lum(hue, sat, target):
    """求「色相/饱和度固定、亮度等于 target」的那个 HSL 明度。

    ⚠️ 这一步不能省。HSL 的明度不是感知亮度：色相变了，同样明度下的亮度差很多
    （亮度公式里绿占 0.715、蓝只占 0.07）。第一版我直接写死明度 0.315，
    苔绿的对比度只有 4.55:1，蓝色却到 6:1。按亮度反解才让十个板块站在同一条线上。
    """
    lo, hi = 0.0, 1.0
    for _ in range(48):
        mid = (lo + hi) / 2
        if _lum(hsl(hue, sat, mid)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------- 十个板块的色相
# (slug, 短名, 色相, 基础饱和度, 为什么是这个颜色)
HUES = [
    ('current',     '目前航天', 208, 0.30, '钢铁蓝：行业基线，也是全站的默认色'),
    ('rocket-tech', '火箭技术',  14, 0.46, '焰橙：发动机热流与试车台'),
    ('starship',    '星舰',     192, 0.30, '不锈钢青灰：舰体的冷金属'),
    ('biosphere',   '生态圈',   146, 0.34, '苔绿：生保系统与植物'),
    ('lightspeed',  '光速推进', 228, 0.42, '深天蓝：光束与深空'),
    ('lifespan',    '寿命冬眠', 258, 0.34, '靛紫：低温与沉睡'),
    ('contact',     '外星交流', 284, 0.36, '罗兰紫：射电与远方'),
    ('resources',   '宇宙资源',  34, 0.44, '赭金：小行星金属矿'),
    ('ai-robots',   'AI 机器人', 170, 0.34, '青碧：传感与算力'),
    ('integration', '星船总体', 216, 0.16, '石墨蓝灰：综合页刻意最灰，不描述某个领域'),
]


def _skin(slug, name, hue, sat, note):
    """一个板块的全套颜色。四档 + 五级栏目色阶。

    每一档都**按目标亮度反解明度**，所以十个板块的同一档在感知上是同一个深浅，
    只有色相不同——这是「十个板块各不相同但像一套东西」的关键。
    """
    page_lum = lum_of(PAGE)
    void_lum = lum_of(VOID)

    # ① ink：浅色面上的文字/描边色（层序号块、栏目名）。对 --page 要到 5.6:1。
    ink = hsl(hue, min(sat + 0.06, 0.62), at_lum(hue, min(sat + 0.06, 0.62),
                                                  lum_for_contrast(PAGE, 5.6)))
    # ② deep：深色舷窗的地色。亮度对齐 --void，只换色相，所以深底上的文字对比度不变。
    deep = hsl(hue, min(sat + 0.10, 0.52), at_lum(hue, min(sat + 0.10, 0.52), void_lum))
    # ③ wash：页面顶部那一抹渐变。比页面底稍深一点点，饱和度压低，只到「能看出偏色」。
    wash_sat = min(sat * 0.85, 0.34)
    wash = hsl(hue, wash_sat, at_lum(hue, wash_sat, page_lum - 0.055))
    # ④ glow：深色面上的亮色（眉标、进度条）。对深底要到 6.2:1。
    glow_sat = min(sat + 0.30, 0.70)
    glow = hsl(hue, glow_sat, at_lum(hue, glow_sat, lum_for_contrast(deep, 6.2, lighter=True)))
    # ⑤ 栏目色阶：同族五档，色相轻微右移、亮度逐档微升 → 靠序号区分而不是靠色相
    ly = []
    base = lum_for_contrast(PAGE, 5.4)
    for i in range(5):
        ly.append(hsl(hue + i * 3.0, min(sat + 0.20, 0.60), at_lum(hue + i * 3.0,
                    min(sat + 0.20, 0.60), base * (1 + i * 0.045))))
    return dict(slug=slug, name=name, hue=hue, sat=sat, note=note,
                ink=ink, deep=deep, wash=wash, glow=glow, ly=ly)


SKINS = {s[0]: _skin(*s) for s in HUES}

# 首页（不属于任何板块）用站点默认的一套：与 --ly* 的默认值一致
DEFAULT = _skin('hub', '总览', 208, 0.30, '站点默认（首页不属于任何板块）')
DEFAULT['deep'] = VOID          # 首页沿用原来的 --void，与 CSS 里的默认值一致
DEFAULT['glow'] = '#63d8e4'     # 与 --signal 一致


def css_vars(skin, prefix=''):
    """产出一段 :root 变量。prefix 是相对本篇文档的 assets 路径前缀
    （板块页 '../assets/'、首页 'assets/'）——内联 <style> 里的 url() 相对文档解析，
    而 site.css 里的相对路径是相对样式表，两者不能混。"""
    out = [f"  --bd-ink:{skin['ink']};",
           f"  --bd-deep:{skin['deep']};",
           f"  --bd-wash:{skin['wash']};",
           f"  --bd-glow:{skin['glow']};"]
    for i, c in enumerate(skin['ly'], 1):
        out.append(f'  --ly{i}:{c};')
    if prefix is not None:
        # 首页不属于任何板块，用主图 space.svg / space-tile.svg；
        # ⚠️ url() 写在 CSS 自定义属性里，解析基准是**样式表**（assets/site.css）而不是文档，
        # 所以这里传空前缀、只给文件名——传 'assets/' 会变成 assets/assets/…（404 过一次）。
        mid = '' if skin['slug'] == 'hub' else '-' + skin['slug']
        out.append(f'  --sky:url(space{mid}.svg);')
        out.append(f'  --tile:url(space-tile{mid}.svg);')
    return ':root{\n' + '\n'.join(out) + '\n}'


# ---------------------------------------------------------------- 构建期断言
def check():
    """对比度不达标就别构建。返回一份自检报告（供打印）。"""
    rows = []
    for slug, s in SKINS.items():
        # 小字（11px 的层序号块 / 8–10px 的标签）在浅底上要 ≥ 4.5
        c_ink_page = contrast(s['ink'], PAGE)
        c_ink_white = contrast(s['ink'], WHITE)
        c_ly_page = min(contrast(c, PAGE) for c in s['ly'])
        c_ly_sunk = min(contrast(c, '#f0f5fa') for c in s['ly'])   # --bg-sunk
        # 深色面上的文字
        c_glow_void = contrast(s['glow'], s['deep'])
        c_voidtext_deep = contrast(VOID_TEXT, s['deep'])
        assert c_ink_page >= 5.3, f'{slug} ink 在 --page 上只有 {c_ink_page:.2f}:1'
        assert c_ink_white >= 5.5, f'{slug} ink 在 --bg 上只有 {c_ink_white:.2f}:1'
        assert c_ly_page >= 4.6, f'{slug} 栏目色阶在 --page 上最低 {c_ly_page:.2f}:1'
        assert c_ly_sunk >= 4.6, f'{slug} 栏目色阶在 --bg-sunk 上最低 {c_ly_sunk:.2f}:1'
        assert c_glow_void >= 6.0, f'{slug} glow 在深底上只有 {c_glow_void:.2f}:1'
        assert c_voidtext_deep >= 8.0, f'{slug} 深底与正文色只有 {c_voidtext_deep:.2f}:1'
        rows.append((slug, s['name'], c_ink_page, c_ly_page, c_glow_void, c_voidtext_deep))
    return rows


if __name__ == '__main__':
    for slug, name, a, b, c, d in check():
        s = SKINS[slug]
        print(f"  {slug:<12} {name:<6} ink {a:5.2f}  ly最低 {b:5.2f}  glow {c:5.2f}  深底正文 {d:5.2f}   "
              f"{s['ink']} {s['deep']} {s['wash']} {s['glow']}")
    print()
    print('全部达标（ink ≥5.0 / ly ≥4.6 / glow ≥4.6 / 深底正文 ≥8.0）')
