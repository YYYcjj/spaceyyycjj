# -*- coding: utf-8 -*-
"""
宇宙航行全景 · 站点生成器

用法：
    python3 tools/build.py

输入：
    tools/content_a.py       板块 1-5 内容
    tools/content_b.py       板块 6-9 内容
    tools/content_c.py       板块 10（收口：星船总体设计）
    tools/board01_body.html  板块一正文（由旧版单页报告抽取而来，一次性素材）
    tools/board01_toc.json   板块一的目录条目

输出：
    index.html               首页（10 个板块的总览）
    sections/*.html          10 个板块页
"""

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import sys
sys.path.insert(0, HERE)
from content_a import SITE, BOARDS_A          # noqa: E402
from content_b import BOARDS_B                # noqa: E402
from content_c import BOARDS_C                # noqa: E402
from chains import CHAINS                     # noqa: E402
from costs import COSTS                       # noqa: E402
from designs import DESIGNS                   # noqa: E402
from ventures import VENTURES                 # noqa: E402
from techroad import TECHROADS                # noqa: E402
from techfigs import FIGS as TECHFIGS         # noqa: E402
from techparams import STEP_META              # noqa: E402
from chainbiz import CHAIN_BIZ                # noqa: E402
from synthfigs import SYNTH_FIGS              # noqa: E402
from theoryfigs import THEORY_FIGS            # noqa: E402
from introfigs import INTRO_FIGS              # noqa: E402
from chainfigs import CHAIN_FIGS              # noqa: E402
import spaceart                                # noqa: E402

BOARDS = BOARDS_A + BOARDS_B + BOARDS_C
assert len(BOARDS) == 10, f'板块数应为 10，实际 {len(BOARDS)}'

# 把技术链路 / 成本 / 具体设计 / 技术发展路线 / 创业者路线图挂到对应板块上（按 slug 匹配）。
# 收口板块（layers=False）不套用这套五层模板——它回答的是「合起来该怎么设计」，
# 不是又补充一个领域，硬套五层只会塞一堆并不存在的内容。
for _b in BOARDS:
    _b['chain'] = CHAINS.get(_b['slug'])
    _b['cost'] = COSTS.get(_b['slug'])
    _b['design'] = DESIGNS.get(_b['slug'])
    _b['techroad'] = TECHROADS.get(_b['slug'])
    _b['venture'] = VENTURES.get(_b['slug'])
    if not _b.get('layers', True):
        continue
    assert _b['chain'], f'板块 {_b["slug"]} 缺少技术链路'
    assert _b['cost'], f'板块 {_b["slug"]} 缺少成本数据'
    assert _b['design'], f'板块 {_b["slug"]} 缺少具体设计'
    assert _b['techroad'], f'板块 {_b["slug"]} 缺少技术发展路线'
    assert _b['venture'], f'板块 {_b["slug"]} 缺少创业者路线图'

# 创业者路线图：九个板块都要有「赛道判断」六项、每一步都要有八个字段
_V_TRACK = ('customer', 'money', 'market', 'rivals', 'moat', 'fatal')
_V_STEP = ('p', 'w', 'do', 'mode', 'gate', 'burn', 'kill', 'stop')
for _b in BOARDS:
    if not _b.get('layers', True):
        continue
    _v = _b['venture']
    for _k in _V_TRACK:
        assert _v['track'].get(_k), f'板块 {_b["slug"]} 的赛道判断缺少 {_k}'
    assert len(_v['steps']) == 5, \
        f'板块 {_b["slug"]} 的创业者路线图应为 5 个阶段，实际 {len(_v["steps"])}'
    for _i, _s in enumerate(_v['steps'], 1):
        for _k in _V_STEP:
            assert _s.get(_k), f'板块 {_b["slug"]} 第 {_i} 个阶段缺少 {_k}'

# 创业者路线图的理论图：九个板块 × 6 张（赛道判断 1 张 + 五个阶段各 1 张）
_V_PARTS = ('track', 1, 2, 3, 4, 5)
for _b in BOARDS:
    if not _b.get('layers', True):
        continue
    for _part in _V_PARTS:
        assert (_b['slug'], _part) in THEORY_FIGS, \
            f'板块 {_b["slug"]} 的「{_part}」缺少理论图'
assert len(THEORY_FIGS) == len(_V_PARTS) * 9, \
    f'理论图应为 {len(_V_PARTS) * 9} 张（九板块 × 6），实际 {len(THEORY_FIGS)}'

# 每个板块开头的两张导览图（含收口页，共十个板块）
for _b in BOARDS:
    for _i in (1, 2):
        assert (_b['slug'], _i) in INTRO_FIGS, \
            f'板块 {_b["slug"]} 缺少导览图 {_i}'
assert len(INTRO_FIGS) == 20, f'导览图应为 20 张（十板块 × 2），实际 {len(INTRO_FIGS)}'

# 技术链路的每一环都要有一张「链路图」（九板块 × 6 环 = 54 张）
_N_CHAIN_FIGS = 0
for _b in BOARDS:
    if not _b.get('layers', True):
        continue
    for _i, _n in enumerate(_b['chain']['nodes'], 1):
        assert (_b['slug'], _i) in CHAIN_FIGS, \
            f'板块 {_b["slug"]} 第 {_i} 环缺少链路图'
        _N_CHAIN_FIGS += 1
assert len(CHAIN_FIGS) == _N_CHAIN_FIGS == 54, \
    f'链路图应为 54 张（九板块 × 6 环），实际 {len(CHAIN_FIGS)}'

