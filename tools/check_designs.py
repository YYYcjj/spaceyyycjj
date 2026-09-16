# -*- coding: utf-8 -*-
"""九个板块三维设计图的自检脚本。

    python3 tools/check_designs.py

检查两张事（这两类问题肉眼截图都很难发现，必须算）：

    1. 越界：任何标注文字的像素包围盒超出画布；
    2. 重叠：同一个图里两条标注文字互相压在一起。

原理：Iso 内部记录了每条文字的锚点（设计单位）与像素偏移，
auto_fit() 之后就能算出它在画布上的实际矩形。

退出码 0 = 全部通过，1 = 有图不通过。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import iso                                    # noqa: E402
from designs import DESIGNS                   # noqa: E402

ORDER = ['current', 'rocket-tech', 'starship', 'biosphere', 'lightspeed',
         'lifespan', 'contact', 'resources', 'ai-robots']

# 让 Iso 把自身实例记下来，便于拿到 auto_fit 之后的内部状态
_made = []
_orig_init = iso.Iso.__init__


def _patched_init(self, *a, **k):
    _orig_init(self, *a, **k)
    _made.append(self)


iso.Iso.__init__ = _patched_init


def boxes_of(g):
    out = []
    for i, (u, v, dxl, dxr, dyt, dyb) in enumerate(g._txt):
        x = g.ox + u * g.s
        y = g.oy + v * g.s
        out.append((i, x + dxl, y + dyt, x + dxr, y + dyb))
    return out


def main():
    bad = 0
    for slug in ORDER:
        if slug not in DESIGNS:
            print(f'BAD {slug:12} 缺少设计数据')
            bad += 1
            continue
        _made.clear()
        DESIGNS[slug]['scene']()
        g = _made[-1]
        g.auto_fit()
        boxes = boxes_of(g)

        oob = [i for (i, x0, y0, x1, y1) in boxes
               if x0 < 0 or x1 > g.w or y0 < 0 or y1 > g.h]
        ov = []
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                ia, ax0, ay0, ax1, ay1 = boxes[a]
                ib, bx0, by0, bx1, by1 = boxes[b]
                if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                    ov.append((ia, ib))

        ok = not (oob or ov)
        if not ok:
            bad += 1
        print(f'{"OK " if ok else "BAD"} {slug:12} s={g.s:5.2f} 文字{len(boxes):3d}'
              f'  越界{oob}  重叠{ov}')

    print()
    print('总体：', '全部通过' if not bad else f'{bad} 张图有问题')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
