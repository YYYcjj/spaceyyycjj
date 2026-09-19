# -*- coding: utf-8 -*-
"""技术路线配图的自检：文字出框 + 互相重叠。

    python3 tools/check_figs.py

45 张图不可能靠肉眼逐张看，所以算：每张图里所有标注文字的实际像素矩形，
两两求交。两类问题截图都很难发现（尤其「出框」——SVG 会直接裁掉，看不见缺了什么）。

同时覆盖两种图：
    Iso  记录的是设计单位锚点 + 像素偏移，auto_fit() 之后才能换算
    Dia  记录的直接是像素坐标

退出码 0 = 全部通过，1 = 有图不通过。加 --list 可以只列出图名与尺寸。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import iso                                     # noqa: E402
from techfigs import FIGS                      # noqa: E402
from synthfigs import SYNTH_FIGS               # noqa: E402

# 所有图都过一遍同一套断言。新增图集时挂到这里就行，不用改下面的逻辑。
REGISTRIES = [('tech', FIGS), ('synth', SYNTH_FIGS)]


def _boxes(obj):
    """返回 (文字包围盒列表, 画布宽, 画布高)。"""
    if isinstance(obj, iso.Iso):
        obj.auto_fit()
        out = []
        for i, (u, v, dxl, dxr, dyt, dyb) in enumerate(obj._txt):
            x = obj.ox + u * obj.s
            y = obj.oy + v * obj.s
            out.append((i, x + dxl, y + dyt, x + dxr, y + dyb))
        return out, obj.w, obj.h
    return [(i, a, b, c, d) for i, (a, b, c, d) in enumerate(obj._txt)], obj.w, obj.h


def _overlaps(boxes):
    out = []
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            _ia, ax0, ay0, ax1, ay1 = boxes[a]
            _ib, bx0, by0, bx1, by1 = boxes[b]
            if ax0 < bx1 - 0.5 and bx0 < ax1 - 0.5 and ay0 < by1 - 0.5 and by0 < ay1 - 0.5:
                out.append((_ia, _ib))
    return out


def main():
    listing = '--list' in sys.argv
    bad = 0
    for tag, registry in REGISTRIES:
        if len(REGISTRIES) > 1:
            print(f'--- {tag} ---')
        for key in sorted(registry):
            spec = registry[key]
            try:
                obj = spec['make']()
            except Exception as e:                              # noqa: BLE001
                print(f'BAD {key:8} 生成失败：{type(e).__name__}: {e}')
                bad += 1
                continue
            boxes, w, h = _boxes(obj)
            if listing:
                print(f'    {key:8} {w}×{h}  文字 {len(boxes)}')
                continue
            oob = [i for (i, x0, y0, x1, y1) in boxes
                   if x0 < 0 or x1 > w or y0 < 0 or y1 > h]
            ov = _overlaps(boxes)
            ok = not (oob or ov)
            if not ok:
                bad += 1
            print(f'{"OK " if ok else "BAD"} {key:8} {w}×{h} 文字{len(boxes):3d}'
                  f'  出框{oob}  重叠{ov}')
    if not listing:
        print()
        print('总体：', '全部通过' if not bad else f'{bad} 张图有问题')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
