# Agent 指引

## 入口

`启动工作台.cmd` → http://127.0.0.1:8788

架构：`ARCHITECTURE.md`

## 出稿 Skill（必用）

`overseas-video-output-standards/` + `.cursor/rules/overseas-video-output-standards.mdc`

**产品外观**：`主图/白底主图.png` 为 SeedDance 默认垫图。Git：**本机 push，内网只 pull**（见 `README_使用说明.md`）。

## 数据（勿写 legacy 路径）

| 路径 | 用途 |
|------|------|
| `01_素材库/` | 竞品、产品、脚本快照 |
| `03_产出库/` | 成片版本 |
| `04_成稿库/` | 成稿索引 |
| `05_反馈库/` | 反馈闭环 |
| `overseas-loc-mvp/runs/` | 当前工作副本 |

## 验证

```powershell
cd 海外视频本地化MVP
.\.venv\Scripts\python.exe scripts\validate_output_standards_skill.py
```
