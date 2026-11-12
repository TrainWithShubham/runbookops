"""Persistent admission limits for presenter-initiated investigations."""

import datetime
import os
import sqlite3

from fastapi import HTTPException


class RunBudget:
    def __init__(self, path, runtime):
        self.path, self.runtime = path, runtime
        self.limit = int(os.getenv("RUNBOOKOPS_PRESENTER_DAILY_RUNS", "20"))
        if not 1 <= self.limit <= 1000:
            raise ValueError("Daily presenter runs must be between 1 and 1000")

    def admit(self):
        if os.getenv("RUNBOOKOPS_LIVE_ENABLED", "true").lower() != "true":
            raise HTTPException(503, "Live investigations are disabled; saved work remains readable")
        day = datetime.datetime.now(datetime.UTC).date().isoformat()
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs (runtime TEXT, day TEXT, count INTEGER, PRIMARY KEY(runtime, day))"
            )
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT count FROM runs WHERE runtime=? AND day=?", (self.runtime, day)
            ).fetchone()
            count = row[0] if row else 0
            if count >= self.limit:
                raise HTTPException(429, "Daily presenter run allowance reached; try again tomorrow (UTC)")
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(runtime, day) DO UPDATE SET count=excluded.count",
                (self.runtime, day, count + 1),
            )
