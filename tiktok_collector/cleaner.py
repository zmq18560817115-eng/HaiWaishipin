from __future__ import annotations

from typing import Iterable

from .models import ReviewedTikTokVideoRecord, TikTokVideoRecord


BASE_POSITIVE_TERMS = {
    "breast",
    "pump",
    "wearable",
    "manual",
    "lactation",
    "milk",
    "nursing",
    "flange",
    "bottle",
    "baby",
    "newborn",
    "mom",
    "mommy",
    "postpartum",
    "feeding",
    "breastfeeding",
    "breastmilk",
    "momcozy",
    "medela",
    "spectra",
    "eufy",
    "dr isla",
    "bunny goody",
}

NEGATIVE_TERMS = {
    "onlyfans",
    "nsfw",
    "porn",
    "nude",
    "lingerie",
    "bikini",
    "sexy",
    "hot girl",
    "thirst trap",
    "cosplay",
    "fetish",
}


def _normalize_terms(values: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        text = str(value or "").strip().lower()
        if text:
            normalized.add(text)
    return normalized


def _keyword_terms(keyword: str) -> set[str]:
    blob = keyword.strip().lower()
    terms = set(BASE_POSITIVE_TERMS)
    if "wearable" in blob:
        terms.update({"wearable", "hands free", "portable"})
    if "manual" in blob:
        terms.update({"manual", "hand pump"})
    if "bottle" in blob:
        terms.update({"bottle", "bottles", "feeding bottle"})
    if "baby" in blob:
        terms.update({"baby", "newborn", "infant"})
    for token in blob.replace("-", " ").split():
        if len(token) >= 3:
            terms.add(token)
    return terms


def _text_blob(record: TikTokVideoRecord) -> str:
    parts = [
        record.caption,
        record.author_name,
        record.music_title,
        " ".join(record.hashtags),
        record.source_keyword,
    ]
    return " ".join(part for part in parts if part).lower()


def review_record(record: TikTokVideoRecord, *, min_score: int = 1) -> ReviewedTikTokVideoRecord:
    text = _text_blob(record)
    keyword_terms = _keyword_terms(record.source_keyword)
    reasons: list[str] = []
    score = 0

    matches = sorted(term for term in keyword_terms if term in text)
    if matches:
        score += min(4, len(matches))
        reasons.append(f"matched_terms:{','.join(matches[:6])}")

    if record.hashtags:
        hash_terms = _normalize_terms(record.hashtags)
        matched_tags = sorted(tag for tag in hash_terms if any(term in tag for term in keyword_terms))
        if matched_tags:
            score += 2
            reasons.append(f"matched_hashtags:{','.join(matched_tags[:4])}")

    if record.like_count >= 100:
        score += 1
        reasons.append("engagement:like_count>=100")
    if record.comment_count >= 10:
        score += 1
        reasons.append("engagement:comment_count>=10")

    if record.caption.strip():
        score += 1
        reasons.append("has_caption")

    blocked = sorted(term for term in NEGATIVE_TERMS if term in text)
    if blocked:
        score -= 4
        reasons.append(f"negative_terms:{','.join(blocked[:4])}")

    keep = score >= min_score and not blocked
    if not keep and not blocked and not matches:
        reasons.append("insufficient_product_relevance")

    return ReviewedTikTokVideoRecord(
        **record.model_dump(mode="python"),
        clean_status="kept" if keep else "dropped",
        relevance_score=score,
        clean_reasons=reasons,
    )


def review_records(
    records: list[TikTokVideoRecord],
    *,
    min_score: int = 1,
) -> tuple[list[ReviewedTikTokVideoRecord], list[ReviewedTikTokVideoRecord]]:
    kept: list[ReviewedTikTokVideoRecord] = []
    dropped: list[ReviewedTikTokVideoRecord] = []
    for record in records:
        reviewed = review_record(record, min_score=min_score)
        if reviewed.clean_status == "kept":
            kept.append(reviewed)
        else:
            dropped.append(reviewed)
    return kept, dropped