# 技术链路的每一环都要有「技术详解」与「创业视角」（54 环）
_N_NODES = 0
for _b in BOARDS:
    if not _b.get('layers', True):
        continue
    for _i, _n in enumerate(_b['chain']['nodes'], 1):
        _cb = CHAIN_BIZ.get((_b['slug'], _i))
        assert _cb and _cb.get('detail') and _cb.get('biz'), \
            f'板块 {_b["slug"]} 第 {_i} 环缺少技术详解或创业视角'
        _N_NODES += 1
assert len(CHAIN_BIZ) == _N_NODES, \
    f'链路详解应有 {_N_NODES} 项（与各板块环节数之和一致），实际 {len(CHAIN_BIZ)}'
for _b in BOARDS:
    if not _b.get('layers', True):
        continue
    _tr = _b['techroad']
    # 板块七比其他板块多一步（「解读」），所以是 5–6 步而不是恒等于 5
    assert 5 <= len(_tr['stages']) <= 6, \
        f'板块 {_b["slug"]} 技术路线应为 5–6 步，实际 {len(_tr["stages"])}'
    for _s in _tr['stages']:
        for _k in ('p', 'w', 'gap', 'do', 'need', 'gate'):
            assert _s.get(_k), f'板块 {_b["slug"]} 第 {_s.get("p")} 步缺少字段 {_k}'

# 把技术参数与配图挂到每一步上（(slug, 步号) 索引；叙述与数值分开维护）
_LAYERED = [b for b in BOARDS if b.get('layers', True)]
_N_STEPS = sum(len(b['techroad']['stages']) for b in _LAYERED)
assert len(STEP_META) == _N_STEPS, \
    f'技术参数表应有 {_N_STEPS} 项（与各板块步数之和一致），实际 {len(STEP_META)}'
for _b in _LAYERED:
    for _i, _s in enumerate(_b['techroad']['stages'], 1):
        _m = STEP_META.get((_b['slug'], _i))
        assert _m, f'板块 {_b["slug"]} 第 {_i} 步缺少技术参数与配图'
        assert _m['params'] and _m['fig'], f'板块 {_b["slug"]} 第 {_i} 步参数或配图为空'
        assert _m['fig'] in TECHFIGS, f'板块 {_b["slug"]} 第 {_i} 步的图键 {_m["fig"]} 不存在'
        _s['params'], _s['fig'] = _m['params'], _m['fig']

# 状态 → (标签类, 中文标签)
CHAIN_STATUS = [
    ('done', 't-done', '已实现'),
    ('run',  't-run',  '在验证'),
    ('hold', 't-hold', '待突破'),
    ('lock', 't-fail', '物理约束'),
    ('plan', 't-plan', '仅纸上'),
]
STATUS_MAP = {k: (cls, lab) for k, cls, lab in CHAIN_STATUS}

# 移动端顶部胶囊导航用的短标签
NAV_SHORT = {
    'current': '目前航天', 'rocket-tech': '火箭技术', 'starship': '星舰建造',
    'biosphere': '飞船生态圈', 'lightspeed': '光速推进', 'lifespan': '寿命与冬眠',
    'contact': '外星交流', 'resources': '宇宙资源', 'ai-robots': 'AI 与机器人',
    'integration': '星船设计',
}

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%231c1c1a'/%3E"
           "%3Ccircle cx='16' cy='16' r='7.5' fill='none' stroke='%23fff' stroke-width='2'/%3E"
           "%3Cellipse cx='16' cy='16' rx='13' ry='4.6' fill='none' stroke='%23fff' stroke-width='1.6'"
           " transform='rotate(-28 16 16)'/%3E%3Ccircle cx='27' cy='9.5' r='2.4' fill='%23fff'/%3E%3C/svg%3E")

CJK_NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九']


def esc(s):
    return html.escape(s, quote=True)


_BOLD = re.compile(r'\*\*([^*\n]+)\*\*')


def rich(s):
    """先转义、再把 **配对** 转成 <b>。

    数据文件里写 **加粗** 比写 <b> 干净，但这些字段都要过 esc()——
    直接输出会把星号当字面字符显示出来（实测有 5 处真的露在页面上）。
    只用于纯文本字段；属性值（title、desc、aria-label 等）仍旧只用 esc()。
    """
    return _BOLD.sub(r'<b>\1</b>', esc(s))


def section_filename(b):
    return f"{b['num']}-{b['slug']}.html"


# ---------------------------------------------------------------- 板块一素材
def load_board01():
    body = open(os.path.join(HERE, 'board01_body.html'), encoding='utf-8').read()
    toc = json.load(open(os.path.join(HERE, 'board01_toc.json'), encoding='utf-8'))
    # 章号重编号：一、→ 1.1，二、→ 1.2 …（仅作用于 h2 开头）
    for i, cn in enumerate(CJK_NUM):
        body = body.replace(f'<h2>{cn}、', f'<h2>1.{i + 1} ')
    # 给目录补上 1.x 编号
    n = 0
    for item in toc:
        if not item['sub']:
            n += 1
            item['n'] = f'1.{n}'
        else:
            item['n'] = ''
    return body, toc


