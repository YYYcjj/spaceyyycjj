# -*- coding: utf-8 -*-
"""十张「虚拟视图」：把每个板块的核心装备放进一个虚拟视窗里，看它**跑起来是什么样**。

和另外几类图的分工：

    导览图 / 理论图 / 链路图   解释关系与步骤（静态概念）
    等轴测设计图（iso.py）     看它长什么样（固定角度）
    可旋转模型（models3d.py）  自己转着看（读者操作）
    **虚拟视图（本模块）**      看它**动起来**——运行时的状态、时序、读数

做法是一层「仪表框」加一层场景：

    ┌──────────────────────────────────────────────┐
    │ 虚拟视窗  一号再入与着陆      模拟 · 非实拍   │   ← 眉标（说清这是算出来的，不是照片）
    ├──────────────────────────────────────────────┤
    │              场景（用 dia.py 画）             │
    ├──────────────────────────────────────────────┤
    │ 复用次数 37  │ 翻修周期 21 天 │ …             │   ← 遥测条（4 个读数）
    └──────────────────────────────────────────────┘

**眉标里那句「模拟 · 非实拍」不能省。** 这一层画的是运行状态，很容易被当成实拍图或
实测数据；站点里所有数字都有出处，唯独这类图是我们按公开参数推的，必须写在脸上。

版式与 dia.py 一致：像素坐标、文字包围盒会被 check_figs.py 自检「出框」与「重叠」。
"""

from dia import (Dia, INK, MUTED, FAINT, LINE, LINE_S, GREEN, BLUE, AMBER, RED,
                 GRAY, BLUE_B, GREEN_B, AMBER_B, RED_B, GRAY_B, BLUE_BR,
                 GREEN_BR, AMBER_BR, RED_BR, GRAY_BR)

W, H = 680, 318
FRAME_B = H - 66          # 仪表框下沿（下面留给遥测条）


class VW:
    """一张虚拟视窗。"""

    def __init__(self, tag, title, sub, chips):
        self.g = Dia(W, H)
        self.w, self.h = W, H
        self._txt = self.g._txt          # 让 check_figs.py 的自检能直接用
        self.aria = ''
        self.bx, self.by = 24, 62
        self.bw, self.bh = W - 48, FRAME_B - self.by - 12

        g = self.g
        g.rect(10, 10, W - 20, FRAME_B - 10, '#ffffff', LINE_S, 1.4, 10)
        for (x, y, dx, dy) in ((10, 10, 1, 1), (W - 10, 10, -1, 1),
                               (10, FRAME_B, 1, -1), (W - 10, FRAME_B, -1, -1)):
            g.line(x, y, x + dx * 18, y, LINE_S, 2)
            g.line(x, y, x, y + dy * 18, LINE_S, 2)
        # 场景区底纹（很淡，只为「这是一块屏」的观感）
        for i in range(1, 8):
            xx = self.bx + self.bw * i / 8
            g.line(xx, self.by - 4, xx, self.by + self.bh + 4, '#f1f0ec', 1)
        for i in range(1, 4):
            yy = self.by + self.bh * i / 4
            g.line(self.bx - 4, yy, self.bx + self.bw + 4, yy, '#f1f0ec', 1)
        g.line(10, 48, W - 10, 48, LINE, 1)
        g.line(10, FRAME_B - 10, W - 10, FRAME_B - 10, LINE, 1)

        g.rect(24, 20, 60, 18, GRAY_B, GRAY_BR, 1, 4)
        g.text(54, 33, tag, 10, GRAY, 'middle', 600)
        g.text(94, 33, title, 12.5, INK, weight=600)
        g.text(W - 24, 33, sub, 9.5, FAINT, 'end')

        cw = (self.bw - 12 * (len(chips) - 1)) / len(chips)
        for i, (k, val) in enumerate(chips):
            cx = self.bx + i * (cw + 12)
            g.rect(cx, FRAME_B + 2, cw, 40, '#fafaf8', LINE, 1, 7)
            g.text(cx + 12, FRAME_B + 19, k, 9.5, FAINT)
            g.text(cx + 12, FRAME_B + 36, val, 13.5, INK, weight=600)

    # ---------------------------------------------------------- 转发图元
    def __getattr__(self, name):
        return getattr(self.g, name)

    def svg(self, aria=''):
        return self.g.svg(aria or getattr(self, 'aria', ''))


