# -*- coding: utf-8 -*-
"""板块十「星船总体设计」的配图。

五张图，各回答一个问题：

    deps     九个板块给出的条件 → 由此确定的设计决策（对照式，dia）
    overall  星船总体构型：轴向串联的舱段（三维等轴测，iso）
    section  沿船轴的剖面：舱段 / 屏蔽需求 / 人员活动（三条对齐带，dia）
    mass     化学推进的质量比曲线（**由火箭方程算出**，不是估的）
    trades   五对互相打架的要求，以及设计上怎么化解（dia）

三维图沿用 iso.py 的几何与配色，二维图沿用 dia.py。
**改图之后必须重跑 `python3 tools/check_figs.py`**——手写像素坐标最容易出
「文字出框」和「互相重叠」，而这两类问题截图基本看不出来（SVG 会直接裁掉）。
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from iso import Iso, INK, MUTED, FAINT                              # noqa: E402
from dia import (Dia, INK as DINK, MUTED as DM, FAINT as DF,        # noqa: E402
                 LINE, GREEN, GREEN_B, GREEN_BR, BLUE, BLUE_B, BLUE_BR,
                 AMBER, AMBER_B, AMBER_BR, RED, RED_B, RED_BR, GRAY, GRAY_B, GRAY_BR)

# 屏幕水平位移换算（与 designs.py 同一套推导）
_K = 1 / 0.8660254
_T = 0.5 / 0.8660254


def roff(p, d):
    x, y, z = p
    return (x + d * _K, y, z + d * _T)


def loff(p, d):
    x, y, z = p
    return (x, y + d * _K, z + d * _T)


# ============================================================ 1. 依赖链（dia）
# (类别, 左侧：板块给出的条件 + 出处, 右侧：由此确定的设计决策 + 理由)
DEPS = [
    ('blue', '复飞与翻修决定成本', '板块一 / 二 · 已实现',
     '船分体发射、在轨组装', '用发射次数换单次运力'),
    ('blue', '化学比冲已到理论附近', '板块二 · 提不动了',
     '不指望更快，靠加注补 Δv', '推进方式不再是可调变量'),
    ('blue', '在轨低温加注是必经之路', '板块三 · 一次都没做过',
     '贮箱独立成段，可分批补加', '加注接口成为关键单点'),
    ('green', '食物闭环是生保最弱环', '板块四 · 98% 只在水中',
     '生态舱承担食物与氧再生', '不能全靠地面补货'),
    ('green', '辐射防护没有技术路线', '板块四 · 唯一未定项',
     '水与废物做屏蔽，并尽量缩短暴露', '设计上只能靠「更快」兜底'),
    ('amber', '光速推进没有减速方案', '板块五 · 物理约束',
     '目标收缩到太阳系以内', '0.2c 只留给无人探测器'),
    ('amber', '深空通信单程 20 分钟起', '板块九 · 改不了',
     '船上必须自主，通信只留回传', '板块七也说明：对话不成立'),
]

_CAT = {'blue': (BLUE, BLUE_B, BLUE_BR),
        'green': (GREEN, GREEN_B, GREEN_BR),
        'amber': (AMBER, AMBER_B, AMBER_BR)}

_DEPS_NOTE = ('从上到下：前三行决定运力与推进方式，中间两行决定生存条件，'
              '最后两行划出物理边界——边界那两条不是「待突破」，是改不了。')


def scene_deps():
    d = Dia(680, 420)
    lx, lw = 14, 286
    rx, rw = 380, 286
    d.text(lx, 26, '九个板块给出的条件', 10, DM, weight=600)
    d.text(rx, 26, '由此确定的总体设计决策', 10, DM, weight=600)
    d.line(lx, 34, lx + lw, 34, LINE, 1)
    d.line(rx, 34, rx + rw, 34, LINE, 1)

    y = 44
    for cat, lt, ls, rt, rs in DEPS:
        main, fill, bd = _CAT[cat]
        d.rect(lx, y, lw, 40, fill, bd, 1, 6)
        d.text(lx + 12, y + 17, lt, 11, main, weight=600)
        d.text(lx + 12, y + 31, ls, 9.5, DF)
        d.arrow(lx + lw + 6, y + 20, rx - 6, y + 20, bd, 1.3)
        d.rect(rx, y, rw, 40, '#ffffff', bd, 1, 6)
        d.text(rx + 12, y + 17, rt, 11, DINK, weight=600)
        d.text(rx + 12, y + 31, rs, 9.5, DF)
        y += 48

    d.text(14, y + 16, _DEPS_NOTE, 10, DF)
    return d


# ============================================================ 2. 总体构型（iso）
def scene_overall():
    """轴向串联的星船：沿 z 轴叠放舱段，每段可单独发射、在轨对接。

    刻意**不让各段同色同径**——全画成等径圆柱会读成一根光筒，看不出分了多少段。
    """
    g = Iso(w=680, h=450)
    # z 从下往上 = 从尾部到船首
    g.cyl(0, 0, 0, 30, 22, 'dark')                 # 推进段
    g.cyl(0, 0, 22, 30, 76, 'blue')                # 低温贮箱段
    g.cyl(0, 0, 98, 42, 2, 'gray')                 # 遮阳板（比船体宽，挡住侧面阳光）
    g.cyl(0, 0, 100, 22, 16, 'gray')               # 节点舱 / 气闸（收径表示过渡）
    g.cyl(0, 0, 116, 28, 36, 'green')              # 生态舱
    g.cyl(0, 0, 152, 28, 44, 'white')              # 乘员舱
    g.cyl(0, 0, 196, 18, 16, 'steel')              # 前部接口段
    # 太阳翼与散热面：都挂在贮箱段外侧，两片成对。
    # **不要挂到舱段中段的高度**——水平薄板在等轴测里一定会横穿后面的舱段，
    # 看起来像把船切了一刀。挂在服务段（贮箱段）既符合工程习惯，也不挡别的段。
    g.box(24, -6, 50, 56, 12, 3, 'blue2')
    g.box(-6, 24, 50, 12, 56, 3, 'blue2')
    g.box(24, -8, 74, 44, 16, 1.5, 'white')
    g.box(-8, 24, 74, 16, 44, 1.5, 'white')
    # 标注：右侧三条、左侧三条，同一侧的 v 必须拉开（v = (x+y)/2 - z）
    g.leader((30, 0, 11), roff((30, 0, 11), 46), '推进段：发动机组与主结构')
    g.leader((30, 0, 60), roff((30, 0, 60), 46), '低温贮箱段 · 外覆遮阳板')
    g.leader((28, 0, 174), roff((28, 0, 174), 46), '乘员舱 · 内设辐射避难所')
    g.leader((0, 22, 108), loff((0, 22, 108), 46), '节点舱 / 气闸', anchor='end')
    g.leader((0, 40, 50), loff((0, 40, 50), 46), '太阳翼与散热面', anchor='end')
    g.leader((0, 28, 134), loff((0, 28, 134), 46), '生态舱：食物与氧再生', anchor='end')
    return g


# ============================================================ 3. 沿轴剖面（dia）
# (舱段名, 一句话功能, 屏蔽需求档, 人员活动)
SEGS = [
    ('推进段', '发动机组', 'low', '禁入 · 机器人'),
    ('贮箱段', '低温推进剂', 'low', '禁入'),
    ('节点舱', '对接与气闸', 'mid', '轮值通过'),
    ('生态舱', '种植与生保', 'mid', '可无人'),
    ('乘员舱', '作息与工作', 'high', '常驻'),
    ('避难点', '水与废物屏蔽', 'top', '风暴时进入'),
    ('接口段', '着陆器与货船', 'low', '通过'),
]

_SHIELD = {'low': ('低', GRAY, GRAY_B, GRAY_BR),
           'mid': ('中', BLUE, BLUE_B, BLUE_BR),
           'high': ('高', AMBER, AMBER_B, AMBER_BR),
           'top': ('最高', RED, RED_B, RED_BR)}

_SEGS_NOTE = ('屏蔽需求的排序说明一件事：船上真正需要重屏蔽的只有乘员舱与避难所，'
              '而质量恰恰要花在这里——这是全船最难省的一笔。')


def scene_section():
    d = Dia(680, 232)
    lx, x0, w = 14, 76, 580
    bw = w / len(SEGS)
    ly1, ly2, ly3 = 52, 112, 146

    d.text(lx, ly1 + 26, '舱段', 10, DM, weight=600)
    d.text(lx, ly2 + 17, '屏蔽需求', 10, DM, weight=600)
    d.text(lx, ly3 + 17, '人员活动', 10, DM, weight=600)

    for i, (name, spec, sh, crew) in enumerate(SEGS):
        bx = x0 + i * bw
        d.rect(bx + 1, ly1, bw - 2, 46, '#ffffff', GRAY_BR, 1, 4)
        d.text(bx + bw / 2, ly1 + 19, name, 11, DINK, 'middle', 600)
        d.text(bx + bw / 2, ly1 + 34, spec, 9, DF, 'middle')
        lab, main, fill, bd = _SHIELD[sh]
        d.rect(bx + 1, ly2, bw - 2, 26, fill, bd, 1, 4)
        d.text(bx + bw / 2, ly2 + 17, lab, 10, main, 'middle', 600)
        d.rect(bx + 1, ly3, bw - 2, 26, '#fafaf8', LINE, 1, 4)
        d.text(bx + bw / 2, ly3 + 17, crew, 9.5, DM, 'middle')

    d.text(lx, ly3 + 62, _SEGS_NOTE, 10, DF)
    return d


# ============================================================ 4. 质量账（dia）
# 用火箭方程算，不估：m0/mf = exp(Δv / (Isp · g0))
G0 = 9.80665
_DV = [4, 6, 9, 12, 15, 20, 25]


def _ratio(dv_kms, isp):
    return math.exp(dv_kms * 1000.0 / (isp * G0))


_METH = [math.log10(_ratio(v, 380)) for v in _DV]
_HYDRO = [math.log10(_ratio(v, 450)) for v in _DV]

_MASS_NOTE = ('读法：火星往返要 9–10 km/s，甲烷机需要 11 倍质量比——'
              '出发质量里 91% 是推进剂。')
_MASS_NOTE2 = '想留出载荷与结构，只能靠在轨加注把这一段补上。'


def scene_mass():
    d = Dia(680, 296)
    d.series(78, 44, 560, 150,
             xlabels=[str(v) for v in _DV],
             ylabels=['1000×', '100×', '10×', '1×'],
             lines=[('液氧 / 甲烷（Isp 380 s）', _METH, 'blue', None),
                    ('液氢 / 液氧（Isp 450 s）', _HYDRO, 'green', '4 3')],
             xname='任务所需 Δv（km/s）', yname='质量比（对数）', ymax=3)
    # 注意：dia 的 text 不解析 markdown，别在这里写 **加粗**，否则星号会原样显示
    d.text(78, 226, '纵轴是对数刻度：10 倍与 100 倍在图上是等距的。', 10, DF)
    d.text(78, 248, _MASS_NOTE, 10, DF)
    d.text(78, 264, _MASS_NOTE2, 10, DF)
    return d


# ============================================================ 5. 设计权衡（dia）
# (左侧要求, 右侧要求, 解法第一行, 解法第二行)
TRADES = [
    ('航程要更快', '质量要更小', '不追速度：用加注补 Δv，', '目标收缩到太阳系以内'),
    ('屏蔽要更厚', '质量要更小', '用水与废物就地做屏蔽，', '并尽量缩短暴露时间'),
    ('船上要自主', '算力受抗辐射限制', '分级自主：关键回路用加固电路，', '其余用商用芯片加冗余'),
    ('系统要高冗余', '质量要更小', '只给不可更换的部件做冗余，', '能换的改为带备件'),
    ('乘员要舒适', '质量要更小', '让乘员休眠：把舱段做成病房，', '而不是酒店'),
]


def scene_trades():
    d = Dia(680, 356)
    lx, lw = 14, 168
    rx, rw = 240, 168
    sx = 430
    d.text(lx, 26, '一侧要求', 10, DM, weight=600)
    d.text(rx, 26, '另一侧要求', 10, DM, weight=600)
    d.text(sx, 26, '设计上的解法', 10, DM, weight=600)
    d.line(lx, 34, lx + lw + 60, 34, LINE, 1)
    d.line(sx, 34, sx + 236, 34, LINE, 1)

    y = 46
    for lt, rt, s1, s2 in TRADES:
        d.rect(lx, y, lw, 44, BLUE_B, BLUE_BR, 1, 6)
        d.text(lx + 12, y + 27, lt, 11, BLUE, weight=600)
        d.arrow(lx + lw + 8, y + 22, rx - 8, y + 22, GRAY_BR, 1.2)
        d.arrow(rx - 8, y + 22, lx + lw + 8, y + 22, GRAY_BR, 1.2)
        d.rect(rx, y, rw, 44, AMBER_B, AMBER_BR, 1, 6)
        d.text(rx + 12, y + 27, rt, 11, AMBER, weight=600)
        d.text(sx, y + 20, s1, 10, DINK)
        d.text(sx, y + 35, s2, 10, DINK)
        y += 56

    d.text(14, y + 12, '五对要求里，前三对是硬约束（物理与器件决定），后两对可以靠设计让步。',
           10, DF)
    return d


# ============================================================ 注册表
SYNTH_FIGS = {
    'deps': dict(cap='九个板块的条件并不是并列的，每一条都直接决定了一项总体设计决策。',
                 make=scene_deps),
    'overall': dict(cap='轴向串联的分体构型：每段单独发射、在轨对接，'
                        '推进剂段独立出来是为了反复补加。',
                    make=scene_overall),
    'section': dict(cap='沿船轴的剖面：屏蔽需求集中在乘员舱与避难所两段，'
                        '而质量恰恰要花在这里。',
                    make=scene_section),
    'mass': dict(cap='火箭方程算出的质量比：化学推进在 9 km/s 量级就已经把质量比推到 11 倍，'
                     '所以加注不是优化项而是前提。',
                 make=scene_mass),
    'trades': dict(cap='设计不是在满足所有要求，而是在这几对矛盾里选一个可接受的折中。',
                   make=scene_trades),
}
