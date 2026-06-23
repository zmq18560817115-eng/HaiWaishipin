#!/usr/bin/env python3
"""将 overseas-loc-mvp/runs/{slug}/ 归档到根目录业务文件夹。"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mvp_runs() -> Path:
    return Path(__file__).resolve().parents[1] / "runs"


def archive_slug(slug: str, *, dry_run: bool = False) -> dict[str, list[str]]:
    slug = slug.strip().lower()
    source = _mvp_runs() / slug
    if not source.is_dir():
        raise FileNotFoundError(f"未找到 runs/{slug}/，请先在页面完成 Brief 或检查 slug")

    root = _root()
    archive_dir = root / "09_archive" / slug
    translation_dir = root / "03_translation" / slug
    subtitles_dir = root / "04_subtitles" / slug
    source_video_dir = root / "01_source_video" / slug
    editing_dir = root / "06_editing" / slug
    review_dir = root / "07_review" / slug

    for path in (
        archive_dir,
        translation_dir,
        subtitles_dir,
        source_video_dir,
        editing_dir,
        review_dir,
    ):
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    manifest_lines = [
        f"# Archive manifest · {slug}",
        f"",
        f"> archived_at: {datetime.now(timezone.utc).isoformat()}",
        f"> source: overseas-loc-mvp/runs/{slug}/",
        f"",
        f"## 文件映射",
        f"",
    ]

    def copy_file(src_rel: str, dest: Path, note: str) -> None:
        src = source / src_rel
        if not src.is_file():
            return
        if dry_run:
            copied.append(f"[dry-run] {src_rel} -> {dest.relative_to(root)}")
        else:
            shutil.copy2(src, dest)
            copied.append(f"{src_rel} -> {dest.relative_to(root).as_posix()}")
        manifest_lines.append(f"- `{src_rel}` → `{dest.relative_to(root).as_posix()}` ({note})")

    def copy_tree(src_rel: str, dest: Path, note: str) -> None:
        src = source / src_rel
        if not src.exists():
            return
        if dry_run:
            copied.append(f"[dry-run] {src_rel}/ -> {dest.relative_to(root)}/")
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            copied.append(f"{src_rel}/ -> {dest.relative_to(root).as_posix()}/")
        manifest_lines.append(f"- `{src_rel}/` → `{dest.relative_to(root).as_posix()}/` ({note})")

    if not dry_run:
        if archive_dir.exists():
            shutil.rmtree(archive_dir)
        shutil.copytree(source, archive_dir)
        copied.append(f"runs/{slug}/ -> 09_archive/{slug}/ (完整副本)")

    copy_file("en-localization-pack.md", translation_dir / "en-localization-pack.md", "EN 脚本包")
    copy_file("subtitles.srt", subtitles_dir / "subtitles.srt", "剪辑字幕")
    copy_file("aspect-ratio-spec.md", review_dir / "aspect-ratio-spec.md", "比例说明")
    copy_file("compliance-report.json", review_dir / "compliance-report.json", "合规扫描")
    copy_file("qa-checklist.md", review_dir / "qa-checklist.md", "QA 清单")
    copy_tree("broll", editing_dir / "broll", "SeedDance B-roll")
    for mp4 in sorted((source / "broll").glob("*.mp4")) if (source / "broll").is_dir() else []:
        copy_file(
            mp4.relative_to(source).as_posix(),
            source_video_dir / mp4.name,
            "B-roll 源片段",
        )

    manifest_path = archive_dir / "archive-manifest.md"
    manifest_lines.append("")
    manifest_lines.append("## 操作记录")
    manifest_lines.append("")
    for line in copied:
        manifest_lines.append(f"- {line}")

    if not dry_run:
        manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        copied.append(f"manifest -> {manifest_path.relative_to(root).as_posix()}")

    return {"slug": slug, "copied": copied, "archive_dir": str(archive_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description="归档 MVP runs/{slug} 到根目录业务文件夹")
    parser.add_argument("slug", help="项目 slug，例如 night-pumping-v1")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要复制的路径")
    args = parser.parse_args()
    try:
        result = archive_slug(args.slug, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    print(f"归档完成: {result['slug']}")
    for line in result["copied"]:
        print(f"  {line}")
    if not args.dry_run:
        print(f"\n完整副本: {result['archive_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