# ================================================================ 01 一子级回收
def vv_current():
    v = VW('虚拟视窗', '一子级再入与回收 · 高度剖面', '模拟 · 非实拍', [
        ('单枚最高复用', '37 次'),
        ('两次飞行间翻修', '约 21 天'),
        ('再入段控制手段', '气动 + 反推'),
        ('着陆精度', '米 级'),
    ])
    ax = v.bx + 46
    top, bot = v.by + 4, v.by + v.bh - 6
    v.line(ax, top, ax, bot, LINE_S, 1.4)
    # 刻度文字在最上一格会和轴名撞车，所以单位并进最上面那个刻度里，不单独放轴名
    for km, f in ((80, 0.0), (60, 0.25), (40, 0.5), (20, 0.75), (0, 1.0)):
        yy = top + (bot - top) * f
        v.line(ax - 5, yy, ax + 5, yy, LINE_S, 1)
        v.text(ax - 9, yy + 3.5, f'{km} km' if km == 80 else f'{km}',
               9.5, FAINT, 'end')

    # 下降轨迹：越高越快，越到低空越垂直
    pts = [(ax + 16, top + 6), (ax + 96, top + 30), (ax + 186, top + 68),
           (ax + 258, top + 112), (ax + 306, bot - 4)]
    v.curve(pts, BLUE, 2.2)
    for x, y in pts:
        v.dot(x, y, 2.6, BLUE)

    # 标签行高固定 40px：四段里每段都是「一行标题 + 一行说明」，
    # 若跟着轨迹点的 y 走，最上面两段只差 24px，说明行会压住下一段标题（自检抓到过）。
    ev = [('再入点火 · 反推 3 台', 0, '进入大气前先把速度压掉一截'),
          ('栅格舵介入 · 改用气动控制', 1, '这一段发动机不工作，全靠舵面'),
          ('着陆点火 · 中心机节流', 3, '一台中心发动机，节流到 40%'),
          ('触地 · 四条着陆腿已展开', 4, '腿在末段展开，冲击进主结构')]
    for i, (lab, idx, note) in enumerate(ev):
        px, py = pts[idx]
        # 标注贴到轨迹右侧（原来是 bx+150，右半边空了一大块）——引线拉到 278px 的文字栏
        lx = v.bx + 354
        ly = v.by + 14 + i * 40
        v.line(px, py, lx - 8, ly, LINE_S, 0.9)
        v.text(lx, ly + 3.5, lab, 11, INK, weight=600)
        v.text(lx, ly + 17, note, 10, MUTED)
    v.aria = '一子级从再入到着陆的高度剖面与各段控制手段'
    return v


# ================================================================ 02 全功率试车
def vv_engine():
    v = VW('虚拟视窗', '全功率试车 · 稳态段数据', '模拟 · 非实拍', [
        ('室压', '300 bar 级'),
        ('涡轮泵转速', '约 3 万 rpm'),
        ('比冲（真空）', '约 350 s'),
        ('推力调节范围', '40%–100%'),
    ])
    x0, y0 = v.bx + 46, v.by + 26
    cw, ch = v.bw - 60, v.bh - 62
    xs = [f'{t}s' for t in (0, 5, 10, 15, 20, 25, 30)]
    # 三条归一化曲线：室压最大最平，泵转速略滞后，温度先冲高再回落
    v.series(x0, y0, cw, ch, xs, ['100%', '75%', '50%', '25%', '0'],
             [('室压', [0, 0.28, 0.92, 0.98, 1.0, 0.97, 0.02], 'blue', None),
              ('涡轮泵转速', [0, 0.20, 0.86, 0.95, 0.97, 0.94, 0.01], 'amber', '5 3'),
              ('喷管壁温', [0, 0.55, 1.0, 0.88, 0.86, 0.87, 0.05], 'red', '2 3')],
             xname='点火后时间（秒）', ymax=1.12)
    v.text(x0, y0 + ch + 48, '三条曲线各自按满量程归一化；喷管壁温在启动瞬间冲高，'
                             '稳定后回落到材料长期可承受的区间。', 10, MUTED)
    v.aria = '全流量分级燃烧发动机全功率试车时室压、泵转速与壁温的时序曲线'
    return v


