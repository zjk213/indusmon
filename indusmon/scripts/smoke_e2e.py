"""End-to-end smoke: real sim + collector + alert path (no HTTP server)."""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

# isolated ports/db
os.environ["INDUSMON_SIM_PORT"] = "15030"
os.environ["INDUSMON_SEED_DEMO"] = "1"
os.environ["INDUSMON_POLL_MS"] = "200"

tmp = Path(tempfile.mkdtemp(prefix="indusmon-smoke-"))
os.environ["INDUSMON_DB"] = str(tmp / "smoke.db")

from indusmon.app import create_app, seed_demo  # noqa: E402
from indusmon.alerts import set_spike  # noqa: E402
from indusmon.config import settings  # noqa: E402
from indusmon.simulator import start_simulator  # noqa: E402

# reload settings after env
from importlib import reload  # noqa: E402
import indusmon.config as cfg  # noqa: E402
reload(cfg)
settings = cfg.settings

app = create_app(start_sim=False, start_collector=False)
conn = app.state.db
start_simulator(settings.sim_host, settings.sim_port)
time.sleep(0.3)
app.state.collector.start()
time.sleep(1.5)

n = conn.execute("SELECT COUNT(*) AS c FROM readings").fetchone()["c"]
print(f"readings after 1.5s: {n}")
assert n > 0, "collector wrote no points"

latest = conn.execute(
    "SELECT tag, value FROM readings WHERE device_id='boiler-01' AND tag='steam_temp' ORDER BY ts DESC LIMIT 1"
).fetchone()
print(f"latest steam_temp: {latest['value'] if latest else None}")
assert latest is not None
assert 100 < latest["value"] < 220, latest["value"]

set_spike(conn, "boiler-01", "steam_temp", 200.0, 5.0)
time.sleep(1.2)
alerts = conn.execute("SELECT * FROM alerts WHERE state='active'").fetchall()
print(f"active alerts after spike: {len(alerts)}")
assert alerts, "expected alert after spike"
print("level:", alerts[0]["level"], "value:", alerts[0]["value"])

app.state.collector.stop()
print("SMOKE OK")
