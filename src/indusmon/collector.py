from __future__ import annotations

import logging
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .alerts import evaluate_and_store
from .models import now_ms

logger = logging.getLogger(__name__)


def decode_registers(regs: list[int], data_type: str, scale: float, offset: float) -> float:
    if data_type == "uint16":
        raw = regs[0] & 0xFFFF
    elif data_type == "int16":
        raw = regs[0] if regs[0] < 32768 else regs[0] - 65536
    elif data_type == "float32":
        if len(regs) < 2:
            raise ValueError("float32 needs 2 registers")
        packed = struct.pack(">HH", regs[0] & 0xFFFF, regs[1] & 0xFFFF)
        raw = struct.unpack(">f", packed)[0]
    else:
        raise ValueError(f"unsupported data_type: {data_type}")
    return raw * scale + offset


@dataclass
class CollectorStats:
    poll_rounds: int = 0
    points_written: int = 0
    comm_errors: int = 0
    started_at: float = field(default_factory=time.time)


class Collector:
    """Polls each enabled device via Modbus TCP and writes readings."""

    def __init__(
        self,
        conn,
        device_loader: Callable[[], list[dict[str, Any]]],
        client_factory: Callable[[str, int], Any] | None = None,
    ) -> None:
        self.conn = conn
        self.device_loader = device_loader
        self.client_factory = client_factory or self._default_client_factory
        self.stats = CollectorStats()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fail_counts: dict[str, int] = {}

    @staticmethod
    def _default_client_factory(host: str, port: int):
        from pymodbus.client import ModbusTcpClient

        return ModbusTcpClient(host=host, port=port, timeout=2.0)

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="indusmon-collector", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        next_due: dict[str, float] = {}
        while not self._stop.is_set():
            devices = [d for d in self.device_loader() if d.get("enabled")]
            now = time.monotonic()
            for dev in devices:
                due = next_due.get(dev["id"], 0.0)
                if now < due:
                    continue
                interval = max(dev.get("poll_interval_ms", 1000) / 1000.0, 0.05)
                next_due[dev["id"]] = now + interval
                try:
                    self.poll_device(dev)
                    self._fail_counts[dev["id"]] = 0
                except Exception as exc:  # noqa: BLE001
                    self.stats.comm_errors += 1
                    self._fail_counts[dev["id"]] = self._fail_counts.get(dev["id"], 0) + 1
                    if self._fail_counts[dev["id"]] in (1, 10, 30):
                        logger.warning(
                            "comm error device=%s count=%s err=%s",
                            dev["id"],
                            self._fail_counts[dev["id"]],
                            exc,
                        )
            self._stop.wait(0.05)

    def poll_device(self, dev: dict[str, Any]) -> int:
        tags = dev.get("tags") or []
        if not tags:
            return 0
        max_reg = max(t["register"] + (2 if t["data_type"] == "float32" else 1) for t in tags)
        count = max(max_reg, 1)
        client = self.client_factory(dev["host"], int(dev["port"]))
        try:
            connected = client.connect()
            if not connected:
                raise ConnectionError(f"cannot connect {dev['host']}:{dev['port']}")
            # pymodbus 3.7 client uses slave=
            try:
                rr = client.read_holding_registers(0, count=count, slave=int(dev["unit_id"]))
            except TypeError:
                rr = client.read_holding_registers(0, count=count, device_id=int(dev["unit_id"]))
            if rr is None or rr.isError():
                raise IOError(f"modbus error: {rr}")
            regs = list(rr.registers)
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass

        ts = now_ms()
        points: list[tuple] = []
        for t in tags:
            need = 2 if t["data_type"] == "float32" else 1
            if t["register"] + need > len(regs):
                continue
            window = regs[t["register"] : t["register"] + need]
            value = decode_registers(window, t["data_type"], t["scale"], t["offset"])
            # If simulator stored raw*100 as int16, tags should use scale=0.01.
            points.append((ts, dev["id"], t["name"], float(value), 0, t))
        self._write_points(points)
        self.stats.poll_rounds += 1
        return len(points)

    def _write_points(self, points: list[tuple]) -> None:
        if not points:
            return
        self.conn.executemany(
            "INSERT INTO readings(ts, device_id, tag, value, quality) VALUES (?,?,?,?,?)",
            [(p[0], p[1], p[2], p[3], p[4]) for p in points],
        )
        self.conn.commit()
        self.stats.points_written += len(points)
        for _, device_id, tag, value, _q, meta in points:
            evaluate_and_store(self.conn, device_id, tag, value, meta)