# ================================================================ 03 在轨加注
def vv_refuel():
    v = VW('虚拟视窗', '在轨推进剂转移 · 两船对接', '模拟 · 非实拍', [
        ('需要转移量', '数百吨 级'),
        ('对接次数', '多次 · 逐步累积'),
        ('低温推进剂', '需长期零蒸发'),
        ('之前是否需要', '去火星必须要'),
    ])
    cy = v.by + 62
    # 两船：左（目标船）与右（加注船），中间对接
    for (cx, lab, lvl, col) in ((v.bx + 108, '目标船 · 贮箱', 0.22, BLUE),
                                (v.bx + 400, '加注船 · 贮箱', 0.88, AMBER)):
        v.rect(cx - 46, cy - 44, 92, 88, '#ffffff', LINE_S, 1.4, 8)
        v.rect(cx - 34, cy + 26, 68, 12, GRAY_B, GRAY_BR, 1, 3)
        v.rect(cx - 34, cy + 26 - 44 * lvl, 68, 44 * lvl, BLUE_B, col, 1.2, 3)
        v.text(cx, cy - 54, lab, 10.5, MUTED, 'middle')
        v.text(cx, cy + 52, f'液位 {lvl*100:.0f}%', 10.5, col, 'middle', 600)
    v.rect(v.bx + 108 + 46, cy - 12, 400 - 108 - 92, 24, GRAY_B, GRAY_BR, 1, 4)
    v.text(v.bx + 300, cy + 4, '对接机构与低温管路', 10.5, GRAY, 'middle')
    v.arrow(v.bx + 300, cy - 30, v.bx + 300, cy - 52, BLUE, 1.4)
    v.text(v.bx + 300, cy - 58, '推进剂转移方向', 10, BLUE, 'middle')
    v.text(v.bx, v.by + v.bh - 6, '加注完成前不能点火出发——这就是「在轨加注」成为'
                                  '去火星前置条件的原因。', 10, MUTED)
    v.aria = '在轨推进剂转移时两船对接与贮箱液位变化的虚拟视图'
    return v


# ================================================================ 04 闭环生保
def vv_biosphere():
    v = VW('虚拟视窗', '生保闭环 · 三条回路的实际闭合率', '模拟 · 非实拍', [
        ('水回收', '98%'),
        ('氧再生', '约 90%'),
        ('食物闭环', '仍是最弱'),
        ('补给依赖', '未归零'),
    ])
    x0 = v.bx + 4
    y0 = v.by + 10
    rows = [('水', 0.98, 'blue', '冷凝水 + 尿液回收，已经跑到 98%，是唯一接近闭环的一环'),
            ('氧', 0.90, 'green', '电解水制氧 + 二氧化碳还原，剩余靠高压氧瓶补'),
            ('食物', 0.15, 'amber', '温室已能种，但单位体积产量撑不起一个人的热量')]
    for i, (lab, frac, ck, note) in enumerate(rows):
        yy = y0 + i * 60
        col = {'blue': BLUE, 'green': GREEN, 'amber': AMBER}[ck]
        fill = {'blue': BLUE_B, 'green': GREEN_B, 'amber': AMBER_B}[ck]
        br = {'blue': BLUE_BR, 'green': GREEN_BR, 'amber': AMBER_BR}[ck]
        v.text(x0, yy + 12, lab, 12, INK, weight=600)
        bx = x0 + 34
        bw = v.bw - 34 - 92
        v.rect(bx, yy, bw, 18, '#fafaf8', LINE, 1, 4)
        v.rect(bx, yy, max(bw * frac, 4), 18, fill, br, 1, 4)
        v.text(bx + bw + 10, yy + 14, f'{frac*100:.0f}%', 13, col, weight=600)
        v.text(bx, yy + 34, note, 10, MUTED)
    v.text(x0, y0 + 3 * 60 + 4, '三条回路里，只有前两条已经工程化；食物这一环决定'
                                '长期航行仍然要靠补给。', 10, MUTED)
    v.aria = '飞船生保系统水、氧、食物三条回路的闭合率对比'
    return v