# ---------------------------------------------------------------- 侧栏
def render_rail(cur):
    parts = [
        f'    <a class="brand" href="../index.html">',
        f'      {rich(SITE["title"])}',
        f'      <small>{rich(SITE["subtitle"])}</small>',
        f'    </a>',
        f'    <nav aria-label="目录">',
    ]
    for b in BOARDS:
        active = ' active' if b['slug'] == cur['slug'] else ''
        parts.append(f'      <a class="bo{active}" href="{section_filename(b)}">'
                     f'<span class="n">{b["num"]}</span>{rich(b["title"])}</a>')
        if b['slug'] == cur['slug']:
            # 侧栏分两组：「五层概览」（带层色点与序号）与「正文小节」（带编号）。
            # 分组的依据是 TOC 里的 layer 字段，不能靠「有没有编号」判断——
            # 板块一的正文小节本来就没有编号，会把它们误判成层。
            grp_done = False
            for s in cur['toc']:
                if s.get('layer'):
                    parts.append(f'      <a class="toc-ly ly-{s["layer"]}" href="#{s["id"]}" data-toc>'
                                 f'<i class="dot"></i>{rich(s["title"])}</a>')
                    continue
                if not grp_done:
                    parts.append('      <span class="rail-grp">正文 · 板块细节</span>')
                    grp_done = True
                cls = ' class="sub"' if s['sub'] else ''
                num = '' if (s['sub'] or not s.get('n')) else f'<span class="n">{s["n"]}</span>'
                parts.append(f'      <a{cls} href="#{s["id"]}" data-toc>{num}{rich(s["title"])}</a>')
    parts.append('    </nav>')
    return '\n'.join(parts)


# ---------------------------------------------------------------- 顶部胶囊导航
def render_topnav(cur):
    items = ['<a href="../index.html">首页</a>']
    for b in BOARDS:
        active = ' class="active"' if b['slug'] == cur['slug'] else ''
        items.append(f'<a href="{section_filename(b)}"{active}>'
                     f'{rich(NAV_SHORT.get(b["slug"], b["title"]))}</a>')
    return ('<nav class="topnav" aria-label="板块导航">\n  <div class="inner">\n    '
            + '\n    '.join(items) + '\n  </div>\n</nav>')


# ---------------------------------------------------------------- 上一/下一
def render_pager(cur):
    i = [b['slug'] for b in BOARDS].index(cur['slug'])
    out = []
    if i > 0:
        p = BOARDS[i - 1]
        out.append(f'<a class="pg prev" href="{section_filename(p)}">'
                   f'<span class="pg-d">上一板块 {p["num"]}</span><span class="pg-t">{rich(p["title"])}</span></a>')
    else:
        out.append('<span class="pg empty"></span>')
    if i < len(BOARDS) - 1:
        n = BOARDS[i + 1]
        out.append(f'<a class="pg next" href="{section_filename(n)}">'
                   f'<span class="pg-d">下一板块 {n["num"]}</span><span class="pg-t">{rich(n["title"])}</span></a>')
    else:
        out.append('<a class="pg next" href="../index.html">'
                   '<span class="pg-d">回到</span><span class="pg-t">全部板块总览</span></a>')
    return '<nav class="pager">\n  ' + '\n  '.join(out) + '\n</nav>'


# ---------------------------------------------------------------- 技术链路
def render_chain_fig(slug, idx, indent='          '):
    """渲染一环保的「链路图」；没配图时返回空串（54 环分批补）。"""
    spec = CHAIN_FIGS.get((slug, idx))
    if not spec:
        return ''
    svg = spec['make']().svg(spec['cap'])
    assert svg.lstrip().startswith('<svg'), \
        f'板块 {slug} 第 {idx} 环的链路图没有生成 SVG'
    return (
        f'{indent}<figure class="trs-fig">\n'
        f'{indent}  <div class="fig-scroll">{svg}</div>\n'
        f'{indent}  <figcaption><span class="fgn">链路图 {idx}</span>'
        f'　{rich(spec["cap"])}</figcaption>\n'
        f'{indent}</figure>\n'
    )


def render_chain(b):
    """把板块的 chain 数据渲染成：最先进的方法 → 环节概览 → 逐环实现路径 → 最难的一环。"""
    ch = b.get('chain')
    if not ch:
        return ''

    cells, items = [], []
    for i, n in enumerate(ch['nodes'], 1):
        cls, lab = STATUS_MAP[n['s']]
        cb = CHAIN_BIZ.get((b['slug'], i)) or {}
        more = ''
        if cb:
            more = ('          <div class="cl-blk">\n'
                    '            <span class="cl-cap">技术详解</span>\n'
                    f'            <p>{rich(cb["detail"])}</p>\n'
                    '          </div>\n'
                    '          <div class="cl-blk biz">\n'
                    '            <span class="cl-cap">创业视角</span>\n'
                    f'            <p>{rich(cb["biz"])}</p>\n'
                    '          </div>\n')
        cells.append(f'        <div class="cb {n["s"]}">\n'
                     f'          <span class="cb-i">{i:02d}</span>\n'
                     f'          <span class="cb-t">{rich(n["t"])}</span>\n'
                     f'        </div>')
        items.append(f'        <li class="{n["s"]}">\n'
                     f'          <div class="cl-h"><span class="cl-t">{rich(n["t"])}</span>'
                     f'<span class="tag {cls}">{lab}</span></div>\n'
                     f'          <div class="cl-x">{rich(n["how"])}</div>\n'
                     + render_chain_fig(b['slug'], i) +
                     more +
                     f'        </li>')

    legend = ' · '.join(
        f'<span class="lg {k}"><i></i>{lab}</span>' for k, _cls, lab in CHAIN_STATUS)

    return (
        '<section id="chain" class="layer ly-2">\n'
        f'      {layer_h2(2, "技术链路", "Technology Chain")}\n'
        f'      <p class="lead">{rich(ch["lead"])}</p>\n'
        '\n'
        '      <div class="frontier">\n'
        '        <span class="fr-cap">最先进的方法</span>\n'
        f'        <span class="fr-t">{rich(ch["frontier"])}</span>\n'
        '      </div>\n'
        '\n'
        '      <div class="chain-bar">\n' + '\n'.join(cells) + '\n      </div>\n'
        f'      <div class="chain-legend"><span class="clg-cap">成熟度</span>{legend}</div>\n'
        '\n'
        '      <h3 class="chain-sub">每一环怎么实现</h3>\n'
        '      <ol class="chain-list">\n' + '\n'.join(items) + '\n      </ol>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        <b>最难的一环：</b>{rich(ch["bottleneck"])}\n'
        '      </div>\n'
        '\n'
        + render_cost(b.get('cost')) + '\n'
        '    </section>'
    )


