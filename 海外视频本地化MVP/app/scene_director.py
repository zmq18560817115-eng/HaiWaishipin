"""根据用户勾选的场景/痛点/卖点标签，生成场景一致的分镜与画面 prompt。"""

from __future__ import annotations

from typing import Any

_SCENE_KEYS: list[tuple[str, tuple[str, ...]]] = [
    ("bedroom", ("卧室", "夜间", "夜奶", "床头")),
    ("car", ("车内", "杯架", "汽车", "车载")),
    ("travel", ("机场", "旅途", "出行", "飞机", "长途")),
    ("office", ("办公室", "背奶", "工位")),
    ("park", ("公园", "遛娃", "户外")),
    ("restaurant", ("餐厅", "商场", "冲奶")),
]


def _blob(tags: list[str]) -> str:
    return "、".join(tags)


def scene_profile_for_tag(tag: str) -> str:
    for profile, keys in _SCENE_KEYS:
        if any(k in tag for k in keys):
            return profile
    return "generic"


def resolve_scene_anchor(scenario_tags: list[str]) -> tuple[str, str, list[str]]:
    """返回 (profile, anchor_tag, warnings)。多场景冲突时锁定首个标签为唯一布景。"""
    if not scenario_tags:
        return "generic", "", []
    profiles = [scene_profile_for_tag(t) for t in scenario_tags]
    unique = {p for p in profiles if p != "generic"}
    warnings: list[str] = []
    anchor = scenario_tags[0]
    profile = scene_profile_for_tag(anchor)
    if len(unique) > 1:
        warnings.append(
            f"已选多个冲突场景（{'、'.join(scenario_tags)}），成片统一按首要场景「{anchor}」生成，避免卧室/车载等混用"
        )
    return profile, anchor, warnings


def _pick(lines: dict[str, str], profile: str, default: str) -> str:
    return lines.get(profile) or lines.get("generic") or default


