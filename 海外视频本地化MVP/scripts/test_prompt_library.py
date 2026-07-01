"""提示词库闭环自检：预设种子 → 列表 → 使用计数。"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
MVP_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(MVP_ROOT))

from app.prompt_library import (  # noqa: E402
    DEFAULT_PROMPT_PRESETS,
    ensure_default_presets,
    list_prompts,
    record_usage,
)
from app.reverse_prompt import run_reverse_prompt  # noqa: E402
from app.data import load_materials  # noqa: E402


def main() -> int:
    presets = ensure_default_presets()
    print(f"[ok] seeded presets: {len(presets)} (expected {len(DEFAULT_PROMPT_PRESETS)})")
    for p in presets:
        print(f"  - {p.get('prompt_type')}: {p.get('label')}")

    listed = list_prompts()
    preset_rows = [r for r in listed if r.get("source") == "preset"]
    assert len(preset_rows) >= len(DEFAULT_PROMPT_PRESETS), "preset count mismatch"

    first = preset_rows[0]
    pid = first["prompt_id"]
    before = int(first.get("usage_count") or 0)
    updated = record_usage(pid)
    assert updated and int(updated["usage_count"]) == before + 1
    print(f"[ok] usage feedback: {pid} {before} -> {updated['usage_count']}")

    materials = load_materials()
    if materials:
        try:
            rev = run_reverse_prompt(materials[0]["link_id"], save=True)
            print(f"[ok] reverse saved: link={materials[0]['link_id']} count={rev['saved_count']}")
        except ValueError as exc:
            print(f"[skip] reverse: {exc}")

    all_items = list_prompts()
    print(f"[ok] library total: {len(all_items)} (presets + reverse)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
