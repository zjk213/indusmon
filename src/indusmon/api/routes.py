from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..models import (
    AlertOut,
    DeviceIn,
    DeviceOut,
    DevicePatch,
    LatestBundle,
    MetricsOut,
    ReadingPoint,
    SpikeRequest,
    TagOut,
    now_ms,
)
from ..alerts import set_spike

router = APIRouter(prefix="/api/v1")


def _db(request: Request):
    return request.app.state.db


def _collector(request: Request):
    return request.app.state.collector


def load_devices(conn, device_id: str | None = None) -> list[dict[str, Any]]:
    if device_id:
        rows = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM devices ORDER BY id").fetchall()
    devices = []
    for r in rows:
        d = dict(r)
        d["enabled"] = bool(d["enabled"])
        tags = conn.execute("SELECT * FROM tags WHERE device_id=? ORDER BY register", (d["id"],)).fetchall()
        d["tags"] = [dict(t) for t in tags]
        devices.append(d)
    return devices


def _device_out(d: dict[str, Any]) -> DeviceOut:
    return DeviceOut(
        id=d["id"],
        name=d["name"],
        host=d["host"],
        port=d["port"],
        unit_id=d["unit_id"],
        poll_interval_ms=d["poll_interval_ms"],
        enabled=bool(d["enabled"]),
        created_at=d["created_at"],
        tags=[TagOut(**{k: t[k] for k in t.keys()}) for t in d.get("tags", [])],
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(request: Request) -> list[DeviceOut]:
    return [_device_out(d) for d in load_devices(_db(request))]


@router.post("/devices", response_model=DeviceOut, status_code=201)
def create_device(request: Request, body: DeviceIn) -> DeviceOut:
    conn = _db(request)
    exists = conn.execute("SELECT 1 FROM devices WHERE id=?", (body.id,)).fetchone()
    if exists:
        raise HTTPException(409, f"device exists: {body.id}")
    conn.execute(
        "INSERT INTO devices(id,name,host,port,unit_id,poll_interval_ms,enabled,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (
            body.id,
            body.name,
            body.host,
            body.port,
            body.unit_id,
            body.poll_interval_ms,
            1 if body.enabled else 0,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ),
    )
    for t in body.tags:
        conn.execute(
            "INSERT INTO tags(device_id,name,register,data_type,scale,offset,unit,limit_hi,limit_hihi,limit_lo) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                body.id,
                t.name,
                t.register,
                t.data_type,
                t.scale,
                t.offset,
                t.unit,
                t.limit_hi,
                t.limit_hihi,
                t.limit_lo,
            ),
        )
    conn.commit()
    return _device_out(load_devices(conn, body.id)[0])


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def patch_device(request: Request, device_id: str, body: DevicePatch) -> DeviceOut:
    conn = _db(request)
    if not conn.execute("SELECT 1 FROM devices WHERE id=?", (device_id,)).fetchone():
        raise HTTPException(404, "device not found")
    fields = body.model_dump(exclude_none=True)
    if "enabled" in fields:
        fields["enabled"] = 1 if fields["enabled"] else 0
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE devices SET {sets} WHERE id=?", (*fields.values(), device_id))
        conn.commit()
    return _device_out(load_devices(conn, device_id)[0])


@router.get("/readings", response_model=list[ReadingPoint])
def query_readings(
    request: Request,
    device_id: str | None = None,
    tag: str | None = None,
    from_ms: int | None = Query(default=None, alias="from"),
    to_ms: int | None = Query(default=None, alias="to"),
    limit: int = Query(default=1000, ge=1, le=20000),
) -> list[ReadingPoint]:
    if from_ms is not None and to_ms is not None and from_ms > to_ms:
        raise HTTPException(400, "from > to")
    sql = "SELECT ts, device_id, tag, value, quality FROM readings WHERE 1=1"
    args: list[Any] = []
    if device_id:
        sql += " AND device_id=?"
        args.append(device_id)
    if tag:
        sql += " AND tag=?"
        args.append(tag)
    if from_ms is not None:
        sql += " AND ts>=?"
        args.append(from_ms)
    if to_ms is not None:
        sql += " AND ts<=?"
        args.append(to_ms)
    sql += " ORDER BY ts DESC LIMIT ?"
    args.append(limit)
    rows = _db(request).execute(sql, args).fetchall()
    return [ReadingPoint(**dict(r)) for r in reversed(rows)]


