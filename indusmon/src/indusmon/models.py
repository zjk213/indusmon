from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field


def now_ms() -> int:
    return int(time.time() * 1000)


class TagIn(BaseModel):
    name: str
    register: int = Field(ge=0, le=65535)
    data_type: Literal["uint16", "int16", "float32"] = "uint16"
    scale: float = 1.0
    offset: float = 0.0
    unit: str = ""
    limit_hi: float | None = None
    limit_hihi: float | None = None
    limit_lo: float | None = None

    model_config = {"protected_namespaces": ()}


class TagOut(TagIn):
    id: int
    device_id: str


class DeviceIn(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    name: str
    host: str = "127.0.0.1"
    port: int = 5020
    unit_id: int = 1
    poll_interval_ms: int = 1000
    enabled: bool = True
    tags: list[TagIn] = Field(default_factory=list)


class DevicePatch(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    unit_id: int | None = None
    poll_interval_ms: int | None = None
    enabled: bool | None = None


class DeviceOut(BaseModel):
    id: str
    name: str
    host: str
    port: int
    unit_id: int
    poll_interval_ms: int
    enabled: bool
    created_at: str
    tags: list[TagOut] = Field(default_factory=list)


class ReadingPoint(BaseModel):
    ts: int
    device_id: str
    tag: str
    value: float
    quality: int = 0
    unit: str = ""


class LatestBundle(BaseModel):
    ts: int
    readings: list[ReadingPoint]


class AlertOut(BaseModel):
    id: int
    ts: int
    device_id: str
    tag: str
    level: Literal["hi", "hihi", "lo"]
    value: float
    limit: float
    state: Literal["active", "cleared", "acked"]
    cleared_ts: int | None = None


class SpikeRequest(BaseModel):
    device_id: str
    tag: str
    value: float
    duration_s: float = 5.0


class MetricsOut(BaseModel):
    uptime_s: float
    poll_rounds: int
    points_written: int
    comm_errors: int
    active_alerts: int
    devices_enabled: int