# ---------------------------------------------------------------- 要花多少钱
def render_cost(cost):
    """把成本数据渲染成一张三段式表格：项目 / 金额 / 口径与说明。"""
    if not cost:
        return ''

    rows = []
    for it in cost['items']:
        rows.append(f'          <tr>\n'
                    f'            <td class="nm" data-th="项目">{rich(it["t"])}</td>\n'
                    f'            <td class="num" data-th="金额">{rich(it["a"])}</td>\n'
                    f'            <td data-th="口径与说明">{rich(it["n"])}</td>\n'
                    f'          </tr>')

    return (
        '      <h3 class="chain-sub">要花多少钱</h3>\n'
        '      <div class="tablewrap">\n'
        '        <table class="cost">\n'
        '          <thead><tr><th>项目</th><th>金额</th><th>口径与说明</th></tr></thead>\n'
        '          <tbody>\n' + '\n'.join(rows) + '\n          </tbody>\n'
        '        </table>\n'
        '      </div>\n'
        f'      <p class="cost-scale"><b>总量级：</b>{rich(cost["scale"])}</p>\n'
        '      <div class="note info">\n'
        f'        {rich(cost["note"])}\n'
        '      </div>'
    )


# ---------------------------------------------------------------- 具体设计
def render_design(b, num):
    """把 design 数据渲染成：设计目标 → 三维等轴测图 → 设计参数 → 设计分解 → 说明。"""
    d = b.get('design')
    if not d:
        return ''

    specs = []
    for it in d['specs']:
        specs.append(f'          <tr>\n'
                     f'            <td class="nm" data-th="设计参数">{rich(it["k"])}</td>\n'
                     f'            <td class="num" data-th="取值">{rich(it["v"])}</td>\n'
                     f'            <td data-th="为什么是这个值">{rich(it["n"])}</td>\n'
                     f'          </tr>')

    subs = '\n'.join(
        f'        <div class="ds">\n'
        f'          <div class="ds-t">{rich(s["t"])}</div>\n'
        f'          <div class="ds-n">{rich(s["n"])}</div>\n'
        f'        </div>' for s in d['subs'])

    return (
        '<section id="design" class="layer ly-3">\n'
        f'      {layer_h2(3, "具体设计", "Design")}\n'
        f'      <p class="lead">{rich(d["headline"])}</p>\n'
        '\n'
        '      <figure class="figure">\n'
        f'        <div class="fig-scroll">{d["scene"]()}</div>\n'
        f'        <p class="fig-hint">图为等轴测示意图，手机上可左右拖动查看细节。</p>\n'
        f'        <figcaption>图 {num}　{rich(d["caption"])}</figcaption>\n'
        f'        <p class="fig-dl">'
        f'<a href="../figures/{b["num"]}-{b["slug"]}.svg">打开矢量原图（SVG）</a>'
        f'<span class="sep">·</span>可另存后放进 PPT、或直接打印</p>\n'
        '      </figure>\n'
        '\n'
        '      <h3 class="chain-sub">设计参数</h3>\n'
        '      <div class="tablewrap">\n'
        '        <table class="spec">\n'
        '          <thead><tr><th>设计参数</th><th>取值</th><th>为什么是这个值</th></tr></thead>\n'
        '          <tbody>\n' + '\n'.join(specs) + '\n          </tbody>\n'
        '        </table>\n'
        '      </div>\n'
        '\n'
        '      <h3 class="chain-sub">设计分解</h3>\n'
        '      <div class="design-subs">\n' + subs + '\n      </div>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        {rich(d["note"])}\n'
        '      </div>\n'
        '    </section>'
    )


# ---------------------------------------------------------------- 创业者路线图
# 赛道判断六项的显示顺序与标签（顺序即阅读顺序，不要改成 dict 的插入序）
TRACK_FIELDS = (
    ('customer', '客户与付款方'),
    ('money',    '钱从哪来'),
    ('market',   '市场量级'),
    ('rivals',   '竞争格局'),
    ('moat',     '护城河'),
    ('fatal',    '这类公司的整体死因'),
)


# ---------------------------------------------------------------- 层级路标
# 每个板块页有五层「概览栏目」（导览 / 链路 / 设计 / 技术路线 / 创业者路线图），
# 后面才是带编号的正文小节。两者原来在视觉上完全同位，读者在近两万像素的长页里
# 找不到路标，所以给层加序号 + 层色（--ly1..--ly5），并给正文区加分组标题。
LAYER_NO = {'intro': 1, 'chain': 2, 'design': 3, 'techroad': 4, 'venture': 5}


def layer_h2(no, title, en):
    """层标题：等宽层序号 + 中文标题 + 英文标签（层序号由 CSS 上色）"""
    return (f'<h2><span class="ly"><i>层</i>{no:02d}</span>{title}'
            f'<span class="en">{en}</span></h2>')


# 正文区（带编号的小节）之前的分组标题——把「五层概览」与「板块正文」分开
GRP_HD = ('<div class="grp-hd"><b>正文</b><span class="en">In Detail</span></div>')


# ---------------------------------------------------------------- 板块开头的导览
INTRO_TOC = dict(id='intro', title='先看两张图', sub=False, n='', layer=1)

