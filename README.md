# 宇宙航行全景 · 2026 年 9 月

一个九板块的静态站点：从一枚已经复用 37 次的猎鹰 9，一直问到光速飞船、冬眠舱和星际通信。

每个板块都尽量把三件事分开写清：**已经做到的**、**正在验证的**、**还只在纸上的**。

## 线上地址

- https://yyycjj.github.io/spaceyyycjj/

## 九个板块

| # | 板块 | 主题 | 一句话 |
|---|---|---|---|
| 01 | [目前航天技术发展](sections/01-current.html) | Current State | 可回收火箭的真实格局：一超多强，中国完成 0→1 未完成 1→N |
| 02 | [航天火箭技术](sections/02-rocket-tech.html) | Rocket Engineering | 化学推进的比冲天花板已经摸到，能压的只剩结构质量与翻修成本 |
| 03 | [星舰建造与技术](sections/03-starship.html) | Starship & Deep Space | 完全复用 + 在轨加注，去火星之前必须跨过的两道坎 |
| 04 | [飞船生态圈](sections/04-biosphere.html) | Ship Biosphere | 闭环生保：ISS 水回收已到 98%，食物闭环仍然最弱 |
| 05 | [飞船速度提升到光速发展](sections/05-lightspeed.html) | Interstellar Propulsion | 光帆目标 0.2c，但加速容易减速难 |
| 06 | [人类寿命延长与冬眠](sections/06-lifespan.html) | Longevity & Hibernation | 冬眠在动物身上成立，在人身上还只是临床试验 |
| 07 | [与外星人交流](sections/07-contact.html) | SETI & Alien Contact | 我们已经在听，但还没听到；发射本身是一个伦理问题 |
| 08 | [宇宙资源获取](sections/08-resources.html) | Cosmic Resources | 小行星采矿：物理学不拦路，经济学拦路 |
| 09 | [飞船 AI 智能与机器人](sections/09-ai-robots.html) | Autonomy & Robotics | 20 分钟通信延迟决定了深空必须自主，抗辐射是算力天花板 |

## 文件结构

```
index.html                    首页：九个板块总览 + 首屏 KPI
sections/01-current.html      … 09-ai-robots.html   九个板块页
figures/01-current.svg        … 09-ai-robots.svg   各板块的三维设计图（独立矢量文件）
figures/index.json            图片清单（文件名 / 标题 / 图注 / 尺寸）
assets/site.css               设计系统（含移动端卡片化）
assets/site.js                交互脚本（无依赖）
tools/build.py                站点生成器
tools/content_a.py            板块 1-5 内容
tools/content_b.py            板块 6-9 内容
tools/chains.py               九个板块的「技术链路」数据
tools/costs.py                九个板块的「要花多少钱」数据
tools/designs.py              九个板块的「具体设计」数据 + 三维等轴测场景
tools/ventures.py             九个板块的「创业者路线图」数据
tools/iso.py                  等轴测（isometric）SVG 生成器
tools/check_designs.py        设计图自检（文字越界 / 互相重叠）
tools/export_figures.py       把九张图导出成独立的 figures/*.svg
tools/board01_body.html       板块一正文（由早期单页报告抽取，一次性素材）
tools/board01_toc.json        板块一目录条目
.github/workflows/pages.yml   GitHub Pages 部署工作流
.nojekyll                     关闭 Jekyll 处理
```

## 重新生成

```bash
python3 tools/build.py            # 生成 index.html 与 sections/*.html
python3 tools/check_designs.py    # 设计图自检
python3 tools/export_figures.py   # 导出 figures/*.svg（改了图之后要重跑）
```

注意：页面里每张图的右下角有一个「打开矢量原图（SVG）」链接，指向 `../figures/NN-slug.svg`。
**改了 `designs.py` 里的图之后必须重跑 `export_figures.py`**，否则页面上的图和下载到的原图会不一致。

