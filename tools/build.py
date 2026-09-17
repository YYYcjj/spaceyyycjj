# -*- coding: utf-8 -*-
"""
宇宙航行全景 · 站点生成器

用法：
    python3 tools/build.py

输入：
    tools/content_a.py       板块 1-5 内容
    tools/content_b.py       板块 6-9 内容
    tools/board01_body.html  板块一正文（由旧版单页报告抽取而来，一次性素材）
    tools/board01_toc.json   板块一的目录条目

输出：
    index.html               首页（9 个板块的总览）
    sections/*.html          9 个板块页
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
from chains import CHAINS                     # noqa: E402
from costs import COSTS                       # noqa: E402
from designs import DESIGNS                   # noqa: E402
from ventures import VENTURES                 # noqa: E402

BOARDS = BOARDS_A + BOARDS_B
assert len(BOARDS) == 9, f'板块数应为 9，实际 {len(BOARDS)}'

# 把技术链路 / 成本 / 具体设计 / 创业者路线图挂到对应板块上（按 slug 匹配，content 文件不用管）
for _b in BOARDS:
    _b['chain'] = CHAINS.get(_b['slug'])
    _b['cost'] = COSTS.get(_b['slug'])
    _b['design'] = DESIGNS.get(_b['slug'])
    _b['venture'] = VENTURES.get(_b['slug'])
    assert _b['chain'], f'板块 {_b["slug"]} 缺少技术链路'
    assert _b['cost'], f'板块 {_b["slug"]} 缺少成本数据'
    assert _b['design'], f'板块 {_b["slug"]} 缺少具体设计'
    assert _b['venture'], f'板块 {_b["slug"]} 缺少创业者路线图'

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
}

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%231c1c1a'/%3E"
           "%3Ccircle cx='16' cy='16' r='7.5' fill='none' stroke='%23fff' stroke-width='2'/%3E"
           "%3Cellipse cx='16' cy='16' rx='13' ry='4.6' fill='none' stroke='%23fff' stroke-width='1.6'"
           " transform='rotate(-28 16 16)'/%3E%3Ccircle cx='27' cy='9.5' r='2.4' fill='%23fff'/%3E%3C/svg%3E")

CJK_NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九']


def esc(s):
    return html.escape(s, quote=True)


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
        f'      {esc(SITE["title"])}',
        f'      <small>{esc(SITE["subtitle"])}</small>',
        f'    </a>',
        f'    <nav aria-label="目录">',
    ]
    for b in BOARDS:
        active = ' active' if b['slug'] == cur['slug'] else ''
        parts.append(f'      <a class="bo{active}" href="{section_filename(b)}">'
                     f'<span class="n">{b["num"]}</span>{esc(b["title"])}</a>')
        if b['slug'] == cur['slug']:
            for s in cur['toc']:
                cls = ' class="sub"' if s['sub'] else ''
                num = '' if (s['sub'] or not s.get('n')) else f'<span class="n">{s["n"]}</span>'
                parts.append(f'      <a{cls} href="#{s["id"]}" data-toc>{num}{esc(s["title"])}</a>')
    parts.append('    </nav>')
    return '\n'.join(parts)


# ---------------------------------------------------------------- 顶部胶囊导航
def render_topnav(cur):
    items = ['<a href="../index.html">首页</a>']
    for b in BOARDS:
        active = ' class="active"' if b['slug'] == cur['slug'] else ''
        items.append(f'<a href="{section_filename(b)}"{active}>{esc(NAV_SHORT[b["slug"]])}</a>')
    return ('<nav class="topnav" aria-label="板块导航">\n  <div class="inner">\n    '
            + '\n    '.join(items) + '\n  </div>\n</nav>')


# ---------------------------------------------------------------- 上一/下一
def render_pager(cur):
    i = [b['slug'] for b in BOARDS].index(cur['slug'])
    out = []
    if i > 0:
        p = BOARDS[i - 1]
        out.append(f'<a class="pg prev" href="{section_filename(p)}">'
                   f'<span class="pg-d">上一板块 {p["num"]}</span><span class="pg-t">{esc(p["title"])}</span></a>')
    else:
        out.append('<span class="pg empty"></span>')
    if i < len(BOARDS) - 1:
        n = BOARDS[i + 1]
        out.append(f'<a class="pg next" href="{section_filename(n)}">'
                   f'<span class="pg-d">下一板块 {n["num"]}</span><span class="pg-t">{esc(n["title"])}</span></a>')
    else:
        out.append('<a class="pg next" href="../index.html">'
                   '<span class="pg-d">回到</span><span class="pg-t">全部板块总览</span></a>')
    return '<nav class="pager">\n  ' + '\n  '.join(out) + '\n</nav>'


# ---------------------------------------------------------------- 技术链路
def render_chain(b):
    """把板块的 chain 数据渲染成：最先进的方法 → 环节概览 → 逐环实现路径 → 最难的一环。"""
    ch = b.get('chain')
    if not ch:
        return ''

    cells, items = [], []
    for i, n in enumerate(ch['nodes'], 1):
        cls, lab = STATUS_MAP[n['s']]
        cells.append(f'        <div class="cb {n["s"]}">\n'
                     f'          <span class="cb-i">{i:02d}</span>\n'
                     f'          <span class="cb-t">{esc(n["t"])}</span>\n'
                     f'        </div>')
        items.append(f'        <li class="{n["s"]}">\n'
                     f'          <div class="cl-h"><span class="cl-t">{esc(n["t"])}</span>'
                     f'<span class="tag {cls}">{lab}</span></div>\n'
                     f'          <div class="cl-x">{esc(n["how"])}</div>\n'
                     f'        </li>')

    legend = ' · '.join(
        f'<span class="lg {k}"><i></i>{lab}</span>' for k, _cls, lab in CHAIN_STATUS)

    return (
        '<section id="chain">\n'
        '      <h2>技术链路<span class="en">Technology Chain</span></h2>\n'
        f'      <p class="lead">{esc(ch["lead"])}</p>\n'
        '\n'
        '      <div class="frontier">\n'
        '        <span class="fr-cap">最先进的方法</span>\n'
        f'        <span class="fr-t">{esc(ch["frontier"])}</span>\n'
        '      </div>\n'
        '\n'
        '      <div class="chain-bar">\n' + '\n'.join(cells) + '\n      </div>\n'
        f'      <div class="chain-legend"><span class="clg-cap">成熟度</span>{legend}</div>\n'
        '\n'
        '      <h3 class="chain-sub">每一环怎么实现</h3>\n'
        '      <ol class="chain-list">\n' + '\n'.join(items) + '\n      </ol>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        <b>最难的一环：</b>{esc(ch["bottleneck"])}\n'
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
                    f'            <td class="nm" data-th="项目">{esc(it["t"])}</td>\n'
                    f'            <td class="num" data-th="金额">{esc(it["a"])}</td>\n'
                    f'            <td data-th="口径与说明">{esc(it["n"])}</td>\n'
                    f'          </tr>')

    return (
        '      <h3 class="chain-sub">要花多少钱</h3>\n'
        '      <div class="tablewrap">\n'
        '        <table class="cost">\n'
        '          <thead><tr><th>项目</th><th>金额</th><th>口径与说明</th></tr></thead>\n'
        '          <tbody>\n' + '\n'.join(rows) + '\n          </tbody>\n'
        '        </table>\n'
        '      </div>\n'
        f'      <p class="cost-scale"><b>总量级：</b>{esc(cost["scale"])}</p>\n'
        '      <div class="note info">\n'
        f'        {esc(cost["note"])}\n'
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
                     f'            <td class="nm" data-th="设计参数">{esc(it["k"])}</td>\n'
                     f'            <td class="num" data-th="取值">{esc(it["v"])}</td>\n'
                     f'            <td data-th="为什么是这个值">{esc(it["n"])}</td>\n'
                     f'          </tr>')

    subs = '\n'.join(
        f'        <div class="ds">\n'
        f'          <div class="ds-t">{esc(s["t"])}</div>\n'
        f'          <div class="ds-n">{esc(s["n"])}</div>\n'
        f'        </div>' for s in d['subs'])

    return (
        '<section id="design">\n'
        '      <h2>具体设计<span class="en">Design</span></h2>\n'
        f'      <p class="lead">{esc(d["headline"])}</p>\n'
        '\n'
        '      <figure class="figure">\n'
        f'        <div class="fig-scroll">{d["scene"]()}</div>\n'
        f'        <p class="fig-hint">图为等轴测示意图，手机上可左右拖动查看细节。</p>\n'
        f'        <figcaption>图 {num}　{esc(d["caption"])}</figcaption>\n'
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
        f'        {esc(d["note"])}\n'
        '      </div>\n'
        '    </section>'
    )


# ---------------------------------------------------------------- 创业者路线图
def render_venture(b):
    """把 venture 数据渲染成：切入点 → 五个阶段（含里程碑与死法）→ 最该避免的事。"""
    v = b.get('venture')
    if not v:
        return ''

    items = []
    for i, s in enumerate(v['steps'], 1):
        items.append(
            f'        <li>\n'
            f'          <div class="vs-h">\n'
            f'            <span class="vs-p">{i:02d}</span>\n'
            f'            <span class="vs-t">{esc(s["p"])}</span>\n'
            f'            <span class="vs-w">{esc(s["w"])}</span>\n'
            f'          </div>\n'
            f'          <p class="vs-do">{esc(s["do"])}</p>\n'
            f'          <div class="vs-meta">\n'
            f'            <span class="vs-mk"><b>里程碑</b>{esc(s["mile"])}</span>\n'
            f'            <span class="vs-rk"><b>这一步的死法</b>{esc(s["risk"])}</span>\n'
            f'          </div>\n'
            f'        </li>')

    return (
        '<section id="venture">\n'
        '      <h2>创业者路线图<span class="en">Founder Roadmap</span></h2>\n'
        f'      <p class="lead">{esc(v["lead"])}</p>\n'
        '\n'
        '      <div class="entry">\n'
        '        <span class="en-cap">切入点</span>\n'
        f'        <span class="en-t">{esc(v["entry"])}</span>\n'
        '      </div>\n'
        '\n'
        '      <ol class="vs">\n' + '\n'.join(items) + '\n      </ol>\n'
        '\n'
        '      <div class="note warn">\n'
        f'        <b>最该避免：</b>{esc(v["avoid"])}\n'
        '      </div>\n'
        '      <div class="note info">\n'
        f'        {esc(v["note"])}\n'
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

    <header class="hero">
      <div class="eyebrow">板块 {num} / 09 · {en}</div>
      <h1>{h1}</h1>
      <p class="dek">{dek}</p>
      <div class="meta">{meta}</div>
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


CHAIN_TOC = dict(id='chain', title='技术链路', sub=False, n='')
DESIGN_TOC = dict(id='design', title='具体设计', sub=False, n='')
VENTURE_TOC = dict(id='venture', title='创业者路线图', sub=False, n='')


def build_section(b, board01):
    legacy = b.get('legacy')
    chain = render_chain(b)
    design = render_design(b, b['num'])
    venture = render_venture(b)
    front = '\n\n'.join(x for x in (chain, design, venture) if x)

    if legacy:
        body = board01[0]
        if front:
            # 插在 KPI 之后、第一个正式章节之前
            m = re.search(r'\n<section id=', body)
            body = body[:m.start()] + '\n\n' + front + body[m.start():]
        toc_subs = board01[1]
    else:
        n = int(b['num'])
        blocks = []
        for i, s in enumerate(b['subs']):
            blocks.append(f'<section id="{s["id"]}">\n'
                          f'    <h2>{n}.{i + 1} {esc(s["title"])}</h2>\n'
                          f'{s["html"].strip()}\n'
                          f'</section>')
        body = '\n\n'.join(blocks)
        if front:
            body = front + '\n\n' + body
        toc_subs = [dict(id=s['id'], title=s['title'], sub=False, n=f'{n}.{i + 1}')
                    for i, s in enumerate(b['subs'])]

    # 侧栏目录：技术链路 / 具体设计 / 创业者路线图 在最前面，且不带编号
    head = (([dict(CHAIN_TOC)] if chain else [])
            + ([dict(DESIGN_TOC)] if design else [])
            + ([dict(VENTURE_TOC)] if venture else []))
    b['toc'] = head + toc_subs

    h1 = b.get('h1') or b['title']
    desc = esc(b['short'] + '。' + b['dek'][:70])
    page = PAGE.format(
        title=esc(f'{b["title"]} · {SITE["title"]}'),
        desc=desc,
        favicon=FAVICON,
        topnav=render_topnav(b),
        rail=render_rail(b),
        num=b['num'], en=esc(b.get('eyebrow') or b['en']),
        h1=esc(h1), dek=esc(b['dek']), meta=esc(b['meta']),
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

    <header class="hero">
      <div class="eyebrow">{subtitle} · {date}</div>
      <h1>{site}</h1>
      <p class="dek">九个板块，从一枚已经复用 37 次的火箭，一直问到光速飞船、冬眠舱和星际通信。
        每个板块都尽量把三件事分开写清：<b>已经做到的</b>、<b>正在验证的</b>、<b>还只在纸上的</b>。</p>
      <div class="meta">数据截止 2026-09-15 ｜ 9 个板块 ｜ 全部来自公开披露信息</div>
    </header>

    <div class="kpis">
      <div class="kpi hi">
        <div class="v"><span data-count="37">0</span><em>次</em></div>
        <div class="k">单枚猎鹰9 最高复用次数<br><span style="color:var(--faint)">板块一 · 已实现</span></div>
      </div>
      <div class="kpi">
        <div class="v"><span data-count="98">0</span><em>%</em></div>
        <div class="k">ISS 水回收闭环率<br><span style="color:var(--faint)">板块四 · 已实现</span></div>
      </div>
      <div class="kpi">
        <div class="v">0.2<em>c</em></div>
        <div class="k">光帆推进的目标速度<br><span style="color:var(--faint)">板块五 · 未实现</span></div>
      </div>
      <div class="kpi zero">
        <div class="v"><span data-count="20">0</span><em>分</em></div>
        <div class="k">火星与地球单程通信延迟<br><span style="color:var(--faint)">板块九 · 改不了</span></div>
      </div>
    </div>

    <section>
      <h2>九个板块<span class="en">Contents</span></h2>
      <p class="lead">前三个板块是当下：已经飞起来的东西、火箭本身的物理极限、以及去火星之前必须跨过的那道坎。
        后六个板块向外推：人在船上怎么活、船能跑多快、能不能睡过去、怎么和外面说话、去哪拿资源、谁来开船。</p>

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

CARD = """        <a class="board-card" href="sections/{file}">
          <div class="bc-top"><span class="bc-num">{num}</span><span class="bc-en">{en}</span></div>
          <h3>{title}</h3>
          <p class="bc-dek">{dek}</p>
          <ul>
{points}
          </ul>
          <span class="bc-go">阅读板块 →</span>
        </a>"""


def build_hub():
    cards = []
    for b in BOARDS:
        points = '\n'.join(f'            <li>{esc(p)}</li>' for p in b['points'])
        cards.append(CARD.format(file=section_filename(b), num=b['num'], en=esc(b['en']),
                                 title=esc(b['title']), dek=esc(b['short']),
                                 points=points))
    desc = esc('从可回收火箭到星际航行：目前航天技术发展、航天火箭技术、星舰建造、飞船生态圈、'
               '光速推进、寿命延长与冬眠、外星文明交流、宇宙资源获取、飞船AI与机器人。')
    page = HUB.format(site=esc(SITE['title']), subtitle=esc(SITE['subtitle']), date=esc(SITE['date']),
                      desc=desc, favicon=FAVICON, cards='\n\n'.join(cards))
    out = os.path.join(ROOT, 'index.html')
    open(out, 'w', encoding='utf-8').write(page)
    return out, len(page.encode())


if __name__ == '__main__':
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