INTRO_LEAD = ('第一次接触这个领域的话，先看这两张图。第一张说清「它在解决什么问题」，'
              '第二张说清「现在走到哪一步了」——本页后面所有细节，都挂在这两张图上。')


def render_intro(b):
    """板块开头的导览：给第一次接触这个领域的人两张图。"""
    figs = []
    for i in (1, 2):
        spec = INTRO_FIGS.get((b['slug'], i))
        if not spec:
            return ''
        svg = spec['make']().svg(spec['cap'])
        assert svg.lstrip().startswith('<svg'), \
            f'板块 {b["slug"]} 的导览图 {i} 没有生成 SVG'
        figs.append(
            '      <figure class="trs-fig">\n'
            f'        <div class="fig-scroll">{svg}</div>\n'
            f'        <figcaption><span class="fgn">导览图 {i}</span>'
            f'　{rich(spec["cap"])}</figcaption>\n'
            '      </figure>')
    return (
        '<section id="intro" class="layer ly-1">\n'
        f'      {layer_h2(1, "先看两张图", "Start Here")}\n'
        f'      <p class="lead">{INTRO_LEAD}</p>\n'
        '\n' + '\n'.join(figs) + '\n    </section>'
    )


def render_theory_fig(slug, part, num, indent='      '):
    """渲染一张理论图。

    没有配图时返回空串——54 张要分批补，所以这里不做「必须有图」的断言；
    等补齐之后再在构建入口加一次总数断言。
    """
    spec = THEORY_FIGS.get((slug, part))
    if not spec:
        return ''
    svg = spec['make']().svg(spec['cap'])
    # 堵死「忘了调 .svg()」那条路：对象直接塞进 HTML 会被浏览器丢掉，
    # 页面上留下一个空图框 + 完全正常的图注，而构建不报错。
    assert svg.lstrip().startswith('<svg'), f'{slug}.{part} 的理论图没有生成 SVG'
    return (
        f'{indent}<figure class="trs-fig">\n'
        f'{indent}  <div class="fig-scroll">{svg}</div>\n'
        f'{indent}  <figcaption><span class="fgn">理论图 {num}</span>'
        f'　{rich(spec["cap"])}</figcaption>\n'
        f'{indent}</figure>\n'
    )


def render_venture(b):
    """把 venture 数据渲染成：切入点 → 赛道判断 → 五个阶段（八字段）→ 最该避免的事。"""
    v = b.get('venture')
    if not v:
        return ''

    track = '\n'.join(
        f'        <div class="vt-i">\n'
        f'          <dt>{lab}</dt>\n'
        f'          <dd>{rich(v["track"][key])}</dd>\n'
        f'        </div>'
        for key, lab in TRACK_FIELDS)

    items = []
    num = 1                       # 理论图在层内统一编号：赛道判断 = 1，五个阶段 = 2..6
    for i, s in enumerate(v['steps'], 1):
        num += 1
        items.append(
            f'        <li>\n'
            f'          <div class="vs-h">\n'
            f'            <span class="vs-p">{i:02d}</span>\n'
            f'            <span class="vs-t">{rich(s["p"])}</span>\n'
            f'            <span class="vs-w">{rich(s["w"])}</span>\n'
            f'          </div>\n'
            f'          <p class="vs-do">{rich(s["do"])}</p>\n'
            f'          <div class="vs-meta">\n'
            f'            <span class="vs-md"><span class="lb">卖什么给谁</span>{rich(s["mode"])}</span>\n'
            f'            <span class="vs-bn"><span class="lb">这一步要投多少</span>{rich(s["burn"])}</span>\n'
            f'            <span class="vs-gt"><span class="lb">通过判据</span>{rich(s["gate"])}</span>\n'
            f'            <span class="vs-kk"><span class="lb">这一步的死法</span>{rich(s["kill"])}</span>\n'
            f'          </div>\n'
            + render_theory_fig(b['slug'], i, num, '          ') +
            f'          <p class="vs-st"><span class="lb">止损线</span>{rich(s["stop"])}</p>\n'
            f'        </li>')

    html = (
        '<section id="venture" class="layer ly-5">\n'
        f'      {layer_h2(5, "创业者路线图", "Founder Roadmap")}\n'
        f'      <p class="lead">{rich(v["lead"])}</p>\n'
        '\n'
        '      <div class="entry">\n'
        '        <span class="en-cap">切入点</span>\n'
        f'        <span class="en-t">{rich(v["entry"])}</span>\n'
        '      </div>\n'
        '\n'
        '      <h3>赛道判断<span class="h3-en">Track Check</span></h3>\n'
        '      <dl class="vt">\n' + track + '\n      </dl>\n'
        + render_theory_fig(b['slug'], 'track', 1) +
        '\n'
        '      <h3>五个阶段<span class="h3-en">Five Stages</span></h3>\n'
        '      <ol class="vs">\n' + '\n'.join(items) + '\n      </ol>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        <b>最该避免：</b>{rich(v["avoid"])}\n'
        '      </div>\n'
        '      <div class="note info">\n'
        f'        {rich(v["note"])}\n'
        '      </div>\n'
        '    </section>'
    )
    # 标签必须用 .lb，不能用 <b>：正文加粗也是 <b>，
    # 一旦给 <b> 配上 display:block，正文里的加粗就会独占一行、标点被甩下去。
    _n_lb = html.count('class="lb"')
    _want = len(v['steps']) * 5
    assert _n_lb == _want, \
        f'板块 {b["slug"]} 路线图的标签数应为 {_want}，实际 {_n_lb}'
    return html