站点是「内容即数据」结构：板块内容写在 `tools/content_a.py` / `content_b.py`，
技术链路写在 `tools/chains.py`，成本写在 `tools/costs.py`，具体设计写在 `tools/designs.py`，
创业者路线图写在 `tools/ventures.py`，
由 `tools/build.py` 生成 `index.html` 与 `sections/*.html`。
**改内容只改 Python 数据文件，不要手改生成的 HTML。**

新增一类内容的标准做法：**放一个新模块，用 slug 挂载**，不要动 `content_*.py`。
`build.py` 里统一挂并在导入时断言，漏配会在构建时直接报错：

```python
for _b in BOARDS:
    _b['chain']  = CHAINS.get(_b['slug'])
    _b['cost']   = COSTS.get(_b['slug'])
    _b['design'] = DESIGNS.get(_b['slug'])
    assert _b['chain'] and _b['cost'] and _b['design'], f'板块 {_b["slug"]} 数据缺失'
```

## 技术链路

每个板块页开头都有一条「技术链路」，回答两件事：**这个领域最先进的方法是什么**，
以及**它具体可以怎样实现**。

- **最先进的方法**：每个板块点名一种前沿方案（例：板块五是「激光推进光帆」，
  板块八是「近地小行星原位资源利用」），并说明它和别的路线差在哪。
- **技术链路**：把该方案拆成 6 个必须按顺序打通的环节，每个环节写清**怎么实现**——
  工程手段、关键参数、需要突破的点。
- **成熟度标注**：每个环节标出当前状态（**已实现 / 在验证 / 待突破 / 物理约束 / 仅纸上**），
  方便一眼看出哪些是工程问题、哪些是物理上就改不了的。
- **最难的一环**：点明这 6 环里哪一环最决定成败，以及为什么。

`tools/chains.py` 里每个板块的字段：

```python
"slug": dict(
    frontier="这个领域最先进的方法",
    lead="为什么这条路线算最先进",
    nodes=[dict(t="环节名", s="成熟度", how="具体怎么实现")],   # 固定 6 环
    bottleneck="最难、也最决定成败的那一环",
)
```

成熟度取值只能是 `done` / `run` / `hold` / `lock` / `plan`，
构建时会校验环数必须为 6、成熟度取值必须合法。

## 要花多少钱

每条技术链路后面都跟一张成本表，按 slug 从 `tools/costs.py` 取：

```python
"slug": dict(
    items=[dict(t="项目", a="金额", n="口径与说明")],
    scale="整条链路的总量级（一句话）",
    note="口径提醒：金额来源、区间、汇率换算依据",
)
```

口径约定：

- 金额单位统一为**美元**，因为原始来源全部是美元计价；只在有实际参考意义时才给人民币换算
  （按约 7.2 元人民币/美元）。
- 同一项目不同来源差异可能达到数倍，**凡有区间的一律给区间，不取单点值**；
  报价（牌价）与成本（边际成本）必须分列，不能混为一谈。
- 成本表用 `table.cost`，它的列宽只在 `min-width:641px` 生效——
  写进移动端会覆盖卡片化的 `td{width:100%}`，把卡片压窄。

## 具体设计

每个板块在技术链路与成本之后，还有一节「具体设计」：**这个最先进的方法具体怎么做**。

- **三维等轴测图**：`tools/iso.py` 是自写的等轴测投影器（把 3D 长方体 / 圆柱 / 圆台投影成
  矢量 SVG），九张图共用同一套几何与配色。矢量图可打印、无外部依赖，比位图渲染更适合工程示意。
- **设计参数表**：7 行，每行给「参数 / 取值 / 为什么是这个值」——只有数值没有理由的表没有意义。
- **设计分解**：子系统 → 做什么、关键指标。

`tools/designs.py` 里每个板块的字段：

