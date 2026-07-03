"""多人协作：成片生产单线程队列（SeedDance 出片串行）。"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

AVG_PRODUCTION_SEC = 18 * 60
ACTIVE_GRACE_SEC = 120

_lock = threading.RLock()
_tickets: dict[str, dict[str, Any]] = {}
_order: list[str] = []
_current_id: str | None = None


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _now_ts() -> float:
    return time.time()


def _client_label(client_id: str) -> str:
    cid = (client_id or "unknown").strip()
    if len(cid) <= 4:
        return f"用户 {cid or '?'}"
    return f"用户 …{cid[-4:]}"


def _ticket_position(ticket_id: str) -> int:
    if ticket_id == _current_id:
        return 0
    try:
        return _order.index(ticket_id)
    except ValueError:
        return -1


def _running_elapsed_sec(ticket: dict[str, Any]) -> int:
    started = ticket.get("started_at_ts")
    if not started:
        return 0
    return max(0, int(_now_ts() - float(started)))


def _estimate_wait_sec(position: int, current: dict[str, Any] | None) -> int:
    if position <= 0:
        return 0
    ahead = max(0, position - 1)
    wait = ahead * AVG_PRODUCTION_SEC
    if current and current.get("status") == "running":
        remain = max(0, AVG_PRODUCTION_SEC - _running_elapsed_sec(current))
        wait += remain
    elif current and current.get("status") in ("active", "queued"):
        wait += AVG_PRODUCTION_SEC
    return wait


def _serialize_ticket(ticket_id: str, *, include_position: bool = True) -> dict[str, Any] | None:
    ticket = _tickets.get(ticket_id)
    if not ticket:
        return None
    current = _tickets.get(_current_id) if _current_id else None
    pos = _ticket_position(ticket_id) if include_position else ticket.get("position", 0)
    wait_sec = _estimate_wait_sec(pos, current) if pos > 0 else 0
    remain_sec = 0
    if ticket_id == _current_id and ticket.get("status") == "running":
        remain_sec = max(0, AVG_PRODUCTION_SEC - _running_elapsed_sec(ticket))
    payload = {
        "ticket_id": ticket_id,
        "slug": ticket.get("slug"),
        "label": ticket.get("label"),
        "client_id": ticket.get("client_id"),
        "client_label": ticket.get("client_label"),
        "status": ticket.get("status"),
        "position": pos,
        "wait_sec": wait_sec,
        "remain_sec": remain_sec,
        "joined_at": ticket.get("joined_at"),
        "started_at": ticket.get("started_at"),
        "finished_at": ticket.get("finished_at"),
        "message": ticket.get("message", ""),
    }
    return payload


def _cleanup_stale_locked() -> None:
    global _current_id
    if not _current_id:
        return
    ticket = _tickets.get(_current_id)
    if not ticket:
        _current_id = None
        return
    if ticket.get("status") not in ("active", "running"):
        _current_id = None
        return
    if ticket.get("status") == "active":
        active_ts = float(ticket.get("active_at_ts") or 0)
        if active_ts and (_now_ts() - active_ts) > ACTIVE_GRACE_SEC:
            ticket["status"] = "cancelled"
            ticket["message"] = "超时未开始，已移出队列"
            ticket["finished_at"] = _utc()
            _current_id = None
            if ticket_id in _order:
                _order.remove(ticket_id)


def _promote_next() -> None:
    global _current_id
    _cleanup_stale_locked()
    if _current_id:
        return
    while _order:
        next_id = _order[0]
        ticket = _tickets.get(next_id)
        if not ticket or ticket.get("status") == "cancelled":
            _order.pop(0)
            continue
        ticket["status"] = "active"
        ticket["active_at"] = _utc()
        ticket["active_at_ts"] = _now_ts()
        _current_id = next_id
        if _order and _order[0] == next_id:
            _order.pop(0)
        return


def queue_snapshot() -> dict[str, Any]:
    with _lock:
        _cleanup_stale_locked()
        items: list[dict[str, Any]] = []
        if _current_id:
            cur = _serialize_ticket(_current_id)
            if cur:
                items.append(cur)
        for tid in _order:
            if tid == _current_id:
                continue
            row = _serialize_ticket(tid)
            if row and row.get("status") != "cancelled":
                items.append(row)
        running = sum(1 for t in _tickets.values() if t.get("status") == "running")
        queued = sum(1 for t in _tickets.values() if t.get("status") in ("queued", "active"))
        return {
            "enabled": True,
            "avg_production_sec": AVG_PRODUCTION_SEC,
            "running": running,
            "queued": queued,
            "items": items,
        }


def join_queue(*, slug: str, label: str = "", client_id: str = "") -> dict[str, Any]:
    slug = (slug or "").strip()
    if not slug:
        raise ValueError("缺少项目 slug")
    ticket_id = uuid.uuid4().hex[:12]
    with _lock:
        for tid, existing in _tickets.items():
            if (
                existing.get("slug") == slug
                and existing.get("client_id") == client_id
                and existing.get("status") in ("queued", "active", "running")
            ):
                row = _serialize_ticket(tid) or {}
                return {
                    "ticket_id": tid,
                    "reused": True,
                    **row,
                    "queue": queue_snapshot(),
                }
        ticket = {
            "ticket_id": ticket_id,
            "slug": slug,
            "label": (label or slug).strip(),
            "client_id": (client_id or "anon").strip(),
            "client_label": _client_label(client_id),
            "status": "queued",
            "joined_at": _utc(),
            "joined_at_ts": _now_ts(),
            "active_at": None,
            "active_at_ts": None,
            "started_at": None,
            "started_at_ts": None,
            "finished_at": None,
            "message": "",
        }
        _tickets[ticket_id] = ticket
        _order.append(ticket_id)
        _promote_next()
        row = _serialize_ticket(ticket_id) or {}
        return {"ticket_id": ticket_id, "reused": False, **row, "queue": queue_snapshot()}


def ticket_status(ticket_id: str) -> dict[str, Any] | None:
    with _lock:
        _cleanup_stale_locked()
        if not _tickets.get(ticket_id):
            return None
        if _tickets[ticket_id].get("status") == "queued":
            _promote_next()
        row = _serialize_ticket(ticket_id)
        if not row:
            return None
        return {**row, "queue": queue_snapshot()}


def cancel_ticket(ticket_id: str, client_id: str = "") -> dict[str, Any]:
    with _lock:
        global _current_id
        ticket = _tickets.get(ticket_id)
        if not ticket:
            raise ValueError("排队号不存在")
        if client_id and ticket.get("client_id") != client_id:
            raise ValueError("无权取消此排队")
        if ticket.get("status") == "running":
            raise ValueError("生成中无法取消")
        ticket["status"] = "cancelled"
        ticket["finished_at"] = _utc()
        ticket["message"] = "已取消排队"
        if ticket_id in _order:
            _order.remove(ticket_id)
        if _current_id == ticket_id:
            _current_id = None
            _promote_next()
        return ticket_status(ticket_id) or {}


def assert_can_run(ticket_id: str, slug: str) -> None:
    _assert_can_run_unlocked(ticket_id, slug)


def _assert_can_run_unlocked(ticket_id: str, slug: str) -> None:
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise ValueError("无效的排队号，请重新点击生成视频")
    if ticket.get("slug") != slug:
        raise ValueError("排队号与当前项目不匹配")
    if ticket.get("status") == "cancelled":
        raise ValueError("排队已取消")
    if ticket_id != _current_id:
        pos = _ticket_position(ticket_id)
        raise RuntimeError(f"尚未轮到您，当前排队位置：第 {max(pos, 1)} 位")
    if ticket.get("status") not in ("active", "running"):
        raise RuntimeError("排队状态异常，请刷新后重试")


def mark_running(ticket_id: str, slug: str) -> None:
    with _lock:
        _assert_can_run_unlocked(ticket_id, slug)
        ticket = _tickets[ticket_id]
        if ticket.get("status") == "running":
            return
        ticket["status"] = "running"
        ticket["started_at"] = _utc()
        ticket["started_at_ts"] = _now_ts()
        if ticket_id in _order:
            _order.remove(ticket_id)


def complete_ticket(ticket_id: str, *, ok: bool = True, message: str = "") -> None:
    with _lock:
        global _current_id
        ticket = _tickets.get(ticket_id)
        if not ticket:
            return
        ticket["status"] = "done" if ok else "error"
        ticket["finished_at"] = _utc()
        if message:
            ticket["message"] = message
        if ticket_id in _order:
            _order.remove(ticket_id)
        if _current_id == ticket_id:
            _current_id = None
            _promote_next()