# ---------------------------------------------------------------- 技术发展路线
ARROW_SVG = ('<svg width="26" height="12" viewBox="0 0 26 12" fill="none" aria-hidden="true">'
             '<path d="M0 6h22M17 1.5 22.5 6 17 10.5" stroke="#9a9992" stroke-width="1.4" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>')

TECHROAD_LEAD = (
    '下面这五步有先后依赖——前一步的通过判据不成立，后一步就无从谈起，'
    '所以顺序不能调换、也不能跳。每一步都写明「要跨的差距 / 具体怎么做 / 需要什么条件 / 通过判据」，'
    '判据是可观测的工程事实（试车时长、复用次数、回收率、σ 值），不是进度百分比。'
)


def _stage_w_class(w):
    """把「时间量级」这个字段兼作状态位：已走完=绿、在推进=蓝、其余按年计=灰。"""
    if w.startswith('已走完'):
        return ' done'
    if w.startswith('在推进') or w.startswith('走完'):
        return ' run'
    return ''


def render_techroad(b):
    """把 techroad 数据渲染成：今天→目标对比 + 五步推进（差距/做法/条件/判据）+ 最硬的一关。"""
    t = b.get('techroad')
    if not t:
        return ''

    items = []
    for s in t['stages']:
        fig_html = ''
        spec = TECHFIGS.get(s.get('fig'))
        if spec:
            fig_html = (
                '            <figure class="trs-fig">\n'
                '              <div class="fig-scroll">'
                + spec['make']().svg(spec['cap']) + '</div>\n'
                f'              <figcaption>{rich(spec["cap"])}</figcaption>\n'
                '            </figure>\n'
            )

        prm_html = ''
        if s.get('params'):
            rows = []
            for pk, pv, pn in s['params']:        # techparams 里是 (参数名, 取值, 口径) 三元组
                rows.append(f'              <tr>\n'
                            f'                <td class="nm" data-th="技术参数">{rich(pk)}</td>\n'
                            f'                <td class="num" data-th="取值">{rich(pv)}</td>\n'
                            f'                <td data-th="口径与依据">{rich(pn)}</td>\n'
                            f'              </tr>')
            prm_html = (
                '            <div class="tablewrap">\n'
                '              <table class="params">\n'
                '                <thead><tr><th>技术参数</th><th>取值</th>'
                '<th>口径与依据</th></tr></thead>\n'
                '                <tbody>\n' + '\n'.join(rows) + '\n                </tbody>\n'
                '              </table>\n'
                '            </div>\n'
            )

        items.append(
            f'        <li>\n'
            f'          <div class="trs-card">\n'
            f'            <div class="trs-h">\n'
            f'              <span class="trs-t">{rich(s["p"])}</span>\n'
            f'              <span class="trs-w{_stage_w_class(s["w"])}">{rich(s["w"])}</span>\n'
            f'            </div>\n'
            f'            <p class="trs-gap"><b>要跨的差距　</b>{rich(s["gap"])}</p>\n'
            f'            <p class="trs-do"><b>怎么做　</b>{rich(s["do"])}</p>\n'
            + fig_html + prm_html +
            f'            <div class="trs-meta">\n'
            f'              <span class="trs-nd"><b>需要的条件</b>{rich(s["need"])}</span>\n'
            f'              <span class="trs-gt"><b>通过判据</b>{rich(s["gate"])}</span>\n'
            f'            </div>\n'
            f'          </div>\n'
            f'        </li>')

    return (
        '<section id="techroad" class="layer ly-4">\n'
        f'      {layer_h2(4, "技术怎么一步步做", "Technology Roadmap")}\n'
        f'      <p class="lead">{TECHROAD_LEAD}</p>\n'
        '\n'
        '      <div class="trbook">\n'
        '        <div class="trb now">\n'
        '          <b>今天在哪</b>\n'
        f'          <p>{rich(t["now"])}</p>\n'
        '        </div>\n'
        f'        <div class="trb-arw">{ARROW_SVG}</div>\n'
        '        <div class="trb goal">\n'
        '          <b>要到哪</b>\n'
        f'          <p>{rich(t["goal"])}</p>\n'
        '        </div>\n'
        '      </div>\n'
        '\n'
        '      <ol class="trs">\n' + '\n'.join(items) + '\n      </ol>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        <b>最硬的一关：</b>{rich(t["hard"])}\n'
        '      </div>\n'
        '      <div class="note info">\n'
        f'        {rich(t["note"])}\n'
        '      </div>\n'
        '    </section>'
    )


# ---------------------------------------------------------------- 页面外壳
PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#f5f5f2">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:locale" content="zh_CN">
<meta property="og:type" content="article">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="../assets/site.css">
</head>
<body>

<div id="progress"></div>

{topnav}

<div class="shell">

  <!-- ================= 侧栏目录 ================= -->
  <aside class="rail">
{rail}
  </aside>

  <!-- ================= 正文 ================= -->
  <main class="main">

    <header class="hero hud">
      <div class="sky" aria-hidden="true"></div>
      <div class="hero-in">
        <div class="eyebrow">板块 {num} / 10 · {en}</div>
        <h1>{h1}</h1>
        <p class="dek">{dek}</p>
        <div class="meta">{meta}</div>
      </div>
      <div class="rail-line" aria-hidden="true"></div>
    </header>

{body}

{pager}

    <footer>
      <b>{site}</b> · {subtitle}<br>
      本页为公开信息整理，数据与判断均已标注来源与不确定性，不构成任何投资建议。<br>
      <a href="../index.html">← 返回全部板块</a>
    </footer>

  </main>
</div>

<button id="totop" type="button" aria-label="回到顶部">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>

