"""Seed demo devices into the configured SQLite DB (idempotent)."""
from __future__ import annotations

import os

from indusmon.app import seed_demo
from indusmon.config import settings
from indusmon.db import Database


def main() -> None:
    db = Database(settings.db)
    seed_demo(db)
    n = db.execute("SELECT COUNT(*) AS c FROM devices").fetchone()["c"]
    print(f"seeded/ensured demo devices; total devices={n} db={settings.db}")
    db.close()


if __name__ == "__main__":
    main()
