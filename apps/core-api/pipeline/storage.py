import json
import os
import sqlite3
from typing import Any

INIT_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS receipts(
  trace_id TEXT NOT NULL,
  hop INTEGER NOT NULL,
  ts TEXT NOT NULL,
  cid TEXT NOT NULL,
  canon TEXT NOT NULL,
  algo TEXT NOT NULL,
  prev_receipt_hash TEXT,
  policy_json TEXT NOT NULL,
  tenant TEXT NOT NULL,
  receipt_hash TEXT NOT NULL,
  PRIMARY KEY(trace_id, hop)
);
CREATE TABLE IF NOT EXISTS heads(
  trace_id TEXT PRIMARY KEY,
  last_hop INTEGER NOT NULL,
  last_receipt_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency(
  api_key TEXT NOT NULL,
  key TEXT NOT NULL,
  response_json TEXT NOT NULL,
  PRIMARY KEY(api_key, key)
);
CREATE TABLE IF NOT EXISTS usage_ledger(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_key TEXT NOT NULL,
  tenant TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  hop INTEGER NOT NULL,
  verified INTEGER NOT NULL,
  vex_units INTEGER NOT NULL,
  fu_tokens INTEGER NOT NULL,
  ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS billing_queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_key TEXT NOT NULL,
  stripe_item TEXT NOT NULL,
  units INTEGER NOT NULL,
  ts INTEGER NOT NULL,
  retries INTEGER NOT NULL DEFAULT 0
);
"""


class Storage:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self.path = path
        with self._conn() as c:
            c.executescript(INIT_SQL)

    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def get_head(self, trace_id: str):
        with self._conn() as c:
            row = c.execute(
                "SELECT trace_id,last_hop,last_receipt_hash FROM heads WHERE trace_id=?",
                (trace_id,),
            ).fetchone()
            return dict(row) if row else None

    def append_receipt(self, receipt: dict[str, Any], expected_prev: str | None) -> int:
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            head = c.execute(
                "SELECT trace_id,last_hop,last_receipt_hash FROM heads WHERE trace_id=?",
                (receipt["trace_id"],),
            ).fetchone()
            if head:
                if head["last_receipt_hash"] != expected_prev:
                    c.execute("ROLLBACK")
                    raise StorageConflict("prev_receipt_hash mismatch")
                hop = head["last_hop"] + 1
            else:
                if expected_prev is not None:
                    c.execute("ROLLBACK")
                    raise StorageConflict("unexpected prev_receipt_hash")
                hop = 1
            receipt["hop"] = hop
            c.execute(
                """INSERT INTO receipts(trace_id,hop,ts,cid,canon,algo,prev_receipt_hash,policy_json,tenant,receipt_hash)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    receipt["trace_id"],
                    hop,
                    receipt["ts"],
                    receipt["cid"],
                    receipt["canon"],
                    receipt["algo"],
                    receipt.get("prev_receipt_hash"),
                    json.dumps(receipt["policy"]),
                    receipt["tenant"],
                    receipt["receipt_hash"],
                ),
            )
            if head:
                c.execute(
                    "UPDATE heads SET last_hop=?, last_receipt_hash=? WHERE trace_id=?",
                    (hop, receipt["receipt_hash"], receipt["trace_id"]),
                )
            else:
                c.execute(
                    "INSERT INTO heads(trace_id,last_hop,last_receipt_hash) VALUES(?,?,?)",
                    (receipt["trace_id"], hop, receipt["receipt_hash"]),
                )
            c.execute("COMMIT")
            return hop

    def get_chain(self, trace_id: str):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM receipts WHERE trace_id=? ORDER BY hop ASC", (trace_id,)
            ).fetchall()
            out = []
            for r in rows:
                out.append(
                    {
                        "trace_id": r["trace_id"],
                        "hop": r["hop"],
                        "ts": r["ts"],
                        "cid": r["cid"],
                        "canon": r["canon"],
                        "algo": r["algo"],
                        "prev_receipt_hash": r["prev_receipt_hash"],
                        "policy": json.loads(r["policy_json"]),
                        "tenant": r["tenant"],
                        "receipt_hash": r["receipt_hash"],
                    }
                )
            return out

    def cache_idempotent(self, api_key: str, idem_key: str, response_json: dict[str, Any]):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO idempotency(api_key,key,response_json) VALUES(?,?,?)",
                (api_key, idem_key, json.dumps(response_json)),
            )

    def get_idempotent(self, api_key: str, idem_key: str):
        with self._conn() as c:
            row = c.execute(
                "SELECT response_json FROM idempotency WHERE api_key=? AND key=?",
                (api_key, idem_key),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["response_json"])

    def record_usage(
        self,
        api_key: str,
        tenant: str,
        trace_id: str,
        hop: int,
        verified: bool,
        vex_units: int,
        fu_tokens: int,
        ts: str,
    ):
        with self._conn() as c:
            c.execute(
                """INSERT INTO usage_ledger(api_key,tenant,trace_id,hop,verified,vex_units,fu_tokens,ts)
                         VALUES(?,?,?,?,?,?,?,?)""",
                (api_key, tenant, trace_id, hop, 1 if verified else 0, vex_units, fu_tokens, ts),
            )

    def enqueue_billing(self, api_key: str, stripe_item: str, units: int, ts_unix: int):
        with self._conn() as c:
            c.execute(
                """INSERT INTO billing_queue(api_key,stripe_item,units,ts,retries)
                         VALUES(?,?,?,?,0)""",
                (api_key, stripe_item, units, ts_unix),
            )

    def dequeue_billing_batch(self, limit: int = 100):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM billing_queue ORDER BY id ASC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_billing_items(self, ids):
        if not ids:
            return
        with self._conn() as c:
            q = "DELETE FROM billing_queue WHERE id IN ({})".format(",".join("?" * len(ids)))
            c.execute(q, ids)

    def bump_billing_retries(self, ids):
        if not ids:
            return
        with self._conn() as c:
            q = "UPDATE billing_queue SET retries = retries + 1 WHERE id IN ({})".format(
                ",".join("?" * len(ids))
            )
            c.execute(q, ids)


class StorageConflict(Exception):
    pass