<script src="../assets/site.js"></script>
</body>
</html>
"""


# ---------------------------------------------------------------- 首屏与仪表化
def render_meta(meta):
    """首屏底部的「遥测条」：把用 ｜ 分隔的元信息拆成等宽小标签。

    段数在 2–4 之间才拆——只有一段（或特别多段）时拆了反而难看，直接原样输出。
    """
    parts = [p.strip() for p in meta.split('｜') if p.strip()]
    if 2 <= len(parts) <= 4:
        return '\n          '.join(f'<span>{esc(p)}</span>' for p in parts)
    return esc(meta)


FIG_NUM_RE = re.compile(r'<figcaption>(图\s*[0-9][0-9.]*)')


def decorate_captions(body):
    """把图注里的「图 05」包成等宽小标签。

    在**最终 HTML 上做正则**，而不是改各个渲染函数——图注来自四处渲染器
    加上板块一那份静态素材，逐个改容易漏，正则一处收口。
    """
    return FIG_NUM_RE.sub(r'<figcaption><span class="fgn">\1</span>', body)


# ---------------------------------------------------------------- 正文内的图占位符
FIG_RE = re.compile(r'\{\{FIG:([a-z0-9_]+)\}\}')


def render_figs(body, num):
    """把正文里的 {{FIG:key}} 换成 <figure>，键取自 synthfigs.SYNTH_FIGS。

    收口板块的图直接长在正文中间（不像别的板块是「一层一图」），所以用占位符引用，
    图仍然集中在 synthfigs.py 里维护。编号按出现顺序给 图 N.1 / N.2 …
    """
    seq = [0]

    def sub(m):
        key = m.group(1)
        spec = SYNTH_FIGS.get(key)
        assert spec, f'未知的图键 {key}（请检查 tools/synthfigs.py 的 SYNTH_FIGS）'
        seq[0] += 1
        # 必须显式调 .svg()：make() 返回的是图对象，直接插进 f-string 会渲染成
        # `<iso.Iso object at 0x…>` 这种被浏览器当成未知标签丢掉的东西——
        # 页面上留下一个**空图框 + 正常图注**，而且全程不报错。加断言把这条路堵死。
        svg = spec['make']().svg(spec['cap'])
        assert svg.lstrip().startswith('<svg'), f'图 {key} 没有产出 SVG'
        return (
            '<figure class="figure">\n'
            f'        <div class="fig-scroll">{svg}</div>\n'
            '        <p class="fig-hint">图为示意图，手机上可左右拖动查看细节。</p>\n'
            f'        <figcaption>图 {num}.{seq[0]}　{rich(spec["cap"])}</figcaption>\n'
            '      </figure>'
        )

    out = FIG_RE.sub(sub, body)
    left = FIG_RE.findall(out)
    assert not left, f'仍有未替换的图占位符：{left}'
    return out


CHAIN_TOC = dict(id='chain', title='技术链路', sub=False, n='', layer=2)
DESIGN_TOC = dict(id='design', title='具体设计', sub=False, n='', layer=3)
TECHROAD_TOC = dict(id='techroad', title='技术怎么一步步做', sub=False, n='', layer=4)
VENTURE_TOC = dict(id='venture', title='创业者路线图', sub=False, n='', layer=5)


def build_section(b, board01):
    legacy = b.get('legacy')
    intro = render_intro(b)
    chain = render_chain(b)
    design = render_design(b, b['num'])
    techroad = render_techroad(b)
    venture = render_venture(b)
    front = '\n\n'.join(x for x in (intro, chain, design, techroad, venture) if x)

    if legacy:
        body = board01[0]
        if front:
            # 插在 KPI 之后、第一个正式章节之前（正文分组标题也跟着插在这里）
            m = re.search(r'\n<section id=', body)
            body = body[:m.start()] + '\n\n' + front + '\n\n' + GRP_HD + body[m.start():]
        toc_subs = board01[1]
    else:
        n = int(b['num'])
        blocks = []
        for i, s in enumerate(b['subs']):
            blocks.append(f'<section id="{s["id"]}">\n'
                          f'    <h2>{n}.{i + 1} {rich(s["title"])}</h2>\n'
                          f'{s["html"].strip()}\n'
                          f'</section>')
        body = '\n\n'.join(blocks)
        if front:
            body = front + '\n\n' + GRP_HD + '\n\n' + body
        toc_subs = [dict(id=s['id'], title=s['title'], sub=False, n=f'{n}.{i + 1}')
                    for i, s in enumerate(b['subs'])]

    # 侧栏目录：这几项概览排在最前面（导览在最上），且不带编号
    head = (([dict(INTRO_TOC)] if intro else [])
            + ([dict(CHAIN_TOC)] if chain else [])
            + ([dict(DESIGN_TOC)] if design else [])
            + ([dict(TECHROAD_TOC)] if techroad else [])
            + ([dict(VENTURE_TOC)] if venture else []))
    b['toc'] = head + toc_subs

    body = render_figs(body, b['num'])
    body = decorate_captions(body)

    h1 = b.get('h1') or b['title']
    desc = esc(b['short'] + '。' + b['dek'][:70])
    page = PAGE.format(
        title=esc(f'{b["title"]} · {SITE["title"]}'),
        desc=desc,
        favicon=FAVICON,
        topnav=render_topnav(b),
        rail=render_rail(b),
        num=b['num'], en=esc(b.get('eyebrow') or b['en']),
        h1=esc(h1), dek=esc(b['dek']), meta=render_meta(b['meta']),
        body=body,
        pager=render_pager(b),
        site=esc(SITE['title']), subtitle=esc(SITE['subtitle']),
    )
    out = os.path.join(ROOT, 'sections', section_filename(b))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(page)
    return out, len(page.encode())


# ---------------------------------------------------------------- 首页
HUB = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{site} · {date}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#f5f5f2">
<meta property="og:title" content="{site} · {date}">
<meta property="og:description" content="{desc}">
<meta property="og:locale" content="zh_CN">
<meta property="og:type" content="website">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>

<div id="progress"></div>

<div class="shell hub">

  <main class="main">

    <header class="hero hud">
      <div class="sky" aria-hidden="true"></div>
      <div class="hero-in">
        <div class="eyebrow">{subtitle} · {date}</div>
        <h1>{site}</h1>
        <p class="dek">十个板块，从一枚已经复用 37 次的火箭，一直问到光速飞船、冬眠舱和星际通信。
          每个板块都尽量把三件事分开写清：<b>已经做到的</b>、<b>正在验证的</b>、<b>还只在纸上的</b>。
          最后一个板块把前面九个的条件合起来，收拢成一版星船总体设计。</p>
        <div class="meta">{meta}</div>
      </div>
      <div class="rail-line" aria-hidden="true"></div>
    </header>

    <div class="kpis">
      <div class="kpi hi">
        <div class="v"><span data-count="37">0</span><em>次</em></div>
        <div class="k">单枚猎鹰9 最高复用次数<br><span>板块一 · 已实现</span></div>
      </div>
      <div class="kpi">
        <div class="v"><span data-count="98">0</span><em>%</em></div>
        <div class="k">ISS 水回收闭环率<br><span>板块四 · 已实现</span></div>
      </div>
      <div class="kpi">
        <div class="v">0.2<em>c</em></div>
        <div class="k">光帆推进的目标速度<br><span>板块五 · 未实现</span></div>
      </div>
      <div class="kpi zero">
        <div class="v"><span data-count="20">0</span><em>分</em></div>
        <div class="k">火星与地球单程通信延迟<br><span>板块九 · 改不了</span></div>
      </div>
    </div>

    <section>
      <h2>十个板块<span class="en">Contents</span></h2>
      <p class="lead">前三个板块是当下：已经飞起来的东西、火箭本身的物理极限、以及去火星之前必须跨过的那道坎。
        中间六个板块向外推：人在船上怎么活、船能跑多快、能不能睡过去、怎么和外面说话、去哪拿资源、谁来开船。
        最后一个板块把前面九个的条件合起来——因为放在一起看才会发现，它们之间是有先后顺序的。</p>

      <div class="board-grid">
{cards}
      </div>
    </section>

    <footer>
      <b>{site}</b> · {subtitle}<br>
      数据来源：SpaceX 官网与飞行记录、NASA / ESA / ISRO 公开资料、FAA 发射通告、国家航天局通报，
      以及 The Astronomical Journal、Nature、Science、《Aging》等期刊论文与各企业公开披露。<br>
      整理日期 2026-09-15 ｜ 本页仅为公开信息整理，不构成任何投资建议。
    </footer>

  </main>
</div>

<button id="totop" type="button" aria-label="回到顶部">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>

<script src="assets/site.js"></script>
</body>
</html>
"""