# ================================================================ 05 光帆加速
def vv_lightsail():
    v = VW('虚拟视窗', '地面激光阵加速 · 帆面受力', '模拟 · 非实拍', [
        ('目标速度', '0.2c 级'),
        ('加速距离', '需要极长'),
        ('帆面尺寸', '公里 级'),
        ('减速手段', '最难的仍在后面'),
    ])
    # 左：激光阵 → 光束 → 帆
    base = v.by + 66
    v.text(v.bx + 4, v.by + 10, '地面激光阵', 11, INK, weight=600)
    for i in range(6):
        xx = v.bx + 6 + i * 15
        v.rect(xx, base - 22, 11, 22, GRAY_B, GRAY_BR, 1, 2)
    for i, yy in enumerate((base - 30, base - 40, base - 50)):
        v.line(v.bx + 48, base - 11, v.bx + 132, yy, AMBER, 1.6, dash='4 3' if i else None)
    v.text(v.bx + 92, base - 62, '激光束', 10, AMBER, 'middle', 600)
    v.rect(v.bx + 132, base - 62, 5, 54, AMBER, AMBER_BR, 1, 2)
    v.text(v.bx + 148, base - 40, '帆面 · 公里级、克/平方米级', 10.5, MUTED)

    # 右：加速度随距离衰减
    x0, y0 = v.bx + 330, v.by + 22
    cw, ch = v.bw - 340, v.bh - 72
    v.series(x0, y0, cw, ch, ['0.1', '1', '3', '10', '30', '100'], ['1', '0.5', '0'],
             [('加速度（相对）', [1.0, 0.55, 0.30, 0.14, 0.07, 0.03], 'blue', None)],
             xname='距太阳（AU，示意）', yname='加速度', ymax=1.1)
    # 说明必须放回画布左侧：接着 x0 写会越过右边界（755 > 680，自检抓到过）
    v.text(v.bx, v.by + 158, '离太阳越远，光束越散，加速度掉得比直觉快——'
                             '光帆更适合当「出发段」。', 10, MUTED)
    v.aria = '地面激光阵推动光帆的虚拟视图与加速度随距离衰减的曲线'
    return v


# ================================================================ 06 冬眠周期
def vv_hibernation():
    v = VW('虚拟视窗', '冬眠周期 · 体温与代谢', '模拟 · 非实拍', [
        ('降温用时', '数天 级'),
        ('维持时长', '目标 数月至数年'),
        ('代谢抑制', '大幅 下降'),
        ('人体验证', '仍不充分'),
    ])
    x0, y0 = v.bx + 46, v.by + 22
    cw, ch = v.bw - 60, v.bh - 62
    # 体温曲线：37 → 10（数天）→ 长期平台 → 唤醒回到 37
    temp = [37, 30, 20, 13, 10, 10, 10, 10, 10, 10, 11, 22, 33, 37]
    v.series(x0, y0, cw, ch,
             ['0', '1天', '3天', '1周', '1月', '1年', '3年', '5年', '1月', '1周', '3天', '1天', '12h', '0'],
             ['37℃', '28℃', '19℃', '10℃'],
             [('核心体温', temp, 'blue', None)], ymax=40, xname='时间轴（对数示意，两端对称）')
    v.text(x0, y0 + ch + 48, '两条短坡是「降」和「升」，中间那条长平台才是关键：'
                             '低温维持得住，冬眠才成立；维持不住，就只是一次低温麻醉。', 10, MUTED)
    v.aria = '冬眠周期中核心体温随时间变化的示意曲线'
    return v


# ================================================================ 07 巡天与判定
def vv_contact():
    v = VW('虚拟视窗', '巡天观测 · 一个候选信号怎么被判定', '模拟 · 非实拍', [
        ('观测方式', '被动接收'),
        ('已确认的外星信号', '0 个'),
        ('候选被排除的主因', '射频干扰'),
        ('发射（回信）', '伦理问题'),
    ])
    steps = [('收到候选', '窄带、多普勒漂移', 'amber'),
             ('复检', '另一台望远镜同日观测', 'blue'),
             ('排除干扰', '地面雷达 / 手机 / 微波炉', 'gray'),
             ('确认', '目前尚无此步', 'green')]
    v.flow(v.by + 26, steps, x0=v.bx + 4, w=v.bw - 8, bh=52)
    v.text(v.bx + 4, v.by + 104, '关键不在「听」，而在「排除」：绝大多数候选最后'
                                 '都能在地球上找到来源。', 10, MUTED)
    # 右侧频谱示意。位置要错开左下那句说明——两者原来在 y 上只差 1px（自检抓到过）
    bx, by = v.bx + 380, v.by + 96
    v.text(bx, by, '频谱示意', 10.5, INK, weight=600)
    v.text(bx + 60, by - 8, '窄带候选', 10, AMBER)
    v.line(bx, by + 30, bx + 200, by + 30, LINE_S, 1.2)
    for i in range(20):
        hh = 3 + (i * 7 % 11)
        v.line(bx + 5 + i * 10, by + 30, bx + 5 + i * 10, by + 30 - hh, LINE_S, 1.6)
    v.line(bx + 125, by + 30, bx + 125, by - 4, AMBER, 2)
    v.text(bx + 4, by + 46, '天然噪声：宽而低', 10, FAINT)
    v.aria = '射电巡天中一个候选信号从收到到确认的判定流程与频谱示意'
    return v


