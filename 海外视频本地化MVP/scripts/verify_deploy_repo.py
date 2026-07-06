"""GitHub 克隆 / git pull 后校验仓库是否具备内网部署所需的全部文件。"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent

REQUIRED_FILES = [
    "启动工作台.cmd",
    "部署内网.cmd",
    "检查开发环境.cmd",
    "setup-dev-env.ps1",
    "ARCHITECTURE.md",
    "README_使用说明.md",
    "config/knowledge-sources.json",
    "config/radar-weights.json",
    "海外视频本地化MVP/app/main.py",
    "海外视频本地化MVP/web/index.html",
    "海外视频本地化MVP/web/app.js",
    "海外视频本地化MVP/web/styles.css",
    "海外视频本地化MVP/requirements.txt",
    "海外视频本地化MVP/.env.example",
    "海外视频本地化MVP/启动页面.cmd",
    "海外视频本地化MVP/scripts/ensure_legacy_paths.py",
    "海外视频本地化MVP/scripts/paths.py",
    "overseas-loc-mvp/requirements.txt",
    "overseas-loc-mvp/.env.example",
    "overseas-loc-mvp/app/video_assemble.py",
    "overseas-video-output-standards/SKILL.md",
    "01_素材库/竞品对标/数据表/videos_meta.csv",
    "01_素材库/竞品对标/数据表/video_analysis.csv",
    "01_素材库/竞品对标/数据表/product_materials.csv",
    "01_素材库/竞品对标/数据表/prompt_library.json",
    "01_素材库/产品资料/便携恒温杯.md",
    "01_素材库/产品资料/便携恒温杯/listing-0602-nw/主图/白底主图.png",
    "04_成稿库/成稿索引.csv",
    "05_反馈库/反馈记录.csv",
    "03_产出库/README.md",
]

REQUIRED_DIRS = [
    "海外视频本地化MVP/app",
    "海外视频本地化MVP/web",
    "海外视频本地化MVP/script_templates",
    "overseas-loc-mvp/app",
    "tiktok_collector",
    "01_素材库/竞品对标/数据表",
    "01_素材库/产品资料",
    "04_成稿库",
    "05_反馈库",
]

WARN_IF_MISSING = [
    ("海外视频本地化MVP/.env", "首次部署需从 .env.example 复制并填写 WORKBENCH_API_TOKEN"),
    ("overseas-loc-mvp/.env", "需填写 ARK_API_KEY 才能使用豆包拆解与 AI 出片"),
    ("海外视频本地化MVP/.venv/Scripts/python.exe", "运行「检查开发环境.cmd」创建 venv"),
    ("overseas-loc-mvp/.venv/Scripts/python.exe", "运行「检查开发环境.cmd」创建 venv"),
]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKFLOW_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _step(name: str, ok: bool, detail: str = "", *, warn: bool = False) -> bool:
    if warn:
        print(f"[WARN] {name}")
        if detail:
            print(f"       {detail}")
        return True
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}")
    if detail:
        print(f"       {detail}")
    return ok


def _read_ui_version() -> int | None:
    main_py = MVP_ROOT / "app" / "main.py"
    text = main_py.read_text(encoding="utf-8")
    m = re.search(r"^UI_VERSION\s*=\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def _csv_row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return max(0, len(rows) - 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 GitHub 仓库是否满足内网部署")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args()

    fails = 0
    warns = 0
    results: list[dict[str, str]] = []

    def record(name: str, ok: bool, detail: str = "", *, level: str = "fail") -> None:
        nonlocal fails, warns
        if level == "warn":
            warns += 1
            _step(name, ok, detail, warn=True)
        elif not _step(name, ok, detail):
            fails += 1
        results.append({"name": name, "ok": ok, "detail": detail, "level": level})

    record("工作区根目录", WORKFLOW_ROOT.is_dir(), _rel(WORKFLOW_ROOT))

    for rel in REQUIRED_DIRS:
        p = WORKFLOW_ROOT / rel.replace("/", "\\")
        record(f"目录 · {rel}", p.is_dir(), _rel(p) if p.is_dir() else "缺失")

    for rel in REQUIRED_FILES:
        p = WORKFLOW_ROOT / rel.replace("/", "\\")
        record(f"文件 · {rel}", p.is_file(), _rel(p) if p.is_file() else "缺失")

    ui_ver = _read_ui_version()
    record("UI 版本号", ui_ver is not None and ui_ver > 0, f"v{ui_ver}" if ui_ver else "无法解析 UI_VERSION")

    index_html = (MVP_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    record(
        "index.html 版本占位符",
        "{{UI_VERSION}}" in index_html,
        "静态资源应带 ?v={{UI_VERSION}} 缓存破除",
    )

    meta_csv = WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "数据表" / "videos_meta.csv"
    analysis_csv = WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "数据表" / "video_analysis.csv"
    meta_n = _csv_row_count(meta_csv)
    analysis_n = _csv_row_count(analysis_csv)
    record("竞品元数据", meta_n > 0, f"videos_meta {meta_n} 条")
    record("已拆解素材", analysis_n > 0, f"video_analysis {analysis_n} 条")

    white_bg = WORKFLOW_ROOT / "01_素材库" / "产品资料" / "便携恒温杯" / "listing-0602-nw" / "主图" / "白底主图.png"
    record("SeedDance 白底主图", white_bg.is_file() and white_bg.stat().st_size > 500, _rel(white_bg))

    for rel, hint in WARN_IF_MISSING:
        p = WORKFLOW_ROOT / rel.replace("/", "\\")
        if not p.exists():
            record(rel, False, hint, level="warn")

    try:
        import ast

        ast.parse((MVP_ROOT / "app" / "main.py").read_text(encoding="utf-8"))
        record("main.py 语法", True)
    except SyntaxError as exc:
        record("main.py 语法", False, str(exc))

    print()
    if args.json:
        print(json.dumps({"ok": fails == 0, "fails": fails, "warns": warns, "ui_version": ui_ver, "items": results}, ensure_ascii=False, indent=2))
    elif fails:
        print(f"部署包不完整：{fails} 项缺失或异常。请确认 git pull 成功且未漏推关键文件。")
        print("开发者推送前可运行：验证GitHub部署包.cmd")
    else:
        print("部署包校验通过。内网服务器下一步：")
        print("  1. 检查开发环境.cmd（首次或 requirements 变更后）")
        print("  2. 配置 overseas-loc-mvp/.env 与 海外视频本地化MVP/.env")
        print("  3. 部署内网.cmd")
        if warns:
            print(f"（另有 {warns} 项提示，属首次部署正常现象）")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
