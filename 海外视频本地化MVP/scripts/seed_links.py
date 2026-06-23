"""Curated portable bottle warmer / travel milk warmer TikTok links."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SeedLink:
    user: str
    video_id: str
    category: str
    notes: str = ""


# 便携暖奶器 / 恒温杯竞品种草与测评（TikTok US）
SEED_LINKS: list[SeedLink] = [
    SeedLink("gadgetglimpse", "7376304558559071530", "bottle_warmer", "portable warmer roundup"),
    SeedLink("eugenie.strawderman", "7440471494041275678", "bottle_warmer", "bololo portable warmer"),
    SeedLink("babybrezza", "7383388217879383339", "bottle_warmer", "baby brezza superfast portable"),
    SeedLink("elliamalone", "7280005363171151146", "bottle_warmer", "momcozy portable review"),
    SeedLink("kaylatwinmom", "7442474674031693099", "bottle_warmer", "travel bottle warmer"),
    SeedLink("beeandtheboys", "7158923548579499310", "bottle_warmer", "on the go feeding"),
    SeedLink("courtneybb04", "7426873794754546974", "bottle_warmer", "portable warmer demo"),
    SeedLink("simply_chella", "7506642110834281774", "bottle_warmer", "mom must have warmer"),
    SeedLink("cupcakegaboo", "7106665278041394478", "bottle_warmer", "bottle warmer hack"),
    SeedLink("claudiadelrio1", "7472050129772629290", "bottle_warmer", "travel milk warmer"),
    SeedLink("brbvicky", "7516360043470654750", "bottle_warmer", "portable warmer review"),
    SeedLink("racheljoanmyers", "7462847085394644270", "bottle_warmer", "warming on the go"),
    SeedLink("chels_morgan97", "7431553642110487838", "bottle_warmer", "momcozy mw03"),
    SeedLink("adiiariiss", "7295379796677201183", "bottle_warmer", "baby feeding essentials"),
    SeedLink("kimberly.michellee", "7460374667765894442", "bottle_warmer", "portable warmer test"),
    SeedLink("lazykelly", "7229018143182785838", "bottle_warmer", "travel baby gear"),
    SeedLink("theinmanfamblog", "7246038193051553067", "bottle_warmer", "diaper bag warmer"),
    SeedLink("theregistrymama", "7456447365608639774", "bottle_warmer", "registry must have"),
    SeedLink("loveeprinny", "7439535973635050783", "bottle_warmer", "bottle warmer comparison"),
    SeedLink("the_health_plug", "7501454276888120622", "bottle_warmer", "baby brezza vs momcozy"),
    SeedLink("h.a.branson", "7467639437304859950", "bottle_warmer", "portable warmer tips"),
    SeedLink("lloyd__co", "7335273528473783595", "bottle_warmer", "travel feeding hack"),
    SeedLink("tiffanymariekohut", "7476987220591660319", "bottle_warmer", "warm milk anywhere"),
    SeedLink("gladysmamacita", "7423195910550605102", "bottle_warmer", "momcozy warmer"),
    SeedLink("jewelpovey", "7389367451684736286", "bottle_warmer", "bottle warmer review"),
    SeedLink("montessori_by_june", "7225989196735991086", "bottle_warmer", "feeding on the go"),
    SeedLink("maceylin", "7510017836069408046", "bottle_warmer", "portable milk warmer"),
    SeedLink("momlifeandmonique", "7462773467201473822", "bottle_warmer", "new mom essentials"),
    SeedLink("helebell511", "7400367780178038047", "bottle_warmer", "night feed warmer"),
    SeedLink("itstheleefam", "7502495667516984607", "bottle_warmer", "family travel feeding"),
    SeedLink("courtneyy__k", "7464258420884000030", "bottle_warmer", "dr browns + warmer"),
    SeedLink("twin_mama6", "7492145649266347306", "bottle_warmer", "twin mom warmer"),
    SeedLink("mady.motherhood", "7521765085048540447", "bottle_warmer", "motherhood must haves"),
    SeedLink("monikalili", "7518352252461927694", "bottle_warmer", "portable warmer unboxing"),
    SeedLink("thebabygearconsultant", "7472253596185398574", "bottle_warmer", "baby gear consultant"),
    SeedLink("themilknest", "7434209692466826526", "bottle_warmer", "feeding support"),
    SeedLink("joannafranken", "7491562905360502034", "bottle_warmer", "new parent travel"),
]


def build_url(link: SeedLink) -> str:
    return f"https://www.tiktok.com/@{link.user}/video/{link.video_id}"


def seed_rows() -> list[dict[str, str]]:
    today = date.today().isoformat()
    rows: list[dict[str, str]] = []
    for index, link in enumerate(SEED_LINKS, start=1):
        rows.append(
            {
                "link_id": str(index),
                "url": build_url(link),
                "category": link.category,
                "platform": "tiktok",
                "subcategory": "便携恒温杯",
                "source": "manual",
                "status": "pending",
                "notes": link.notes,
                "added_at": today,
            }
        )
    return rows
