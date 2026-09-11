from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusServerContext,
        ModbusSlaveContext,
    )
    from pymodbus.server import StartTcpServer
except ImportError:  # pragma: no cover
    StartTcpServer = None  # type: ignore
    ModbusServerContext = None  # type: ignore


@dataclass
class SimPoint:
    register: int
    kind: str  # sine | ramp | noise | digital | hold
    base: float = 0.0
    amp: float = 1.0
    period_s: float = 30.0
    gain: float = 100.0  # stored = round(raw * gain); tag scale should be 1/gain


@dataclass
class SimulatorProfile:
    unit_id: int
    points: list[SimPoint] = field(default_factory=list)


def default_profiles() -> list[SimulatorProfile]:
    """Two virtual devices on one TCP server (different unit ids)."""
    boiler = SimulatorProfile(
        unit_id=1,
        points=[
            SimPoint(0, "sine", base=165.0, amp=12.0, period_s=45.0),  # steam temp °C
            SimPoint(1, "sine", base=0.85, amp=0.08, period_s=60.0),  # pressure MPa
            SimPoint(2, "sine", base=55.0, amp=8.0, period_s=90.0),  # level %
            SimPoint(3, "digital", gain=1.0),  # burner
        ],
    )
    line = SimulatorProfile(
        unit_id=2,
        points=[
            SimPoint(0, "sine", base=12.0, amp=3.0, period_s=20.0),  # motor current A
            SimPoint(1, "ramp", base=1450.0, amp=40.0, period_s=120.0, gain=1.0),  # rpm
            SimPoint(2, "noise", base=2.5, amp=0.4, period_s=10.0),  # vibration mm/s
            SimPoint(3, "ramp", base=0.0, amp=1.0, period_s=5.0, gain=1.0),  # counter
        ],
    )
    return [boiler, line]


class RegisterBank:
    """Process-local holding registers + spike overrides, thread-safe enough for MVP."""

    def __init__(self, profiles: list[SimulatorProfile] | None = None) -> None:
        self.profiles = profiles or default_profiles()
        self.t0 = time.time()
        self._spikes: dict[tuple[int, int], tuple[float, int]] = {}

    def apply_spike(self, unit_id: int, register: int, raw: float, until_ms: int) -> None:
        self._spikes[(unit_id, register)] = (raw, until_ms)

    def clear_expired(self, now_ms: int | None = None) -> None:
        now = now_ms or int(time.time() * 1000)
        dead = [k for k, (_, until) in self._spikes.items() if until <= now]
        for k in dead:
            del self._spikes[k]

    def _wave(self, p: SimPoint, t: float) -> float:
        if p.kind == "sine":
            return p.base + p.amp * math.sin(2 * math.pi * t / max(p.period_s, 0.001))
        if p.kind == "ramp":
            frac = (t % p.period_s) / p.period_s
            return p.base + p.amp * frac
        if p.kind == "noise":
            n = math.sin(t * 12.9898 + p.register * 78.233) * 43758.5453
            frac = n - math.floor(n)
            return p.base + p.amp * (frac - 0.5) * 2
        if p.kind == "digital":
            return 1.0 if (int(t / 15) % 2 == 0) else 0.0
        return p.base

    def raw_values(self, unit_id: int, count: int = 32) -> list[int]:
        self.clear_expired()
        t = time.time() - self.t0
        vals = [0] * count
        profile = next((p for p in self.profiles if p.unit_id == unit_id), None)
        if not profile:
            return vals
        for p in profile.points:
            if p.register < 0 or p.register >= count:
                continue
            override = self._spikes.get((unit_id, p.register))
            if override is not None:
                # spike stores already-gained register value
                vals[p.register] = int(max(-32768, min(32767, override[0])))
                continue
            raw = self._wave(p, t)
            if p.kind == "digital":
                vals[p.register] = 1 if raw >= 0.5 else 0
            else:
                stored = int(round(raw * p.gain))
                vals[p.register] = max(-32768, min(32767, stored))
        return vals

    def to_datastore(self):
        if ModbusSlaveContext is None:
            raise RuntimeError("pymodbus is not installed")
        bank = self

        def make_block(unit_id: int):
            class _Block(ModbusSequentialDataBlock):
                def getValues(self, address, count=1):  # noqa: N802
                    end = address + count
                    raw = bank.raw_values(unit_id, max(end, 1) + 8)
                    return raw[address:end]

                def setValues(self, address, values):  # noqa: N802
                    return

            return _Block(0, [0] * 64)

        slaves = {}
        for prof in self.profiles:
            slaves[prof.unit_id] = ModbusSlaveContext(
                hr=make_block(prof.unit_id), zero_mode=True
            )
        return ModbusServerContext(slaves=slaves, single=False)


_bank = RegisterBank()


def get_bank() -> RegisterBank:
    return _bank


def map_unit_tag_to_register(unit_id: int, tag: str) -> int | None:
    mapping = {
        (1, "steam_temp"): 0,
        (1, "pressure"): 1,
        (1, "level"): 2,
        (1, "burner"): 3,
        (2, "motor_current"): 0,
        (2, "rpm"): 1,
        (2, "vibration"): 2,
        (2, "parts_count"): 3,
    }
    return mapping.get((unit_id, tag))


def tag_gain(unit_id: int, tag: str) -> float:
    """Match SimPoint.gain so spike values convert to registers correctly."""
    bank = get_bank()
    profile = next((p for p in bank.profiles if p.unit_id == unit_id), None)
    if not profile:
        return 100.0
    reg = map_unit_tag_to_register(unit_id, tag)
    if reg is None:
        return 100.0
    for p in profile.points:
        if p.register == reg:
            return p.gain
    return 100.0


def start_simulator(host: str = "127.0.0.1", port: int = 5020):
    """Start Modbus TCP server in a daemon thread. Returns the thread."""
    import threading

    if StartTcpServer is None:
        raise RuntimeError("pymodbus is required for the simulator")

    context = get_bank().to_datastore()

    def _run() -> None:
        logger.info("Modbus simulator listening on %s:%s", host, port)
        try:
            StartTcpServer(context=context, address=(host, port))
        except Exception as exc:  # noqa: BLE001
            logger.error("Simulator stopped: %s", exc)

    th = threading.Thread(target=_run, name="indusmon-sim", daemon=True)
    th.start()
    return th
