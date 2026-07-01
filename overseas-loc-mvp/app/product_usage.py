"""便携恒温杯：产品形态、结构与正确用法（与 8788 工作台保持一致）。"""
from __future__ import annotations

# 完整规则见 海外视频本地化MVP/app/product_usage.py；此处为交付引擎 SeedDance 子进程引用。

THERMOS_TEMPERATURE_EN = (
    "TEMPERATURE DISPLAY (export/US): Fahrenheit °F ONLY on vertical digital display; "
    "FORBIDDEN: Celsius °C readout; typical readout ~98°F (body-warm, NOT boiling)"
)

THERMOS_MILK_PHYSICS_EN = (
    "MILK PHYSICS: body-warm milk only; gentle pour; "
    "FORBIDDEN: boiling, steam plume, rolling bubbles, red-hot liquid"
)

THERMOS_MILK_SOURCE_EN = (
    "MILK SOURCE: pour breast milk FROM breast-milk storage bag OR pour FROM home baby feeding bottle INTO cup; "
    "FORBIDDEN: grocery milk plastic bottle, milk carton, yogurt cup, any commercial dairy packaging"
)

THERMOS_STRUCTURE_EN = (
    "STRUCTURE (match pour-spout product reference exactly): flip-top hinged lid on top with light-purple side release button, "
    "NOT a screw cap; integrated POUR OUTLET is a small circular spout hole inside a bowl-shaped recess on the lid — "
    "when cup is tilted, warm milk streams OUT through this spout hole into a separate clear baby feeding bottle; "
    "fill milk INTO cup interior through open flip lid; darker purple band with nurture wise logo below lid; "
    "vertical digital temperature display with Fahrenheit °F readout only (~98°F typical, never °C) and icons on lower body; "
    "oval recessed power button beside display; "
    "charging port in recessed bottom area under silicone cover, never a side USB port on cup body; "
    "FORBIDDEN: dome screw cap, unscrew lid, wide-mouth pour without spout hole, bottle inside cup"
)

THERMOS_POUR_ACTION_EN = (
    "POUR DEMO: flip lid open to fill from storage bag or home baby bottle; after warming, tilt cup — "
    "body-warm milk pours OUT only from the small circular spout hole in the lid recess into baby bottle below, "
    "no steam plume or boiling bubbles, matching pour-spout reference photo"
)

THERMOS_USAGE_EN = (
    "USAGE: rechargeable insulated milk-warming thermos cup (cylindrical cup body), separate from baby bottle; "
    "pour milk INTO cup through open flip-top lid to warm inside, then tilt cup and pour warm milk OUT "
    "through the small circular spout hole in lid recess into baby feeding bottle; "
    "FORBIDDEN: placing baby bottle inside cup, wide-mouth pour without spout, bottle-in-cup warming; "
    "not a bottle-in-warmer device. "
    f"{THERMOS_MILK_SOURCE_EN}. {THERMOS_STRUCTURE_EN}. {THERMOS_TEMPERATURE_EN}. "
    f"{THERMOS_MILK_PHYSICS_EN}. {THERMOS_POUR_ACTION_EN}"
)

THERMOS_PRODUCT_EN = (
    "portable rechargeable milk-warming thermos cup, matte lavender purple cylindrical body, "
    "flip-top hinged lid with integrated circular pour spout hole in bowl-shaped lid recess, "
    "light-purple lid release button, nurture wise band, vertical digital Fahrenheit °F display showing ~98°F, "
    "pour-spout reference photo"
)
