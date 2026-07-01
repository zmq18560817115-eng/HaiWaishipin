# 海外视频本地化 MVP · 竞品采集与工作台

**TikTok 竞品元数据 → 结构拆解 → 脚本生成 → 交付 zip**

日常入口：根目录 **`启动工作台.cmd`** → http://127.0.0.1:8788

## 用户流程（5 步）

素材库 → 脚本生成（产品 + 标签 + 生成）→ 完成交付 → 成稿库 / 反馈库

| 环节 | 引擎 |
|------|------|
| 发现候选 | Playwright 公开页面低频发现 URL → discovery_candidates |
| 同步 TikTok | oEmbed + Playwright |
| 结构拆解 | 豆包视频理解（`ARK_API_KEY`）+ 规则兜底 |
| 生成脚本 | 豆包（默认，共用 `ARK_API_KEY`）→ Claude → 规则模板 |
| 完成交付 | `overseas-loc-mvp` 子进程 |
| AI 空镜 | SeedDance 2.0 / fal.ai（`FAL_KEY`，可选） |

## 命令行（设置页可代替）

```bat
运行.cmd discover --limit-per-query 20
运行.cmd promote --limit 20
运行.cmd fetch
运行.cmd decompose      :: 结构拆解 → video_analysis
运行.cmd templates
运行.cmd products
运行.cmd bridge --id 19
```

## 目录

```
海外视频本地化MVP/
├── 启动页面.cmd          # 开发用，由 启动工作台.cmd 调用
├── .env.example
├── 数据表/               # CSV 数据源
├── web/                  # 8788 前端
├── app/                  # 8788 后端
└── scripts/pipeline.py
```

知识库配置：根目录 `config/knowledge-sources.json`

豆包详细视频分解接入说明见：`docs/豆包详细视频分解接入指南.md`。
## TikTok 抓取工作流入口

为了让本地工作台、命令行、Cursor 共用同一套本地文件入口，已固定提供：

- 统一脚本：`scripts/tiktok_workflow.py`
- 根目录命令包装：`..\运行TikTok抓取工作流.cmd`
- 工作台 API：
  - `GET /api/tiktok-collector/db/videos`
  - `POST /api/tiktok-collector/db/sync`
  - `POST /api/tiktok-collector/collect`

推荐命令：

```powershell
cd 海外视频本地化MVP
.\.venv\Scripts\python.exe scripts\tiktok_workflow.py status
.\.venv\Scripts\python.exe scripts\tiktok_workflow.py collect-sync --keywords "wearable breast pump" "baby bottle" --limit 10 --headless false --manual-verify-wait-sec 180
.\.venv\Scripts\python.exe scripts\tiktok_workflow.py query-db --q "wearable breast pump" --limit 10
.\.venv\Scripts\python.exe scripts\tiktok_workflow.py sync-db --q "wearable breast pump" --limit 10
```

如果让 Cursor 接手，优先让它调用这一条：

```powershell
C:\Users\bu\Documents\海外视频本地化工作流\海外视频本地化MVP\.venv\Scripts\python.exe C:\Users\bu\Documents\海外视频本地化工作流\海外视频本地化MVP\scripts\tiktok_workflow.py collect-sync --keywords "wearable breast pump" "manual breast pump" "baby bottle" --limit 10 --headless false --manual-verify-wait-sec 180
```

这条链路会按当前工作流逻辑执行：

`TikTok 搜索抓取 -> JSON/CSV 导出 -> MySQL 去重入库 -> clean 结果同步到 workflow CSV 素材库`
