from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import load_devices, router
from .collector import Collector
from .config import settings
from .db import Database

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


def seed_demo(conn) -> None:
    if conn.execute("SELECT COUNT(*) AS c FROM devices").fetchone()["c"] > 0:
        return
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    devices = [
        (
            "boiler-01",
            "1# 蒸汽锅炉",
            1,
            [
                ("steam_temp", 0, "uint16", 0.01, 0.0, "°C", 175.0, 180.0, None),
                ("pressure", 1, "uint16", 0.01, 0.0, "MPa", 0.90, 0.95, None),
                ("level", 2, "uint16", 0.01, 0.0, "%", 70.0, 80.0, 30.0),
                ("burner", 3, "uint16", 1.0, 0.0, "", None, None, None),
            ],
        ),
        (
            "line-02",
            "2# 装配产线",
            2,
            [
                ("motor_current", 0, "uint16", 0.01, 0.0, "A", 16.0, 18.0, None),
                ("rpm", 1, "uint16", 1.0, 0.0, "rpm", None, None, None),
                ("vibration", 2, "uint16", 0.01, 0.0, "mm/s", 4.0, 5.5, None),
                ("parts_count", 3, "uint16", 1.0, 0.0, "pcs", None, None, None),
            ],
        ),
    ]
    for dev_id, name, unit_id, tags in devices:
        conn.execute(
            "INSERT INTO devices(id,name,host,port,unit_id,poll_interval_ms,enabled,created_at) "
            "VALUES (?,?,?,?,?,?,1,?)",
            (dev_id, name, settings.sim_host, settings.sim_port, unit_id, settings.poll_ms, created),
        )
        for name_t, reg, dtype, scale, offset, unit, hi, hihi, lo in tags:
            conn.execute(
                "INSERT INTO tags(device_id,name,register,data_type,scale,offset,unit,limit_hi,limit_hihi,limit_lo) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (dev_id, name_t, reg, dtype, scale, offset, unit, hi, hihi, lo),
            )
    conn.commit()
    logger.info("Seeded demo devices: boiler-01, line-02")


def create_app(start_sim: bool = True, start_collector: bool = True) -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_sim:
            from .simulator import start_simulator

            # port bind failure must abort startup (S2.13)
            start_simulator(settings.sim_host, settings.sim_port)
            logger.info("simulator started on %s:%s", settings.sim_host, settings.sim_port)
        if start_collector:
            app.state.collector.start()
            logger.info("collector started")
        yield
        app.state.collector.stop()
        try:
            app.state.db.close()
        except Exception:  # noqa: BLE001
            pass

    app = FastAPI(
        title="IndusMon",
        version="0.1.0",
        description="工业设备数采与监控平台",
        lifespan=lifespan,
    )
    app.state.db = Database(settings.db)
    app.state.collector = Collector(app.state.db, lambda: load_devices(app.state.db))
    app.state.started_at = time.time()

    if settings.seed_demo:
        seed_demo(app.state.db)

    app.include_router(router)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app
