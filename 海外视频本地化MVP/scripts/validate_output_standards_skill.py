"""验证 overseas-video-output-standards skill 与当前工作流是否对齐。

用法:
  python scripts/validate_output_standards_skill.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent
SKILL_ROOT = WORKFLOW_ROOT / "overseas-video-output-standards"
sys.path.insert(0, str(MVP_ROOT / "scripts"))
sys.path.insert(0, str(MVP_ROOT))

from app.data import load_materials  # noqa: E402
from app.product_usage import THERMOS_USAGE_EN  # noqa: E402
from paths import PRODUCT_MATERIALS_DIR, VIDEOS_META_CSV  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def main() -> int:
    results: list[dict] = []

    for rel in (
        "SKILL.md",
        "references/product-rules.md",
        "references/script-to-asset-workflow.md",
        "references/material-asset-standards.md",
        "references/qa-checklist.md",
        "agents/openai.yaml",
    ):
        p = SKILL_ROOT / rel
        results.append(check(f"skill:{rel}", p.is_file(), str(p)))

    pour = PRODUCT_MATERIALS_DIR / "便携恒温杯" / "listing-0602-nw" / "主图" / "倒出口参考.png"
    white = PRODUCT_MATERIALS_DIR / "便携恒温杯" / "listing-0602-nw" / "主图" / "白底主图.png"
    results.append(check("asset:倒出口参考.png", pour.is_file(), str(pour)))
    results.append(check("asset:白底主图.png", white.is_file(), str(white)))

    from app.product_assets import get_product_hero_image, get_product_usage_pour_image, get_product_white_hero_image  # noqa: E402

    hero = get_product_white_hero_image("便携恒温杯")
    pour_img = get_product_usage_pour_image("便携恒温杯")
    hero_ok = hero is not None and "白底" in hero.name
    results.append(check("code:white_hero resolves", hero_ok, str(hero) if hero else "missing"))
    results.append(
        check(
            "code:hero != pour",
            hero is not None and pour_img is not None and hero.resolve() != pour_img.resolve(),
            f"hero={hero.name if hero else '-'} pour={pour_img.name if pour_img else '-'}",
        )
    )
    results.append(check("code:get_product_hero_image alias", get_product_hero_image("便携恒温杯") == hero, "white hero alias"))

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
    fidelity_keywords = ("白底主图", "production_fidelity", "physics", "hero lock")
    missing_fidelity = [k for k in fidelity_keywords if k.lower() not in skill_text.lower()]
    results.append(
        check(
            "skill:production_fidelity_rules",
            not missing_fidelity,
            "missing: " + ", ".join(missing_fidelity) if missing_fidelity else "hero/scenario/detail locks documented",
        )
    )

    keywords = ("flip-top", "spout hole", "storage bag", "FORBIDDEN", "wide-mouth", "Fahrenheit", "steam plume")
    missing = [k for k in keywords if k not in THERMOS_USAGE_EN]
    results.append(
        check(
            "code:product_usage thermos rules",
            not missing,
            "missing: " + ", ".join(missing) if missing else "aligned with skill product-rules",
        )
    )

    n = len(load_materials())
    results.append(check("data:competitor materials", n > 0, f"{n} items"))

    results.append(check("data:videos_meta.csv", VIDEOS_META_CSV.is_file(), str(VIDEOS_META_CSV)))

    compliance = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "processes"
    results.append(check("knowledge:compliance", compliance.is_dir()))

    # skill 要求但代码尚未结构化的字段
    app_dir = MVP_ROOT / "app"
    for term in ("asset_manifest", "shot_asset_map", "scene_continuity", "character_continuity", "production_fidelity"):
        found = any(term in py.read_text(encoding="utf-8", errors="ignore") for py in app_dir.glob("*.py"))
        results.append(
            check(
                f"gap:code.{term}",
                found,
                "skill 已定义，代码待接入（生成脚本时由 Agent 按 skill 产出）" if not found else "present",
            )
        )

    passed = sum(1 for r in results if r["ok"])
    report = {
        "skill_root": str(SKILL_ROOT),
        "passed": passed,
        "total": len(results),
        "usable_for_workflow": passed == len(results),
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["usable_for_workflow"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
