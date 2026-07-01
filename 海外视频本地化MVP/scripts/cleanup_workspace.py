"""工作区瘦身：去重数据路径、清理与主流程无关的临时/测试产物。

用法:
  python scripts/cleanup_workspace.py --dry-run
  python scripts/cleanup_workspace.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent

if str(MVP_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MVP_ROOT / "scripts"))

from ensure_legacy_paths import ensure_legacy_junctions, replace_legacy_dirs_with_junctions  # noqa: E402

JUNK_GLOBS = (
    WORKFLOW_ROOT / "temp",
    WORKFLOW_ROOT / "logs",
)

JUNK_FILES = (
    WORKFLOW_ROOT / "CODEX_接管核查.md",
)

ROOT_DEMO_CMDS = (
    WORKFLOW_ROOT / "演示流程视频.cmd",
    WORKFLOW_ROOT / "演示长视频.cmd",
    WORKFLOW_ROOT / "工作流试运行.cmd",
    WORKFLOW_ROOT / "端到端测试.cmd",
    WORKFLOW_ROOT / "启动页面MVP.cmd",
)

ROOT_REDUNDANT_CMDS = (
    WORKFLOW_ROOT / "安装并检查开发环境.cmd",
    WORKFLOW_ROOT / "整理工作区目录.cmd",
    WORKFLOW_ROOT / "打开工作流文件夹.cmd",
    WORKFLOW_ROOT / "归档MVP产出.cmd",
)

DEPRECATED_DIRS = (
    WORKFLOW_ROOT / "overseas-loc-mvp" / "static",
)


def _remove_path(path: Path, *, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if dry_run:
        print(f"  [dry-run] remove {path.relative_to(WORKFLOW_ROOT)}")
        return True
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"  removed {path.relative_to(WORKFLOW_ROOT)}")
    return True


def clean_temp_and_logs(*, dry_run: bool) -> int:
    n = 0
    for folder in JUNK_GLOBS:
        if not folder.is_dir():
            continue
        for item in folder.iterdir():
            if item.name == ".gitkeep":
                continue
            if _remove_path(item, dry_run=dry_run):
                n += 1
    for f in JUNK_FILES:
        if _remove_path(f, dry_run=dry_run):
            n += 1
    archive = WORKFLOW_ROOT / "03_产出库"
    if archive.is_dir():
        for p in archive.glob("batch-scenario-*.json"):
            if _remove_path(p, dry_run=dry_run):
                n += 1
    return n


def clean_demo_launchers(*, dry_run: bool) -> int:
    n = 0
    for cmd in (*ROOT_DEMO_CMDS, *ROOT_REDUNDANT_CMDS):
        if _remove_path(cmd, dry_run=dry_run):
            n += 1
    legacy_bat = WORKFLOW_ROOT / "overseas-loc-mvp" / "start.bat"
    if _remove_path(legacy_bat, dry_run=dry_run):
        n += 1
    return n


def clean_deprecated_ui(*, dry_run: bool) -> int:
    n = 0
    for d in DEPRECATED_DIRS:
        if _remove_path(d, dry_run=dry_run):
            n += 1
    return n


def write_architecture_readme(*, dry_run: bool) -> None:
    path = WORKFLOW_ROOT / "ARCHITECTURE.md"
    body = """# 本地部署架构（精简）

## 运行链路

```
启动工作台.cmd
  └─ 海外视频本地化MVP (8788) — UI + 素材/脚本/成稿/反馈 API
        ├─ 01_素材库 — 竞品 CSV、拆解、产品图、脚本快照
        ├─ 04_成稿库 / 05_反馈库 — 交付索引与闭环反馈
        ├─ 03_产出库 — 版本化成片归档
        └─ subprocess → overseas-loc-mvp — 字幕、zip、SeedDance、合规
              └─ runs/ref-{id}/ — 当前工作副本
```

## 必留目录

| 路径 | 作用 |
|------|------|
| `海外视频本地化MVP/` | 主工作台 + `.venv` |
| `overseas-loc-mvp/` | 交付引擎 + `.venv` + `runs/` + `.env` |
| `01_素材库/` | 全部业务素材与脚本快照 |
| `03_产出库/` | 历史成片版本 |
| `04_成稿库/` | 成稿索引 |
| `05_反馈库/` | 反馈闭环数据 |
| `overseas-video-output-standards/` | 出稿 Skill |
| `config/` | 知识库与豆包配置示例 |
| `tiktok_collector/` | TikTok 同步（可选） |

## 兼容联接（自动）

旧路径 `数据表/`、`成稿库/` 等为 **junction** 指向 `01_*` / `04_*` / `05_*`，启动 8788 时自动创建。

## 根目录命令

| 命令 | 作用 |
|------|------|
| `启动工作台.cmd` | 日常入口 |
| `检查开发环境.cmd` | 检查并创建双 venv |
| `配置SeedDance.cmd` | 编辑 `overseas-loc-mvp/.env` |
| `清理工作区.cmd` | 去重、junction、删临时文件 |
| `python 海外视频本地化MVP/scripts/cleanup_workspace.py` | 本瘦身脚本 |
"""
    if dry_run:
        print(f"  [dry-run] write {path.name}")
        return
    path.write_text(body, encoding="utf-8")
    print(f"  wrote {path.relative_to(WORKFLOW_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="工作区瘦身")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-junction", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    report: dict[str, object] = {"dry_run": dry, "steps": []}

    print("=== 1. 合并重复目录并建立 junction ===")
    if args.skip_junction:
        linked = ensure_legacy_junctions()
    else:
        linked = replace_legacy_dirs_with_junctions(dry_run=dry)
    report["junctions"] = linked
    for line in linked:
        print(f"  {line}")

    print("=== 2. 清理临时/日志/批量测试元数据 ===")
    n_junk = clean_temp_and_logs(dry_run=dry)
    report["junk_removed"] = n_junk
    print(f"  {n_junk} item(s)")

    print("=== 3. 移除演示启动器与废弃 UI ===")
    n_demo = clean_demo_launchers(dry_run=dry)
    n_ui = clean_deprecated_ui(dry_run=dry)
    report["demo_cmds_removed"] = n_demo
    report["deprecated_ui_removed"] = n_ui

    print("=== 4. 写入 ARCHITECTURE.md ===")
    write_architecture_readme(dry_run=dry)

    out = WORKFLOW_ROOT / "temp" / "cleanup_report.json"
    if not dry:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  report: {out.relative_to(WORKFLOW_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