def build_thermos_shots(
    *,
    product_name: str,
    market: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    scenarios = market.get("scenario_tags") or []
    pains = market.get("pain_tags") or []
    selling = market.get("selling_tags") or []
    audience = market.get("audience_tags") or []
    profile, anchor, warnings = resolve_scene_anchor(scenarios)
    pain_zh = _blob(pains)
    sell_zh = _blob(selling)
    aud_zh = _blob(audience)

    vo_hook = {
        "bedroom": "2 a.m. feeds shouldn't feel this chaotic.",
        "car": "No way to warm milk safely in the car?",
        "travel": "Travel days and cold bottles don't mix.",
        "office": "Pumping moms need warm milk without the hassle.",
        "park": "Out at the park and the bottle's still too cold?",
        "restaurant": "Public places make warming milk harder than it should be.",
        "generic": "Warming milk shouldn't steal this much of your calm.",
    }
    vo_pain = {
        "bedroom": "Cold milk and fumbling in the dark makes night feeds exhausting.",
        "car": "Waiting forever while baby cries in the back seat is stressful.",
        "travel": "Airport lines and no hot water — every parent knows the panic.",
        "office": "Stepping away to find hot water breaks your whole rhythm.",
        "park": "You shouldn't need a microwave on a stroller walk.",
        "restaurant": "Hunting for hot water mid-meal is the last thing you need.",
        "generic": f"These pains hit hard: {pain_zh[:40]}." if pain_zh else "Slow, uneven warming adds stress you don't need.",
    }
    vo_sell = {
        "bedroom": "This portable warmer heats evenly right on your nightstand.",
        "car": "Cup-holder friendly — even heat in minutes on the road.",
        "travel": "Rechargeable travel warmer, ready in your carry-on.",
        "office": "Compact on your desk — steady heat between meetings.",
        "park": "Fits the diaper bag — warm milk at the playground.",
        "restaurant": "Discreet in your bag — heat without leaving the table.",
        "generic": "Portable, even heating in just a few minutes.",
    }
    if any("USB" in s or "充电" in s for s in selling):
        vo_sell[profile] = vo_sell.get(profile, vo_sell["generic"]).replace(
            "Portable", "USB-C rechargeable portable"
        )
    vo_proof = {
        "bedroom": "Soft indicator light, quiet heat — baby stays settled.",
        "car": "Stable in the cup holder while you focus on the drive.",
        "travel": "TSA-friendly size, one less thing to stress about.",
        "office": "Quick heat between tasks — no microwave run.",
        "park": "One-hand operation while baby is in the stroller.",
        "restaurant": "Low-profile warm-up right at your seat.",
        "generic": "Steady temperature you can trust, shot after shot.",
    }
    vo_cta = {
        "bedroom": "Save this for calmer night feeds.",
        "car": "Save this before your next car trip with baby.",
        "travel": "Save this for your next flight with little ones.",
        "office": "Save this if you're a pumping mom on the go.",
        "park": "Save this for your next park day.",
        "restaurant": "Save this for dining out with baby.",
        "generic": "Save this for easier bottle days.",
    }

    vis_hook = {
        "bedroom": f"昏暗卧室近景，疲惫爸妈夜奶瞬间，痛点特写；布景仅限：{anchor}",
        "car": f"车内副驾视角，婴儿座椅与奶瓶，杯架空位特写；布景：{anchor}",
        "travel": f"机场/旅途等候区，妈咪包与奶瓶特写；布景：{anchor}",
        "office": f"办公室桌角，背奶妈妈短暂停留，奶瓶与包；布景：{anchor}",
        "park": f"公园长椅/遛娃动线，婴儿车与奶瓶；布景：{anchor}",
        "restaurant": f"餐厅/商场座位，低调温奶需求；布景：{anchor}",
        "generic": f"近景口播或问题特写；布景：{anchor}",
    }
    vis_pain = {
        "bedroom": f"卧室夜奶焦虑空镜：冷奶瓶、昏暗床头灯、妈妈剪影；痛点：{pain_zh}",
        "car": f"车内加热困扰：奶瓶凉、宝宝哭闹暗示（无血腥）；痛点：{pain_zh}",
        "travel": f"旅途候机/赶路焦虑空镜；痛点：{pain_zh}",
        "office": f"工位旁等待热水/微波炉的焦虑感；痛点：{pain_zh}",
        "park": f"户外遛娃时奶瓶过凉的困扰；痛点：{pain_zh}",
        "restaurant": f"商场/餐厅找热水的窘迫；痛点：{pain_zh}",
        "generic": f"展示困扰：{pain_zh}",
    }
    vis_sell = {
        "bedroom": f"卧室床头使用 {product_name} 加热演示；卖点：{sell_zh}",
        "car": f"车内杯架放置 {product_name} 加热演示；卖点：{sell_zh}",
        "travel": f"旅途场景 {product_name} 便携加热；卖点：{sell_zh}",
        "office": f"办公桌/哺乳角 {product_name} 演示；卖点：{sell_zh}",
        "park": f"公园遛娃场景 {product_name} 使用；卖点：{sell_zh}",
        "restaurant": f"餐厅座位旁 {product_name} 低调加热；卖点：{sell_zh}",
        "generic": f"产品特写与加热演示；卖点：{sell_zh}",
    }
    vis_proof = {
        "bedroom": f"卧室夜奶成功：温度均匀、宝宝安睡侧写；场景：{anchor}",
        "car": f"车内稳定加热完成，杯架稳固；场景：{anchor}",
        "travel": f"旅途出行温奶完成瞬间；场景：{anchor}",
        "office": f"办公室背奶间隙完成加热；场景：{anchor}",
        "park": f"公园遛娃间隙温奶完成；场景：{anchor}",
        "restaurant": f"餐厅座位旁温奶完成；场景：{anchor}",
        "generic": f"场景证明：{anchor}",
    }
    vis_cta = {
        "bedroom": f"卧室柔光下对镜轻声推荐；人群：{aud_zh}",
        "car": f"车内安全停靠时对镜推荐；人群：{aud_zh}",
        "travel": f"旅途场景对镜推荐；人群：{aud_zh}",
        "office": f"办公场景对镜推荐；人群：{aud_zh}",
        "park": f"公园场景对镜推荐；人群：{aud_zh}",
        "restaurant": f"餐厅场景对镜推荐；人群：{aud_zh}",
        "generic": f"口播对镜；人群：{aud_zh}",
    }

    sd_pain = {
        "bedroom": (
            "Dim nursery at night, cold baby bottle on wooden bedside table, "
            "warm lamp glow, tired parent silhouette soft focus, slow push-in, "
            "no medical claim, cozy bedroom only, no car interior, 9:16"
        ),
        "car": (
            "Car interior back seat, baby bottle in cup holder, daylight through window, "
            "subtle stress mood, no bedroom, slow handheld, no medical claim, 9:16"
        ),
        "travel": (
            "Airport lounge or travel waiting area, diaper bag open, baby bottle, "
            "soft daylight, no bedroom no car interior, cinematic b-roll, 9:16"
        ),
        "office": (
            "Office desk corner, breast pump bag, baby bottle, muted corporate light, "
            "no bedroom, no car, slow push-in, 9:16"
        ),
        "park": (
            "Park bench and stroller, baby bottle in bag, golden hour outdoor, "
            "no indoor bedroom, lifestyle b-roll, 9:16"
        ),
        "restaurant": (
            "Casual restaurant table, baby bottle discreetly in tote, warm ambient light, "
            "no bedroom no vehicle, commercial b-roll, 9:16"
        ),
        "generic": (
            "Soft neutral nursery light, baby bottle on tray, warm ambient glow, "
            "slow push-in, no medical claim, 9:16"
        ),
    }

    specs = [
        ("钩子", "0-3s", _pick(vis_hook, profile, vis_hook["generic"]), _pick(vo_hook, profile, vo_hook["generic"]), "LIVE_ACTION"),
        ("痛点", "3-8s", _pick(vis_pain, profile, vis_pain["generic"]), _pick(vo_pain, profile, vo_pain["generic"]), "AI_BROLL"),
        ("方案", "8-13s", _pick(vis_sell, profile, vis_sell["generic"]), _pick(vo_sell, profile, vo_sell["generic"]), "LIVE_ACTION"),
        ("证明", "13-17s", _pick(vis_proof, profile, vis_proof["generic"]), _pick(vo_proof, profile, vo_proof["generic"]), "LIVE_ACTION"),
        ("行动号召", "17-20s", _pick(vis_cta, profile, vis_cta["generic"]), _pick(vo_cta, profile, vo_cta["generic"]), "LIVE_ACTION"),
    ]

    storyboard: list[dict[str, Any]] = []
    for i, (role, timing, visual, vo, ft) in enumerate(specs, start=1):
        vp = (
            f"{visual}；产品：{product_name}；唯一布景：{anchor}；"
            f"人群：{aud_zh}；竖屏9:16；禁止出现与「{anchor}」冲突的场景元素"
        )
        sd = ""
        if ft == "AI_BROLL":
            sd = _pick(sd_pain, profile, sd_pain["generic"])
        storyboard.append({
            "number": i,
            "role": role,
            "timing": timing,
            "visual": visual,
            "voiceover_en": vo,
            "subtitle_en": vo,
            "visual_prompt": vp,
            "seedance_prompt": sd,
            "footage_type": ft,
        })

    titles = {
        "bedroom": ("Night feeds made calmer", f"{product_name} for 2 a.m. peace"),
        "car": ("Warm milk in the cup holder", f"{product_name} on the road"),
        "travel": ("Travel-ready bottle warming", f"{product_name} for trips"),
        "office": ("Desk-side bottle warming", f"{product_name} for working moms"),
        "park": ("Warm milk at the playground", f"{product_name} for park days"),
        "restaurant": ("Discreet warming out dining", f"{product_name} anywhere"),
        "generic": ("Even heat in minutes", f"{product_name} tips"),
    }
    title_en, subtitle_en = titles.get(profile, titles["generic"])
    meta = {"scene_profile": profile, "scene_anchor": anchor, "title_en": title_en, "subtitle_en": subtitle_en}
    return storyboard, meta, warnings


def build_pump_shots(
    *,
    product_name: str,
    market: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    """吸奶器：同样锁定单一布景，避免场景混用。"""
    scenarios = market.get("scenario_tags") or []
    pains = market.get("pain_tags") or []
    selling = market.get("selling_tags") or []
    audience = market.get("audience_tags") or []
    profile, anchor, warnings = resolve_scene_anchor(scenarios)
    pain_zh = _blob(pains)
    sell_zh = _blob(selling)
    aud_zh = _blob(audience)

    vo = {
        "bedroom": [
            "Middle-of-the-night pumping shouldn't hurt this much.",
            "Wrong fit in the dark makes every session harder.",
            "Quieter motor and better fit — right at your bedside.",
            "Less cleanup means back to sleep faster.",
            "Save this for calmer night pumping.",
        ],
        "office": [
            "Pumping at work shouldn't feel this stressful.",
            "Bulky gear and wrong suction waste your break.",
            "Portable, adjustable suction that fits your rhythm.",
            "Quick clean parts between meetings.",
            "Save this for your work pumping routine.",
        ],
    }
    default_vo = [
        "Still struggling with your pump setup?",
        f"Real pain point: {pain_zh[:36]}." if pain_zh else "Wrong fit can make every session uncomfortable.",
        f"Key benefit: {sell_zh[:36]}." if sell_zh else "Adjustable suction helps you find a better fit.",
        f"Works in your scene: {anchor}.",
        "Save this for your next pumping session.",
    ]
    lines = vo.get(profile, default_vo)

    vis_roles = ("钩子", "痛点", "方案", "证明", "行动号召")
    timings = ("0-3s", "3-8s", "8-13s", "13-17s", "17-20s")
    fts = ("LIVE_ACTION", "AI_BROLL", "LIVE_ACTION", "LIVE_ACTION", "LIVE_ACTION")
    storyboard: list[dict[str, Any]] = []
    for i, (role, timing, ft) in enumerate(zip(vis_roles, timings, fts), start=1):
        visual = f"{role}镜头；布景仅限：{anchor}；痛点：{pain_zh}；卖点：{sell_zh}"
        vp = f"{visual}；产品：{product_name}；人群：{aud_zh}；竖屏9:16；禁止冲突场景"
        sd = ""
        if ft == "AI_BROLL":
            sd = (
                f"Soft {profile} pumping setup, {anchor} setting only, "
                "warm side light, slow push-in, no medical claim, 9:16"
            )
        storyboard.append({
            "number": i,
            "role": role,
            "timing": timing,
            "visual": visual,
            "voiceover_en": lines[i - 1],
            "subtitle_en": lines[i - 1],
            "visual_prompt": vp,
            "seedance_prompt": sd,
            "footage_type": ft,
        })
    meta = {
        "scene_profile": profile,
        "scene_anchor": anchor,
        "title_en": f"{product_name} pumping tips",
        "subtitle_en": f"Made for {anchor}",
    }
    return storyboard, meta, warnings
