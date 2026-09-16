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
assets/site.css               设计系统（含移动端卡片化）
assets/site.js                交互脚本（无依赖）
tools/build.py                站点生成器
tools/content_a.py            板块 1-5 内容
tools/content_b.py            板块 6-9 内容
tools/chains.py               九个板块的「技术链路」数据
tools/board01_body.html       板块一正文（由早期单页报告抽取，一次性素材）
tools/board01_toc.json        板块一目录条目
.github/workflows/pages.yml   GitHub Pages 部署工作流
.nojekyll                     关闭 Jekyll 处理
```

## 重新生成

```bash
python3 tools/build.py
```

站点是「内容即数据」结构：板块内容写在 `tools/content_a.py` / `content_b.py`，
技术链路写在 `tools/chains.py`，由 `tools/build.py` 生成 `index.html` 与 `sections/*.html`。
改内容只改 Python 数据文件，不要手改生成的 HTML。

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
