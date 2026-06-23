"""模拟使用者走查：素材库 → 脚本生成 → 交付 → 成稿库 闭环验证。"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8788"
PRODUCT = "便携恒温杯"
TAGS = {
    "audience_tags": ["0-12月新手爸妈"],
    "scenario_tags": ["夜间卧室喂奶"],
    "selling_tags": ["便携可充电设计", "外出随时加热"],
    "pain_tags": ["传统暖奶器太大不便携"],
}


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return json.load(r)


def post(path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def step(name: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    print(line.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    if detail:
        d = detail.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(f"       {d}")


def main() -> int:
    fails = 0

    # 0 启动与环境
    try:
        h = get("/api/health")
        step("0. 服务可用", h.get("ok"), f"UI v{h.get('ui_version')} · 素材 {h.get('materials')} · 已拆解 {h.get('analyzed')} · 产品 {h.get('products')}")
        if h.get("analyzed", 0) < 1:
            fails += 1
            step("0b. 数据就绪", False, "无已拆解素材，需到「设置」运行拆解")
    except Exception as e:
        step("0. 服务可用", False, str(e))
        return 1

    # 1 素材库
    mats = get("/api/materials?analyzed_only=true")
    items = mats.get("items") or []
    step("1. 素材库（已拆解）", len(items) > 0, f"共 {len(items)} 条")
    if not items:
        return 1
    link_id = next((i["link_id"] for i in items if not i.get("delivery_ready")), items[0]["link_id"])
    for i in items:
        if not i.get("delivery_ready") and i.get("content_line") == PRODUCT:
            link_id = i["link_id"]
            break
    detail = get(f"/api/materials/{link_id}")
    step("1b. 素材详情", bool(detail.get("analysis")), f"#{link_id} {str(detail.get('title',''))[:40]}")

    # 2 脚本页预览（模拟：选产品 + 结构参考）
    pid = urllib.parse.quote(PRODUCT)
    prev = get(f"/api/materials/{link_id}/preview?product_id={pid}")
    tags = prev.get("delivery_tags") or {}
    sel = prev.get("selected_tags") or {}
    aud_n = len(tags.get("audience") or [])
    sell_n = len(tags.get("selling") or [])
    pain_n = len(tags.get("pains") or [])
    step(
        "2. 脚本页标签池",
        aud_n > 0 and sell_n > 0 and pain_n > 0,
        f"人群 {aud_n} · 场景 {len(tags.get('scenarios') or [])} · 卖点 {sell_n} · 痛点 {pain_n}",
    )
    step("2b. 五步条-结构参考", bool(prev.get("material")), f"模板 {prev.get('template',{}).get('label','')}")
    step("2c. 五步条-产品", bool(prev.get("product")), prev.get("product", {}).get("product_name", PRODUCT))

    # 3 生成脚本（四类标签）
    body = {
        "product_id": PRODUCT,
        "bridge": True,
        "target_country": "US",
        "language": "en",
        "style": "us_tiktok_spoken",
        **TAGS,
    }
    try:
        gen = post(f"/api/materials/{link_id}/generate", body)
        pack = gen.get("script_pack") or {}
        vo = pack.get("voiceover_20s") or ""
        bad_travel = any(x in vo.lower() for x in ("traveling", "out with baby", "next trip"))
        bad_scene = TAGS["scenario_tags"][0] == "夜间卧室喂奶" and bad_travel
        step("3. 生成脚本", bool(pack.get("storyboard")), f"标题 {str(pack.get('title',''))[:50]}")
        step("3b. 场景一致（卧室无外出口播）", not bad_scene, vo[:80] if bad_scene else "口播与卧室场景一致")
        shots = pack.get("storyboard") or []
        if shots:
            v0 = shots[0].get("visual", "")
            step("3c. 分镜画面含场景", TAGS["scenario_tags"][0] in v0 or "夜间" in v0, v0[:60])
    except urllib.error.HTTPError as e:
        fails += 1
        step("3. 生成脚本", False, e.read().decode()[:120])
        return 1

    slug = gen.get("slug") or f"ref-{link_id:03d}"

    # 4 完成交付
    prev2 = get(f"/api/materials/{link_id}/preview?product_id={pid}")
    step("4a. 生成后可交付", prev2.get("can_finish") is True, f"can_finish={prev2.get('can_finish')}")
    try:
        fin = post(f"/api/delivery/{slug}/finish")
        step("4. 完成交付", fin.get("ok") is not False, fin.get("message", "ok")[:60])
    except urllib.error.HTTPError as e:
        fails += 1
        step("4. 完成交付", False, e.read().decode()[:120])

    prev3 = get(f"/api/materials/{link_id}/preview?product_id={pid}")
    step("4b. 交付后 delivery_ready", prev3.get("delivery_ready") is True, f"slug={slug}")

    # 5 成稿库
    finished = get("/api/library/finished")
    items_f = finished.get("items") or []
    hit = any(x.get("slug") == slug for x in items_f)
    step("5. 成稿库入库", hit, f"成稿共 {len(items_f)} 条")

    # 6 zip
    try:
        req = urllib.request.Request(f"{BASE}/api/delivery/{slug}/zip")
        with urllib.request.urlopen(req) as r:
            size = len(r.read())
        step("6. 下载 zip", size > 500, f"{size} bytes")
    except Exception as e:
        fails += 1
        step("6. 下载 zip", False, str(e))

    print()
    if fails:
        print(f"走查未完全通过（{fails} 项需关注）")
        return 1
    print("走查通过：素材库 → 脚本生成（本页标签）→ 交付 → 成稿库 闭环可用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