@router.get("/readings/latest", response_model=LatestBundle)
def latest_readings(request: Request) -> LatestBundle:
    conn = _db(request)
    rows = conn.execute(
        """
        SELECT r.ts, r.device_id, r.tag, r.value, r.quality, COALESCE(t.unit,'') AS unit
        FROM readings r
        LEFT JOIN tags t ON t.device_id=r.device_id AND t.name=r.tag
        WHERE r.ts = (
          SELECT MAX(r2.ts) FROM readings r2
          WHERE r2.device_id=r.device_id AND r2.tag=r.tag
        )
        ORDER BY r.device_id, r.tag
        """
    ).fetchall()
    points = [ReadingPoint(**dict(r)) for r in rows]
    return LatestBundle(ts=now_ms(), readings=points)


@router.get("/series")
def series(
    request: Request,
    device_id: str,
    tag: str,
    from_ms: int | None = Query(default=None, alias="from"),
    to_ms: int | None = Query(default=None, alias="to"),
    max_points: int = Query(default=500, ge=10, le=5000),
) -> dict[str, Any]:
    if from_ms is not None and to_ms is not None and from_ms > to_ms:
        raise HTTPException(400, "from > to")
    sql = "SELECT ts, value FROM readings WHERE device_id=? AND tag=?"
    args: list[Any] = [device_id, tag]
    if from_ms is not None:
        sql += " AND ts>=?"
        args.append(from_ms)
    if to_ms is not None:
        sql += " AND ts<=?"
        args.append(to_ms)
    sql += " ORDER BY ts ASC"
    rows = _db(request).execute(sql, args).fetchall()
    if len(rows) > max_points:
        step = len(rows) // max_points
        rows = rows[::step]
    return {
        "device_id": device_id,
        "tag": tag,
        "points": [{"ts": r["ts"], "value": r["value"]} for r in rows],
    }


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    request: Request,
    state: str | None = None,
    device_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[AlertOut]:
    sql = "SELECT * FROM alerts WHERE 1=1"
    args: list[Any] = []
    if state:
        sql += " AND state=?"
        args.append(state)
    if device_id:
        sql += " AND device_id=?"
        args.append(device_id)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    rows = _db(request).execute(sql, args).fetchall()
    return [AlertOut(**dict(r)) for r in rows]


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
def ack_alert(request: Request, alert_id: int) -> AlertOut:
    conn = _db(request)
    row = conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
    if not row:
        raise HTTPException(404, "alert not found")
    conn.execute("UPDATE alerts SET state='acked' WHERE id=?", (alert_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
    return AlertOut(**dict(row))


@router.post("/sim/spike")
def sim_spike(request: Request, body: SpikeRequest) -> dict[str, Any]:
    conn = _db(request)
    try:
        set_spike(conn, body.device_id, body.tag, body.value, body.duration_s)
    except KeyError as exc:
        raise HTTPException(404, f"not found: {exc}") from exc
    return {
        "ok": True,
        "device_id": body.device_id,
        "tag": body.tag,
        "value": body.value,
        "duration_s": body.duration_s,
    }


@router.get("/metrics", response_model=MetricsOut)
def metrics(request: Request) -> MetricsOut:
    col = _collector(request)
    conn = _db(request)
    active = conn.execute("SELECT COUNT(*) AS c FROM alerts WHERE state='active'").fetchone()["c"]
    enabled = conn.execute("SELECT COUNT(*) AS c FROM devices WHERE enabled=1").fetchone()["c"]
    return MetricsOut(
        uptime_s=round(time.time() - col.stats.started_at, 1),
        poll_rounds=col.stats.poll_rounds,
        points_written=col.stats.points_written,
        comm_errors=col.stats.comm_errors,
        active_alerts=int(active),
        devices_enabled=int(enabled),
    )


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    async def gen():
        while True:
            if await request.is_disconnected():
                break
            try:
                # run blocking latest query in thread
                latest = await asyncio.to_thread(latest_readings, request)
                payload = latest.model_dump()
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as exc:  # noqa: BLE001
                yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")
