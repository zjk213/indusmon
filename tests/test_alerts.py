from __future__ import annotations

from indusmon.alerts import evaluate_and_store, evaluate_level
from indusmon.db import connect


def test_evaluate_level_priority():
    meta = {"limit_hi": 10, "limit_hihi": 20, "limit_lo": 1}
    assert evaluate_level(25, meta) == ("hihi", 20.0)
    assert evaluate_level(15, meta) == ("hi", 10.0)
    assert evaluate_level(0.5, meta) == ("lo", 1.0)
    assert evaluate_level(5, meta) is None


def test_alert_active_and_hysteresis_clear(tmp_path):
    conn = connect(tmp_path / "t.db")
    meta = {"limit_hi": 10.0, "limit_hihi": 20.0, "limit_lo": None}
    evaluate_and_store(conn, "d1", "temp", 12.0, meta)
    row = conn.execute("SELECT * FROM alerts WHERE state='active'").fetchone()
    assert row is not None
    assert row["level"] == "hi"
    assert row["limit"] == 10.0

    # still above — no duplicate
    evaluate_and_store(conn, "d1", "temp", 12.5, meta)
    n = conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
    assert n == 1

    # within hysteresis (10 * 0.98 = 9.8) — still active at 9.9
    evaluate_and_store(conn, "d1", "temp", 9.9, meta)
    assert conn.execute("SELECT state FROM alerts WHERE id=1").fetchone()["state"] == "active"

    # clear
    evaluate_and_store(conn, "d1", "temp", 9.0, meta)
    assert conn.execute("SELECT state FROM alerts WHERE id=1").fetchone()["state"] == "cleared"


def test_hihi_supersedes_hi(tmp_path):
    conn = connect(tmp_path / "t.db")
    meta = {"limit_hi": 10.0, "limit_hihi": 20.0, "limit_lo": None}
    evaluate_and_store(conn, "d1", "temp", 12.0, meta)
    evaluate_and_store(conn, "d1", "temp", 25.0, meta)
    active = conn.execute("SELECT * FROM alerts WHERE state='active'").fetchall()
    assert len(active) == 1
    assert active[0]["level"] == "hihi"
