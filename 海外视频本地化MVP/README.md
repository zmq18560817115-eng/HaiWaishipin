# 海外视频本地化 MVP · 竞品采集

**收集母婴 TikTok 竞品 → AI 拆解 → 爆款模板 → 产品资料 → 送进本地化 MVP**

## 整条流程（2 步）

| 步骤 | 做什么 | 得到什么 |
|------|--------|----------|
| 1 | 竞品库选视频 → **生成并去出稿** | 自动跳转出稿页 |
| 2 | 出稿页点 **完成交付** | 七项脚本包 + 字幕 + SeedDance 空镜（zip） |

**交付脚本包七项**：标题 · 副标题 · 20秒口播 · 分镜 · 字幕文案 · 画面提示词 · SeedDance Prompt

```bat
启动工作台.cmd
```

中间过程（拆解、英文稿、合规扫描）全自动，**不用管其它文件**。

## 两条线（不要混）

| 线 | 给谁 | 产出 | 页面 |
|---|---|---|---|
| **实拍交付** | 剪辑 / 拍摄 | zip：`交付脚本包.md/json` + `剪辑单.html` + `subtitles.srt` | 8787 主按钮 |
| **Step 6 AI 空镜**（可选） | 剪辑补 B-roll | `broll/shot-N.mp4` | 8787 底部，仅 AI 镜出现 |

Step 6 需外接 **fal.ai SeedDance 2.0**：

```bat
配置SeedDance.cmd    :: 填写 FAL_KEY 并测试连接
重启出海出稿.cmd
```

链路：`脚本 Prompt → fal.ai SeedDance → broll/shot-N.mp4`（不进交付 zip）

## Step 7 成稿库 + 反馈库

每次点 **生成交付包** 自动写入：

| 库 | 路径 | 内容 |
|---|---|---|
| **成稿库** | `成稿库/成稿索引.csv` | 生成脚本、视频、模板、产品资料、交付文件 |
| **反馈库** | `反馈库/反馈记录.csv` | 人工修改、是否采纳、投放数据（出稿页可填） |

这些数据后续可反哺模型训练。

## Step 5 大模型生成脚本包

**输入**：产品资料 + 爆款结构模板 + 参考视频拆解 + 目标国家/语言/风格  
**输出**（`生成脚本/{id}/script-pack.json`）：

| 字段 | 说明 |
|------|------|
| title | 标题 |
| subtitle | 副标题 |
| voiceover_20s | 20 秒口播脚本 |
| storyboard | 分镜脚本（5 镜） |
| subtitle_copy | 字幕文案 |
| visual_prompts | 画面提示词 |
| seedance_prompts | SeedDance 2.0 视频生成提示词 |

配置 `ANTHROPIC_API_KEY` 后走 Claude；未配置时自动用规则模板兜底。

## Step 4 本地 Web MVP

三栏页面：**左侧筛选**（产品/品类/关键词）→ **中间素材列表** → **右侧 AI 拆解 + 一键生成脚本**

```bat
启动页面.cmd    :: http://127.0.0.1:8788
```

功能：素材列表、素材详情、AI 拆解结果（8 字段）、一键生成新脚本（并自动 bridge 到本地化 MVP）

## 知识库（KRO Skill）

已装载 [Knowledge Research Orchestrator](file:///C:/Users/bu/Downloads/knowledge-research-orchestrator-codex-shareable/knowledge-research-orchestrator/SKILL.md)，关联：

| 来源 | 路径 |
|------|------|
| 公司 NAS | `\\DS223\obsidian知识库` |
| KRO 脚本 | `Downloads\knowledge-research-orchestrator-codex-shareable\...` |
| 配置文件 | `config/knowledge-sources.json` |

```bat
运行.cmd knowledge                    :: 列出知识来源
运行.cmd knowledge "熊猫布布 吸奶器"   :: 检索 DS223
```

## 目录

```
海外视频本地化MVP/
├── 运行.cmd
├── .env                          ← KRO + DS223 路径
├── config/knowledge-sources.json
├── 数据表/
│   ├── raw_links.csv
│   ├── videos_meta.csv
│   ├── video_analysis.csv        ← 单条拆解（8字段）
│   ├── script_templates.csv      ← 爆款结构模板
│   └── product_materials.csv     ← 产品资料库（8字段）★
├── script_templates/
├── 产品资料/
└── scripts/pipeline.py
```

## 流水线

```bat
运行.cmd links
运行.cmd fetch
运行.cmd decompose      :: → video_analysis
运行.cmd templates      :: → script_templates
运行.cmd products       :: → product_materials（从 DS223 同步）
运行.cmd bridge --id 19
```

### product_materials 八个字段

产品名称、适用人群、核心卖点、用户痛点、使用场景、禁用词/风险表述、价格区间、竞品参考

### 前置条件

- 连接公司内网，确保 `\\DS223\obsidian知识库` 可打开
- DS223 离线时，`products` 会使用 `overseas-loc-mvp/knowledge/` 本地镜像兜底

## MVP 页面

`bridge` 后打开根目录 **启动页面MVP.cmd**，选 `ref-019` 继续 Step 3–6（Step 3 知识检索也会走 DS223）。
