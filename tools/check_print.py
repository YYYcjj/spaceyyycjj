#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印质量检查：把导出的 PDF 逐页量一遍，抓两类「屏幕上永远看不到」的缺陷。

    python3 tools/check_print.py <PDF 路径> [更多 PDF…]

先用 tools/make_pdf.js 导出 PDF：

    NODE_PATH=<node-workspace>/node_modules node tools/make_pdf.js <URL> /tmp/p.pdf

依赖 pymupdf（可选，只在跑这个检查时需要）：

    /Users/yyy/.workbuddy/binaries/python/envs/default/bin/pip install pymupdf

## 为什么需要它

报告类站点的用途之一是打印/发 PDF，但**分页是在导出那一刻才决定的**：
浏览器里的截图、DOM 断言、对比度检查全都看不到分页断在哪里。实测抓到过两类问题：

1. **页底残留的空盒子**：卡片被页边切开时，上一页只剩一个空框的圆角顶边。
   修法是给这类「矮卡片」加 `break-inside:avoid`（实测不加会让首页多出两个空框，
   加上之后页数不变）。
2. **图形被页边切断**：图表横跨两页。

⚠️ 注意误报：`break-inside:avoid` 把一个盒子搬到下一页时，
**盒子的边框可能被画在上一页的页边距区域**（y 落在底部留白里）。
那部分在纸上不可见，不算缺陷——所以判定要排除「起点已经在内容区之下」的图形。

## 两个判据

- `cut`  ：图形从内容区内越出页面下沿 → 真的被切断。
- `open` ：图形位于页面底部、高度很小、宽度很大、且其内部没有文字 → 页底残留的空盒子。
"""
import sys

try:
    import pymupdf
except ImportError:
    print('缺少 pymupdf：pip install pymupdf（只需跑这个检查时安装）')
    raise SystemExit(2)

# 与 tools/make_pdf.js 里的页边距保持一致（14mm ≈ 39.7pt）
MARGIN = 39.7


def analyse(path):
    doc = pymupdf.open(path)
    pages = doc.page_count
    areas, cuts, opens, thin = [], [], [], []

    for i, page in enumerate(doc, 1):
        H, W = page.rect.height, page.rect.width
        content_bottom = H - MARGIN
        content_left, content_right = MARGIN, W - MARGIN
        content_w = content_right - content_left

        # 页内所有文字行（用来判断一个盒子里有没有内容）
        lines = []
        for blk in page.get_text('dict')['blocks']:
            if blk.get('type') != 0:
                continue
            for ln in blk['lines']:
                if ''.join(s['text'] for s in ln['spans']).strip():
                    lines.append(ln['bbox'])

        bottom = 0.0
        for d in page.get_drawings():
            r = d['rect']
            if r.width < 3 or r.height < 3:
                continue
            if r.y1 <= H + 1:
                bottom = max(bottom, min(r.y1, H))
            # ① 从内容区内越出页下沿 / 页上沿 → 被切断
            if r.y1 > H + 1 and r.y0 < content_bottom - 2:
                cuts.append((i, round(r.y0), round(r.y1 - H), round(r.width)))
            if r.y0 < -1 and r.y1 > MARGIN + 2:
                cuts.append((i, 'top', round(r.y1), round(r.width)))
            # ② 页底残留的空盒子
            if (r.height < 60 and r.width > content_w * 0.4
                    and content_bottom - 12 < r.y1 <= H
                    and not any(ln[1] > r.y0 and ln[3] < r.y1 + 1 and ln[0] < r.x1 and ln[2] > r.x0
                                for ln in lines)):
                opens.append((i, round(r.y0), round(r.height), round(r.width)))
        for ln in lines:
            bottom = max(bottom, ln[3])
        areas.append(bottom / H)

        # 末页天然可能只占一点（文档结尾），不算缺陷
        if i < pages and len(page.get_text().strip()) < 200 and len(page.get_drawings()) < 12:
            thin.append(i)

    body = areas[:-1] or areas
    fill = sorted(body)[len(body) // 2]
    doc.close()
    return dict(pages=pages, fill=fill, low=sum(1 for a in body if a < .75),
                thin=thin, cuts=cuts, opens=opens)


def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        raise SystemExit(2)

    bad = 0
    for path in paths:
        r = analyse(path)
        print(f'{path}')
        print(f'  {r["pages"]} 页 | 填充率中位数 {r["fill"] * 100:.0f}% | '
              f'低于 75% 的页 {r["low"]} 个 | 近乎空白页 {len(r["thin"])} 个 {r["thin"] or ""}')
        if r['cuts']:
            bad += 1
            print(f'  ✗ 被页边切断的图形 {len(r["cuts"])} 处：{r["cuts"][:5]}')
        else:
            print('  ✓ 没有图形被页边切断')
        if r['opens']:
            bad += 1
            print(f'  ✗ 页底残留的空盒子 {len(r["opens"])} 处：{r["opens"][:5]}')
        else:
            print('  ✓ 页底没有残留的空盒子')
        if r['thin']:
            bad += 1
            print(f'  ✗ 近乎空白的页：{r["thin"]}')
        else:
            print('  ✓ 没有近乎空白的页')
        print()

    print('==> ' + ('打印检查全部通过' if not bad else f'{bad} 个 PDF 有问题'))
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
