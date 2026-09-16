# -*- coding: utf-8 -*-
"""把九个板块的三维等轴测图导出成独立文件。

    python3 tools/export_figures.py            # 只导出 SVG
    SHOT_PNG=1 python3 tools/export_figures.py # 提示同时需要渲 PNG（由外部脚本负责）

输出：
    figures/NN-slug.svg    自包含的矢量图（含白底、标题、图注），可直接双击查看或放进 PPT
    figures/index.json     清单（文件名 / 标题 / 图注 / 尺寸），供渲染或索引使用

为什么不直接把页面里那段内联 SVG 另存：内联版本没有 xmlns、没有白底、
标题与图注在 HTML 的 <figcaption> 里，单独存出来会是一张没有说明的透明图。
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from content_a import BOARDS_A                 # noqa: E402
from content_b import BOARDS_B                 # noqa: E402
from designs import DESIGNS                    # noqa: E402

BOARDS = BOARDS_A + BOARDS_B
OUT_DIR = os.path.join(ROOT, 'figures')

FONT = ('-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",'
        '"Hiragino Sans GB","Microsoft YaHei",sans-serif')
PAD_TOP = 52          # 标题占的高度
PAD_BOT = 46          # 图注占的高度


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def standalone(slug, board, design):
    """把内联 SVG 包成自包含文件：白底 + 标题 + 图 + 图注 + xmlns。"""
    inner = design['scene']()
    m = re.match(r'<svg viewBox="0 0 (\d+) (\d+)"[^>]*>(.*)</svg>$', inner, re.S)
    if not m:
        raise RuntimeError(f'{slug}: 场景 SVG 结构不符合预期')
    w, h = int(m.group(1)), int(m.group(2))
    body = m.group(3)
    H = h + PAD_TOP + PAD_BOT

    title = f'{board["num"]}　{board["title"]}'
    sub = design['headline']
    cap = f'图 {board["num"]}　{design["caption"]}'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" '
        f'width="{w}" height="{H}" font-family=\'{FONT}\'>\n'
        f'  <rect width="{w}" height="{H}" fill="#ffffff"/>\n'
        f'  <text x="30" y="30" font-size="17" font-weight="650" fill="#1c1c1a">{esc(title)}</text>\n'
        f'  <text x="30" y="47" font-size="11.5" fill="#6f6f69">{esc(sub)}</text>\n'
        f'  <line x1="30" y1="{PAD_TOP - 2}" x2="{w - 30}" y2="{PAD_TOP - 2}" '
        f'stroke="#e6e5e0" stroke-width="1"/>\n'
        f'  <g transform="translate(0,{PAD_TOP})">\n{body}\n  </g>\n'
        f'  <line x1="30" y1="{PAD_TOP + h + 10}" x2="{w - 30}" y2="{PAD_TOP + h + 10}" '
        f'stroke="#e6e5e0" stroke-width="1"/>\n'
        f'  <text x="30" y="{PAD_TOP + h + 30}" font-size="11.5" fill="#9a9992">{esc(cap)}</text>\n'
        f'</svg>\n'
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    for b in BOARDS:
        slug = b['slug']
        d = DESIGNS.get(slug)
        if not d:
            print(f'跳过 {slug}：缺少设计数据')
            continue
        svg = standalone(slug, b, d)
        name = f'{b["num"]}-{slug}.svg'
        path = os.path.join(OUT_DIR, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        index.append(dict(
            file=name,
            num=b['num'],
            slug=slug,
            title=b['title'],
            headline=d['headline'],
            caption=d['caption'],
            w=int(m.group(1)), h=int(m.group(2)),
        ))
        print(f'  {name:<32} {len(svg.encode()):>7,} B')

    with open(os.path.join(OUT_DIR, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f'\n共 {len(index)} 张图 → {os.path.relpath(OUT_DIR, ROOT)}/')


if __name__ == '__main__':
    main()