```python
"slug": dict(
    headline="设计目标（一句话）",
    specs=[dict(k="参数", v="取值", n="为什么是这个值")],
    subs=[dict(t="子系统", n="做什么 / 关键指标")],
    scene=<返回 SVG 的函数>,      # 用 iso.py 搭
    caption="图的说明（放 figcaption，不要画进 SVG）",
    note="设计说明：取舍、不确定性",
)
```

### 画等轴测图的几条硬规矩（改图前必读）

1. **只有 (x − y) 不同才会左右分开。** 坐标是 `u = (x−y)·cos30`、`v = (x+y)·sin30 − z`。
   把两台泵写成 `(±34, ±34)`，它们的 x − y 都是 0，会在屏幕中轴上叠成一个。
   要横向铺开就固定 `y = 0`、只变 `x`。
2. **标注一律往屏幕水平方向延伸。** 用 `roff(p, d)` / `loff(p, d)` 按物体坐标算锚点，
   别手填 `R()` / `L()`——手填很容易让文字压在别的物体上。
3. **同一侧的标注要让 `v` 彼此拉开 ≥18 个单位**，否则文字会叠在一起。
4. **长句一律放 `caption`**，不要 `g.note()` 画进 SVG：SVG 里的文字无法自动换行，长了就被裁。
5. 画完必须跑自检（同时报「文字出框」和「文字互相重叠」）：

```bash
python3 tools/check_designs.py
```

自检比肉眼看可靠得多——本轮的三个 bug（缩放只会缩不会放、缩放解漏掉右边缘约束、
三条左侧标注 `v` 相同叠在一起）全都是它先发现的，截图上看不出来。

## 创业者路线图

每个板块最后还有一节「创业者路线图」：**如果要从零做这件事，该怎么一步步走**。

- **切入点**：一句话给出最适合新公司的位置。
- **五个阶段**：每阶段有 `阶段名 / 时间量级 / 做什么 / 里程碑 / 这一步的死法`。
  「死法」是必备字段——只说该做什么、不说会在哪里死的路线图没有价值。
- **最该避免的事**：这个方向最常见的错误下注。

`tools/ventures.py` 里每个板块的字段：

```python
"slug": dict(
    entry="切入点（一句话）",
    lead="为什么从这里切，而不是从最显眼的地方切",
    steps=[dict(p="阶段名", w="时间量级", do="做什么", mile="里程碑", risk="这一步的死法")],
    avoid="最该避免的事",
    note="口径提醒",
)
```

**内容立场（写内容时守住，别写成招商广告）**：

1. 优先推荐上下游的**耗材 / 检测 / 软件 / 服务**，而不是整机与总体——
   整箭、整发动机、整星都是国家级资本与十年周期的游戏，新公司进不去。
2. 没有商业路径的方向（光速推进、人体冬眠）**直接说「这不是创业赛道」**，
   然后给出真正能做的使能技术。宁可劝退，不要给人虚假希望。
3. 每一步都要写「死法」。
4. 「地面收入养航天研发」是出现频率最高的可行结构——
   航天客户预算大但节奏极慢，纯航天定位的公司活不到量产。

## 技术说明

- 纯静态：无运行时依赖、无 CDN 引用，图表为手写内联 SVG
- 桌面端：左侧粘性目录（板块 + 当前板块小节）+ 滚动高亮 + 顶部阅读进度条
- 移动端（<640px）：侧栏隐藏、顶部切换为横向胶囊导航、表格自动转为卡片式（`td::before` 带字段名）
- 每个板块页底部有上一/下一板块导航
- 部署：推送 `main` 由 GitHub Actions 发布到 GitHub Pages

## 数据来源

SpaceX 官网与飞行记录、NASA / ESA / ISRO 公开资料、FAA 发射通告、国家航天局通报，
以及 The Astronomical Journal、Nature、Science、《Aging》等期刊论文与各企业公开披露。

整理日期：2026-09-15。本仓库仅为公开信息整理，不构成任何投资建议。