# ================================================================ 08 采矿作业
def vv_mining():
    v = VW('虚拟视窗', '小行星采矿 · 一次作业的四个阶段', '模拟 · 非实拍', [
        ('拦路的不是物理', '是经济性'),
        ('单次往返周期', '以年 计'),
        ('低重力作业', '难点'),
        ('已有商业采样', '已实现'),
    ])
    # 左：小行星 + 飞船附着
    cx, cy, r = v.bx + 86, v.by + 60, 44
    poly = [(cx + r * 0.98, cy - r * 0.2), (cx + r * 0.55, cy - r * 0.9),
            (cx - r * 0.35, cy - r * 0.95), (cx - r * 0.98, cy - r * 0.15),
            (cx - r * 0.75, cy + r * 0.8), (cx + r * 0.2, cy + r * 0.98),
            (cx + r * 0.9, cy + r * 0.45)]
    v.poly(poly, GRAY_B, GRAY_BR, 1.2)
    v.text(cx, cy + r + 20, '小行星 · 引力几乎可以忽略', 10, MUTED, 'middle')
    v.rect(cx - 34, cy - r - 26, 68, 20, '#ffffff', LINE_S, 1.2, 4)
    v.text(cx, cy - r - 13, '采矿船', 10.5, INK, 'middle', 600)
    v.line(cx, cy - r - 6, cx, cy - r + 4, LINE_S, 1)

    # 右：四阶段
    y0 = v.by + 12
    ph = [('① 绕飞与测绘', '先把形状、自转与成分测清楚', 'blue'),
          ('② 锚定', '低重力下不能「降落」，只能抓住', 'amber'),
          ('③ 采掘与分选', '破碎、抓取、按成分分开', 'gray'),
          ('④ 装舱与返程', '装多少决定这趟划不划算', 'green')]
    for i, (t, n, ck) in enumerate(ph):
        yy = y0 + i * 42
        col = {'blue': BLUE, 'amber': AMBER, 'gray': GRAY, 'green': GREEN}[ck]
        fill = {'blue': BLUE_B, 'amber': AMBER_B, 'gray': GRAY_B, 'green': GREEN_B}[ck]
        br = {'blue': BLUE_BR, 'amber': AMBER_BR, 'gray': GRAY_BR, 'green': GREEN_BR}[ck]
        v.rect(v.bx + 200, yy, v.bw - 204, 34, fill, br, 1, 6)
        v.text(v.bx + 212, yy + 15, t, 11, col, weight=600)
        v.text(v.bx + 212, yy + 29, n, 10, MUTED)
    v.aria = '小行星采矿一次作业的四个阶段与飞船锚定的虚拟视图'
    return v


# ================================================================ 09 延迟下的自主
def vv_autonomy():
    v = VW('虚拟视窗', '同一个故障，两种时间尺度', '模拟 · 非实拍', [
        ('火星单程延迟', '约 20 分钟'),
        ('本机决策耗时', '毫秒–秒 级'),
        ('遥控方案的代价', '延迟即失效'),
        ('抗辐射算力', '真正的天花板'),
    ])
    y1, y2 = v.by + 46, v.by + 122
    for (y, lab, col, fill, br) in ((y1, '方案 A · 本机自主', BLUE, BLUE_B, BLUE_BR),
                                    (y2, '方案 B · 地面遥控', RED, RED_B, RED_BR)):
        v.text(v.bx + 4, y + 14, lab, 11, col, weight=600)
        v.rect(v.bx + 130, y, v.bw - 134, 26, fill, br, 1, 4)
    # A：问题 → 本机决策 → 完成（很短）
    ax = v.bx + 130
    for (x, t) in ((0.02, '发现'), (0.16, '判定'), (0.30, '执行'), (0.44, '完成')):
        xx = ax + (v.bw - 134) * x
        v.dot(xx, y1 + 13, 3.4, BLUE)
        v.text(xx, y1 - 8, t, 10, BLUE, 'middle')
    v.text(ax + (v.bw - 134) * 0.5, y1 + 42, '从发现到处置全部发生在船上，'
                                             '地面事后才知道', 10, MUTED, 'middle')
    # B：问题 → 传回地面 → 等待 → 指令回来 → 执行（很长，且画到框外）
    v.dot(ax, y2 + 13, 3.4, RED)
    v.text(ax, y2 - 8, '发现', 10, RED, 'middle')
    v.arrow(ax + 10, y2 + 13, v.bx + v.bw - 4, y2 + 13, RED, 1.6)
    v.text(v.bx + v.bw - 4, y2 + 30, '等待地面判断 + 指令回传 ≈ 40 分钟',
           10, RED, 'end', 600)
    v.text(ax + (v.bw - 134) * 0.5, y2 + 42, '这 40 分钟里故障还在继续；'
                                             '所以深空必须自主', 10, MUTED, 'middle')
    v.aria = '同一故障在自主方案与遥控方案下时间尺度对比的虚拟视图'
    return v


