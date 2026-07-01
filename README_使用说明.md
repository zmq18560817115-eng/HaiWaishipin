# 海外视频本地化工作流

日常入口：**双击 `启动工作台.cmd`** → http://127.0.0.1:8788

架构说明见 **`ARCHITECTURE.md`**。

## 核心页面（8788）

| 页面 | 作用 |
|------|------|
| **视频生成** | 产品标签 → 对标爆款 → 脚本预览 → 确认出片 |
| **成稿反馈** | 成稿库、反馈库、闭环约束反哺下一轮生成 |

## 数据目录（唯一写入源）

| 目录 | 内容 |
|------|------|
| `01_素材库/` | 竞品 CSV、AI 拆解、产品资料、脚本快照 |
| `03_产出库/` | 版本化成片（按时间戳归档） |
| `04_成稿库/` | 已交付项目索引 |
| `05_反馈库/` | 审核/投放反馈（闭环数据源） |

工作副本：`overseas-loc-mvp/runs/ref-{id}/`（可被下次重生成覆盖）

## 应用组件

| 目录 | 作用 |
|------|------|
| `海外视频本地化MVP/` | 主工作台（8788） |
| `overseas-loc-mvp/` | 交付引擎（子进程：字幕、zip、SeedDance） |
| `overseas-video-output-standards/` | 出稿 Skill |

## 环境

1. `检查开发环境.cmd` — 检查并自动创建双 venv
2. `overseas-loc-mvp/.env` — `ARK_API_KEY`（豆包拆解 + 脚本生成 + SeedDance）
3. 可选 `ANTHROPIC_API_KEY` — 仅当 `SCRIPT_LLM_PROVIDER=anthropic` 时使用 Claude

## 维护

| 命令 | 作用 |
|------|------|
| `清理工作区.cmd` | 去重路径、删临时文件、建立 junction |
| `本地生成视频.cmd` | 命令行 SeedDance 出片 |
| `运行TikTok抓取工作流.cmd` | 同步竞品元数据（可选） |

## 内网部署（团队）

1. `git clone` 本仓库到服务器（如 `D:\vl-workflow`）
2. `检查开发环境.cmd` — 创建双 venv
3. 复制 `overseas-loc-mvp/.env.example` → `.env`，填写 `ARK_API_KEY`
4. 复制 `海外视频本地化MVP/.env.example` → `.env`，设置 `WORKBENCH_HOST=0.0.0.0` 与 `WORKBENCH_API_TOKEN`
5. 双击 **`部署内网.cmd`**，局域网访问 `http://<服务器IP>:8788`
6. 定期运行 **`备份工作区.cmd`**（数据备份到 `06_备份库/`，已在 .gitignore）

用户可在页面下载成片 zip；服务器同时保留 `03_产出库` 版本归档。