CARD = """        <a class="board-card{cls}" href="sections/{file}">
          <div class="bc-top"><span class="bc-num">{num}</span><span class="bc-en">{en}</span></div>
          <h3>{title}</h3>
          <p class="bc-dek">{dek}</p>
          <ul>
{points}
          </ul>
          <span class="bc-go">{go}</span>
        </a>"""


def build_hub():
    cards = []
    for b in BOARDS:
        points = '\n'.join(f'            <li>{rich(p)}</li>' for p in b['points'])
        capstone = not b.get('layers', True)
        cards.append(CARD.format(
            file=section_filename(b), num=b['num'], en=esc(b['en']),
            title=esc(b['title']), dek=esc(b['short']), points=points,
            cls=' capstone' if capstone else '',
            go='收口 · 看整体方案 →' if capstone else '阅读板块 →'))
    desc = esc('从可回收火箭到星际航行：目前航天技术发展、航天火箭技术、星舰建造、飞船生态圈、'
               '光速推进、寿命延长与冬眠、外星文明交流、宇宙资源获取、飞船AI与机器人，'
               '最后把九个板块的条件收拢成一版星船总体设计。')
    page = HUB.format(site=esc(SITE['title']), subtitle=esc(SITE['subtitle']), date=esc(SITE['date']),
                      desc=desc, favicon=FAVICON, cards='\n\n'.join(cards),
                      meta=render_meta('数据截止 2026-09-15 ｜ 10 个板块 ｜ 全部来自公开披露信息'))
    out = os.path.join(ROOT, 'index.html')
    open(out, 'w', encoding='utf-8').write(page)
    return out, len(page.encode())


if __name__ == '__main__':
    # 舷窗背景（星场/网格/轨道弧）每次构建都重生成，保证与代码同步、且结果确定
    print('=== 舷窗背景 ===')
    for _p, _n in spaceart.write_assets(os.path.join(ROOT, 'assets')):
        print(f'  {os.path.relpath(_p, ROOT):<34} {_n:>7,} B')

    b01 = load_board01()
    total = 0
    print('=== 板块页 ===')
    for b in BOARDS:
        path, size = build_section(b, b01)
        total += size
        print(f'  {os.path.relpath(path, ROOT):<34} {size:>7,} B')
    path, size = build_hub()
    total += size
    print('=== 首页 ===')
    print(f'  {os.path.relpath(path, ROOT):<34} {size:>7,} B')
    print()
    print(f'  合计 {total:,} B / {len(BOARDS) + 1} 个页面')
