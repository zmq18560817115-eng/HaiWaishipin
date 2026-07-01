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

### 内网更新（开发者 push 之后）

**推送到 GitHub 不会自动改内网。** 内网服务器是独立副本，需要手动拉代码并重启服务。

**开发者（本机）：**

```text
git add …
git commit -m "…"
git push workflow main
```

仓库地址：https://github.com/zmq18560817115-eng/-Overseas-Video-Localization-Workflow

**内网服务器（运维 / 管理员）：**

1. 关闭正在运行的工作台窗口（标题含「本地化工作台-内网」）
2. 在工作区目录执行：

```powershell
cd D:\vl-workflow          # 按实际 clone 路径修改
git pull workflow main
```

3. 若 `requirements.txt` 等有变动，再运行一次 `检查开发环境.cmd`
4. 双击 **`部署内网.cmd`** 重新启动
5. 浏览器访问 `http://<服务器IP>:8788`，确认页面正常（设置页可看版本/健康检查）

**会随 `git pull` 更新：** 页面 UI、后端逻辑、`.cmd` 脚本、`.env.example` 模板。

**不会随 Git 同步（保留在服务器本地）：**

| 路径 | 说明 |
|------|------|
| `overseas-loc-mvp/.env` | API 密钥，每台服务器单独配置 |
| `海外视频本地化MVP/.env` | 内网监听地址、访问 Token |
| `01_素材库/` ~ `05_反馈库/` | 业务数据与成片 |
| `06_备份库/` | 定时备份 |

更新前若有进行中的出片任务，建议等任务结束再重启，避免中断。

**密钥说明：** 同事浏览器访问工作台时**不需要**各自配置 `ARK_API_KEY`；密钥只写在服务器 `overseas-loc-mvp/.env`，由后端统一调用火山方舟。未配置密钥时仍可打开页面，但豆包精细拆解与 AI 出片不可用，脚本会回退规则模板。
