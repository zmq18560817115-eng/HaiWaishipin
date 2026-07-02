"""便携恒温杯：产品形态、结构与正确用法（脚本/分镜/SeedDance 统一约束）。"""

from __future__ import annotations

# ── 温度显示（出口版：华氏度，非摄氏）────────────────────────────────────────
THERMOS_TEMPERATURE_ZH = (
    "数显温度单位为华氏度（°F），禁止显示摄氏度（°C）；"
    "出口版典型读数约 98°F（接近体温的舒适温奶，非沸水）；"
    "屏上须带 °F 标识，不得把 98 画成 98°C 或仅写 98 无单位"
)

THERMOS_TEMPERATURE_EN = (
    "TEMPERATURE DISPLAY (export/US): Fahrenheit °F ONLY on vertical digital display; "
    "FORBIDDEN: Celsius °C readout, °C symbol, or 37/40/100 style Celsius numbers; "
    "typical setpoint/readout ~98°F (body-warm serving temp, NOT boiling)"
)

# ── 奶液物理状态（非烧开）────────────────────────────────────────────────
THERMOS_MILK_PHYSICS_ZH = (
    "母乳/配方奶为温热状态（body-warm），倒奶时液体平稳流出；"
    "禁止：烧开冒热气、大量白色蒸汽、沸腾起泡、火苗加热、滚烫发红液体"
)

THERMOS_MILK_PHYSICS_EN = (
    "MILK PHYSICS: breast milk or formula is body-warm only; gentle steady pour stream; "
    "FORBIDDEN: boiling, rolling bubbles, dense white steam plume, simmering, red-hot liquid, stovetop flame heating"
)

# ── 进液来源（避免误用市售牛奶瓶）────────────────────────────────────────
THERMOS_MILK_SOURCE_ZH = (
    "进液来源仅限：储奶袋（母乳储存袋）或家里日常使用的婴儿奶瓶倒奶；"
    "禁止出现：市售牛奶塑料瓶、鲜奶纸盒/利乐包、酸奶杯、任意商超乳制品包装"
)

THERMOS_MILK_SOURCE_EN = (
    "MILK SOURCE: pour breast milk FROM breast-milk storage bag OR pour FROM home baby feeding bottle INTO cup; "
    "FORBIDDEN: grocery milk plastic bottle, milk carton, yogurt cup, any commercial dairy packaging"
)

# ── 产品结构（严格对照倒出口参考图 + 白底图）────────────────────────────
THERMOS_STRUCTURE_ZH = (
    "结构严格对照产品参考图：顶部为翻盖式铰链盖（侧面浅紫矩形按键弹开），非螺旋旋盖；"
    "倒出口为盖面碗形凹槽内的小圆孔出液嘴，倾斜杯身时暖奶从此圆孔流出；"
    "进液经翻开顶盖倒入杯内腔体；盖下深紫装饰环 nurture wise 标识；"
    "下段竖向数显屏（华氏度 °F 温度，典型约 98°F，禁止摄氏度）；数显旁椭圆形 recessed 电源键；"
    "底部 recessed 充电口（硅胶盖内，非杯身侧面 USB 口）；"
    "禁止画成：圆顶旋盖、宽口直倒、杯身侧面充电口、奶瓶放入杯内"
)

THERMOS_STRUCTURE_EN = (
    "STRUCTURE (match pour-spout product reference exactly): flip-top hinged lid on top with light-purple side release button, "
    "NOT a screw cap; integrated POUR OUTLET is a small circular spout hole inside a bowl-shaped recess on the lid — "
    "when cup is tilted, warm milk streams OUT through this spout hole into a separate clear baby feeding bottle; "
    "fill milk INTO cup interior through open flip lid; darker purple band with nurture wise logo below lid; "
    "vertical digital temperature display with Fahrenheit °F readout only (~98°F typical, never °C) and icons on lower body; oval recessed power button beside display; "
    "charging port in recessed bottom area under silicone cover, never a side USB port on cup body; "
    "FORBIDDEN: dome screw cap, unscrew lid, wide-mouth pour without spout hole, bottle inside cup"
)

THERMOS_POUR_ACTION_EN = (
    "POUR DEMO: flip lid open to fill from storage bag or home baby bottle; after warming, tilt cup — "
    "body-warm milk pours OUT only from the small circular spout hole in the lid recess into baby bottle below, "
    "no steam plume or boiling bubbles, matching pour-spout reference photo"
)

# ── 用法总约束 ────────────────────────────────────────────────────────────
THERMOS_USAGE_ZH = (
    "产品为可充电加热保温杯（独立于奶瓶的圆柱暖奶容器，非奶瓶暖奶器）；"
    "用法：从储奶袋或家用奶瓶经翻开顶盖倒入杯内加热保温，再倾斜杯身经盖面圆孔出液嘴倒出到干净奶瓶喂哺；"
    "禁止：把奶瓶放进杯内、从宽口直倒（必须经过圆孔出液嘴）、奶瓶浸在杯中加热"
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
    "portable rechargeable milk-warming thermos cup — match approved white-background hero product photo exactly "
    "for matte lavender purple cylindrical body, flip-top hinged lid with integrated circular pour spout hole, "
    "light-purple lid release button, nurture wise band, vertical digital Fahrenheit °F display showing ~98°F; "
    "no redesign, recolor, or simplification"
)

# 策划/分镜 visual 一行汇总
THERMOS_VISUAL_RULES_ZH = (
    f"{THERMOS_USAGE_ZH}；{THERMOS_MILK_SOURCE_ZH}；{THERMOS_STRUCTURE_ZH}；"
    f"{THERMOS_TEMPERATURE_ZH}；{THERMOS_MILK_PHYSICS_ZH}"
)