# ================================================================ 10 在轨组装
def vv_assembly():
    v = VW('虚拟视窗', '在轨组装 · 为什么必须按这个顺序', '模拟 · 非实拍', [
        ('不能一次发射', '超出现有运力'),
        ('对接次数', '多次 · 逐步累积'),
        ('顺序依据', '结构 + 生保 + 能源'),
        ('先装哪一段', '最重的先上'),
    ])
    steps = [('① 推进级', '最重，先上去', 'gray'),
             ('② 贮箱', '在轨加注接口在这', 'blue'),
             ('③ 服务舱', '帆板与散热先到位', 'blue'),
             ('④ 生保舱', '有电有水才敢装人', 'green'),
             ('⑤ 居住舱', '最后装人的部分', 'green'),
             ('⑥ 指令舱', '封顶并接气闸', 'amber')]
    v.flow(v.by + 30, steps, x0=v.bx + 4, w=v.bw - 8, bh=58)
    v.text(v.bx + 4, v.by + 106, '顺序不是设计偏好，是约束推出来的：', 10.5, INK, weight=600)
    for i, t in enumerate(('重的先上 → 结构受力路径才连续；',
                           '在加注接口被封在下面之前，必须先把它装好；',
                           '生保舱要通电通水才能调试，所以能源段要更早；',
                           '住人的舱最后上，否则它会先被别的作业磨坏。')):
        v.text(v.bx + 10, v.by + 126 + i * 17, '· ' + t, 10, MUTED)
    v.aria = '星船在轨组装六个模块的对接顺序与顺序依据'
    return v


# ================================================================ 装配
VIEWS = {
    'current':     dict(make=vv_current,     cap='一子级回收不是「一次点火」的事，'
                                             '而是三种控制手段在三个高度区间接力。'),
    'rocket-tech': dict(make=vv_engine,      cap='全功率试车看的不是某个点的最大值，'
                                             '而是三条曲线在稳态段能不能稳住。'),
    'starship':    dict(make=vv_refuel,      cap='在轨加注的难点不在对接，'
                                             '而在低温推进剂长期不蒸发。'),
    'biosphere':   dict(make=vv_biosphere,   cap='闭环生保里水与氧已经工程化，'
                                             '食物这一环决定长期航行仍要靠补给。'),
    'lightspeed':  dict(make=vv_lightsail,   cap='光帆的加速度随距离迅速衰减，'
                                             '所以它更像「出发段」而不是全程动力。'),
    'lifespan':    dict(make=vv_hibernation, cap='冬眠的成败在中间那条长平台——'
                                             '能不能把低温长期维持住。'),
    'contact':     dict(make=vv_contact,     cap='巡天的瓶颈是排除干扰，'
                                             '不是接收灵敏度。'),
    'resources':   dict(make=vv_mining,      cap='小行星采矿每一步都能做，'
                                             '卡住整条链的是第④步的性价比。'),
    'ai-robots':   dict(make=vv_autonomy,    cap='同一次故障，自主方案以秒计、'
                                             '遥控方案以四十分钟计。'),
    'integration': dict(make=vv_assembly,    cap='在轨组装的顺序由结构、生资与能源'
                                             '三类约束共同决定。'),
}

if __name__ == '__main__':
    for k, spec in VIEWS.items():
        v = spec['make']()
        print(f'  {k:<12} {v.w}×{v.h}  文字 {len(v._txt):3d}')
    print('\n全部生成通过')
