# -*- coding: utf-8 -*-
"""The ledger: what was built, from what, with which results, and what
happened to it afterwards (deployment plan §4.2; review §7, split into the
release bill of materials — prod/release_manifest.json — the build
specification — the register — per-report attestations, the publication
index and this append-only ledger of jobs and events).

SQLite, one file per release root, written by ONE coordinator process (the
runner's parent process or a checks/publish command run on the same VM);
workers return results to the coordinator and never open the database. WAL
mode. The SQL is plain enough that a PostgreSQL connection could replace
``sqlite3`` behind ``connect()`` if Sport Wales wants a queryable register.

    python -m prod.ledger status <ledger.sqlite> [--release v6.0]
    python -m prod.ledger export <ledger.sqlite> <out_dir>        # jobs.csv, attestations.json, events.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, release TEXT NOT NULL, started TEXT NOT NULL, finished TEXT,
  host TEXT, dataset_sha256 TEXT, manifest_sha256 TEXT, params TEXT);
CREATE TABLE IF NOT EXISTS jobs (
  release TEXT NOT NULL, school_id TEXT NOT NULL, slug TEXT NOT NULL, family TEXT NOT NULL,
  status TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0, started TEXT, finished TEXT,
  host TEXT, run_id TEXT, error TEXT, seconds REAL, mode TEXT,
  PRIMARY KEY (release, school_id));
CREATE TABLE IF NOT EXISTS attestations (
  release TEXT NOT NULL, school_id TEXT NOT NULL, json TEXT NOT NULL, recorded TEXT NOT NULL,
  PRIMARY KEY (release, school_id));
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, release TEXT, school_id TEXT,
  kind TEXT NOT NULL, detail TEXT);
"""
STATUSES = ("pending", "building", "built", "failed", "staged", "verified", "published", "withdrawn", "held")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(SCHEMA)
    con.row_factory = sqlite3.Row
    return con


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.con = connect(path)

    # ---- runs ---------------------------------------------------------------
    def start_run(self, run_id: str, release: str, host: str, dataset_sha256: str, manifest_sha256: str, params: dict):
        self.con.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?)",
                         (run_id, release, now(), None, host, dataset_sha256, manifest_sha256, json.dumps(params)))
        self.event(release, None, "run.start", run_id)
        self.con.commit()

    def finish_run(self, run_id: str, release: str, summary: dict):
        self.con.execute("UPDATE runs SET finished=? WHERE run_id=?", (now(), run_id))
        self.event(release, None, "run.finish", json.dumps(summary))
        self.con.commit()

    # ---- jobs ---------------------------------------------------------------
    def ensure_job(self, release: str, school_id: str, slug: str, family: str, status: str = "pending"):
        self.con.execute("INSERT OR IGNORE INTO jobs (release, school_id, slug, family, status) VALUES (?,?,?,?,?)",
                         (release, school_id, slug, family, status))
        self.con.commit()

    def job(self, release: str, school_id: str):
        r = self.con.execute("SELECT * FROM jobs WHERE release=? AND school_id=?", (release, school_id)).fetchone()
        return dict(r) if r else None

    def jobs(self, release: str, status: str | None = None):
        q = "SELECT * FROM jobs WHERE release=?" + (" AND status=?" if status else "") + " ORDER BY school_id"
        return [dict(r) for r in self.con.execute(q, (release, status) if status else (release,))]

    def mark(self, release: str, school_id: str, status: str, host: str | None = None, run_id: str | None = None,
             error: str | None = None, seconds: float | None = None, mode: str | None = None, started: bool = False):
        assert status in STATUSES, status
        if started:
            self.con.execute("UPDATE jobs SET status=?, attempt=attempt+1, started=?, finished=NULL, host=?, run_id=?, error=NULL "
                             "WHERE release=? AND school_id=?", (status, now(), host, run_id, release, school_id))
        else:
            self.con.execute("UPDATE jobs SET status=?, finished=?, error=?, seconds=COALESCE(?, seconds), mode=COALESCE(?, mode) "
                             "WHERE release=? AND school_id=?", (status, now(), error, seconds, mode, release, school_id))
        self.event(release, school_id, "job." + status, error or "")
        self.con.commit()

    # ---- attestations -------------------------------------------------------
    def attest(self, release: str, school_id: str, attestation: dict):
        self.con.execute("INSERT OR REPLACE INTO attestations VALUES (?,?,?,?)",
                         (release, school_id, json.dumps(attestation, ensure_ascii=False, sort_keys=True), now()))
        self.con.commit()

    def attestation(self, release: str, school_id: str) -> dict | None:
        r = self.con.execute("SELECT json FROM attestations WHERE release=? AND school_id=?", (release, school_id)).fetchone()
        return json.loads(r[0]) if r else None

    def attestations(self, release: str) -> dict:
        return {r[0]: json.loads(r[1]) for r in self.con.execute(
            "SELECT school_id, json FROM attestations WHERE release=? ORDER BY school_id", (release,))}

    # ---- events -------------------------------------------------------------
    def event(self, release: str | None, school_id: str | None, kind: str, detail: str = ""):
        self.con.execute("INSERT INTO events (ts, release, school_id, kind, detail) VALUES (?,?,?,?,?)",
                         (now(), release, school_id, kind, detail))
        self.con.commit()

    # ---- reporting ----------------------------------------------------------
    def status(self, release: str | None = None) -> dict:
        q = "SELECT release, status, COUNT(*) n, ROUND(AVG(seconds),1) avg_s, MAX(seconds) max_s FROM jobs"
        args = ()
        if release:
            q += " WHERE release=?"; args = (release,)
        q += " GROUP BY release, status ORDER BY release, status"
        return {"jobs": [dict(r) for r in self.con.execute(q, args)],
                "runs": [dict(r) for r in self.con.execute("SELECT run_id, release, started, finished, host FROM runs ORDER BY started")]}

    def export(self, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        for table, fname in (("jobs", "jobs.csv"), ("events", "events.csv"), ("runs", "runs.csv")):
            rows = self.con.execute(f"SELECT * FROM {table}").fetchall()
            with (out_dir / fname).open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if rows:
                    w.writerow(rows[0].keys())
                    w.writerows([list(r) for r in rows])
        att = {r[0] + "|" + r[1]: json.loads(r[2]) for r in self.con.execute("SELECT release, school_id, json FROM attestations")}
        (out_dir / "attestations.json").write_text(json.dumps(att, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["status", "export"]); ap.add_argument("ledger"); ap.add_argument("arg", nargs="?")
    ap.add_argument("--release")
    a = ap.parse_args(argv)
    L = Ledger(Path(a.ledger))
    if a.cmd == "status":
        print(json.dumps(L.status(a.release), indent=1))
    else:
        L.export(Path(a.arg or "ledger_export")); print("exported")


if __name__ == "__main__":
    main()
