from __future__ import annotations

from typing import Any

from .models import now_ms

HYSTERESIS = 0.02  # 2%


def _clear_ok(value: float, limit: float, level: str) -> bool:
    if level in ("hi", "hihi"):
        return value <= limit * (1 - HYSTERESIS) if limit >= 0 else value <= limit * (1 + HYSTERESIS)
    # lo
    return value >= limit * (1 + HYSTERESIS) if limit >= 0 else value >= limit * (1 - HYSTERESIS)


def evaluate_level(value: float, meta: dict[str, Any]) -> tuple[str, float] | None:
    """Return (level, limit) if a threshold is breached; priority hihi > hi > lo."""
    hihi = meta.get("limit_hihi")
    hi = meta.get("limit_hi")
    lo = meta.get("limit_lo")
    if hihi is not None and value >= float(hihi):
        return "hihi", float(hihi)
    if hi is not None and value >= float(hi):
        return "hi", float(hi)
    if lo is not None and value <= float(lo):
        return "lo", float(lo)
    return None


def _active_alert(conn, device_id: str, tag: str, level: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM alerts WHERE device_id=? AND tag=? AND level=? AND state='active' ORDER BY id DESC LIMIT 1",
        (device_id, tag, level),
    ).fetchone()
    return dict(row) if row else None


def evaluate_and_store(conn, device_id: str, tag: str, value: float, meta: dict[str, Any]) -> None:
    """Evaluate thresholds and insert/clear alerts. Caller holds DB lock if needed."""
    breach = evaluate_level(value, meta)
    # Clear any active alerts that recovered (check all configured levels)
    levels: list[tuple[str, Any]] = [
        ("hihi", meta.get("limit_hihi")),
        ("hi", meta.get("limit_hi")),
        ("lo", meta.get("limit_lo")),
    ]
    for level, limit in levels:
        if limit is None:
            continue
        active = _active_alert(conn, device_id, tag, level)
        if not active:
            continue
        if breach and breach[0] == level:
            continue  # still active at this level
        if _clear_ok(value, float(limit), level):
            conn.execute(
                "UPDATE alerts SET state='cleared', cleared_ts=? WHERE id=?",
                (now_ms(), active["id"]),
            )
            conn.commit()

    if not breach:
        return
    level, limit = breach
    existing = _active_alert(conn, device_id, tag, level)
    if existing:
        return
    # higher priority supersedes lower active ones on same tag
    conn.execute(
        "UPDATE alerts SET state='cleared', cleared_ts=? WHERE device_id=? AND tag=? AND state='active' AND level!=?",
        (now_ms(), device_id, tag, level),
    )
    conn.execute(
        "INSERT INTO alerts(ts, device_id, tag, level, value, \"limit\", state) VALUES (?,?,?,?,?,?,'active')",
        (now_ms(), device_id, tag, level, value, limit),
    )
    conn.commit()


def set_spike(conn, device_id: str, tag: str, value: float, duration_s: float) -> None:
    from .simulator import get_bank, map_unit_tag_to_register, tag_gain

    row = conn.execute("SELECT unit_id FROM devices WHERE id=?", (device_id,)).fetchone()
    if not row:
        raise KeyError(device_id)
    unit_id = int(row["unit_id"])
    reg = map_unit_tag_to_register(unit_id, tag)
    if reg is None:
        raise KeyError(tag)
    until = now_ms() + int(duration_s * 1000)
    gain = tag_gain(unit_id, tag)
    raw_storage = int(round(value * gain))
    raw_storage = max(-32768, min(32767, raw_storage))
    get_bank().apply_spike(unit_id, reg, float(raw_storage), until)
    conn.execute(
        "INSERT INTO spikes(device_id, tag, value, until_ts) VALUES (?,?,?,?) "
        "ON CONFLICT(device_id, tag) DO UPDATE SET value=excluded.value, until_ts=excluded.until_ts",
        (device_id, tag, value, until),
    )
    conn.commit()
