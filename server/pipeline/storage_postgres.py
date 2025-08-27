import psycopg2
import psycopg2.extras
import json
import os
from typing import Optional, Dict, Any, List
from .storage import StorageConflict

INIT_SQL = """
-- Enable WAL mode equivalent (default in PostgreSQL)
-- Create tables with proper constraints and indexes

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
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(api_key, key)
);

CREATE TABLE IF NOT EXISTS usage_ledger(
  id SERIAL PRIMARY KEY,
  api_key TEXT NOT NULL,
  tenant TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  hop INTEGER NOT NULL,
  verified INTEGER NOT NULL,
  vex_units INTEGER NOT NULL,
  fu_tokens INTEGER NOT NULL,
  ts TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_queue(
  id SERIAL PRIMARY KEY,
  api_key TEXT NOT NULL,
  stripe_item TEXT NOT NULL,
  units INTEGER NOT NULL,
  ts INTEGER NOT NULL,
  retries INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_receipts_trace_id ON receipts(trace_id);
CREATE INDEX IF NOT EXISTS idx_usage_ledger_api_key ON usage_ledger(api_key);
CREATE INDEX IF NOT EXISTS idx_usage_ledger_tenant ON usage_ledger(tenant);
CREATE INDEX IF NOT EXISTS idx_billing_queue_api_key ON billing_queue(api_key);
CREATE INDEX IF NOT EXISTS idx_idempotency_created_at ON idempotency(created_at);
"""

class PostgreSQLStorage:
    """
    PostgreSQL implementation of the Storage interface.
    Mirrors the SQLite DAO interface exactly for drop-in replacement.
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(INIT_SQL)
            conn.commit()

    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(
            self.connection_string,
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def get_head(self, trace_id: str):
        """Get the head (latest receipt) for a trace"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT trace_id, last_hop, last_receipt_hash FROM heads WHERE trace_id = %s",
                    (trace_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def append_receipt(self, receipt: Dict[str, Any], expected_prev: Optional[str]) -> int:
        """Append a receipt to the chain with conflict detection"""
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    # Start transaction
                    cur.execute("BEGIN")
                    
                    # Check current head
                    cur.execute(
                        "SELECT trace_id, last_hop, last_receipt_hash FROM heads WHERE trace_id = %s FOR UPDATE",
                        (receipt["trace_id"],)
                    )
                    head = cur.fetchone()
                    
                    if head:
                        if head["last_receipt_hash"] != expected_prev:
                            cur.execute("ROLLBACK")
                            raise StorageConflict("prev_receipt_hash mismatch")
                        hop = head["last_hop"] + 1
                    else:
                        if expected_prev is not None:
                            cur.execute("ROLLBACK")
                            raise StorageConflict("unexpected prev_receipt_hash")
                        hop = 1
                    
                    receipt["hop"] = hop
                    
                    # Insert receipt
                    cur.execute("""
                        INSERT INTO receipts(trace_id, hop, ts, cid, canon, algo, prev_receipt_hash, policy_json, tenant, receipt_hash)
                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        receipt["trace_id"], hop, receipt["ts"], receipt["cid"], receipt["canon"], 
                        receipt["algo"], receipt.get("prev_receipt_hash"), json.dumps(receipt["policy"]), 
                        receipt["tenant"], receipt["receipt_hash"]
                    ))
                    
                    # Update or insert head
                    if head:
                        cur.execute(
                            "UPDATE heads SET last_hop = %s, last_receipt_hash = %s WHERE trace_id = %s",
                            (hop, receipt["receipt_hash"], receipt["trace_id"])
                        )
                    else:
                        cur.execute(
                            "INSERT INTO heads(trace_id, last_hop, last_receipt_hash) VALUES(%s, %s, %s)",
                            (receipt["trace_id"], hop, receipt["receipt_hash"])
                        )
                    
                    cur.execute("COMMIT")
                    return hop
                    
            except psycopg2.Error as e:
                conn.rollback()
                if "duplicate key" in str(e).lower():
                    raise StorageConflict("Receipt already exists")
                raise

    def get_chain(self, trace_id: str):
        """Get the complete receipt chain for a trace"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM receipts WHERE trace_id = %s ORDER BY hop ASC",
                    (trace_id,)
                )
                rows = cur.fetchall()
                
                out = []
                for r in rows:
                    out.append({
                        "trace_id": r["trace_id"],
                        "hop": r["hop"],
                        "ts": r["ts"],
                        "cid": r["cid"],
                        "canon": r["canon"],
                        "algo": r["algo"],
                        "prev_receipt_hash": r["prev_receipt_hash"],
                        "policy": json.loads(r["policy_json"]),
                        "tenant": r["tenant"],
                        "receipt_hash": r["receipt_hash"]
                    })
                return out

    def cache_idempotent(self, api_key: str, idem_key: str, response_json: Dict[str, Any]):
        """Cache an idempotent response"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO idempotency(api_key, key, response_json) 
                    VALUES(%s, %s, %s)
                    ON CONFLICT (api_key, key) 
                    DO UPDATE SET response_json = EXCLUDED.response_json, created_at = CURRENT_TIMESTAMP
                """, (api_key, idem_key, json.dumps(response_json)))
            conn.commit()

    def get_idempotent(self, api_key: str, idem_key: str):
        """Get cached idempotent response"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT response_json FROM idempotency WHERE api_key = %s AND key = %s",
                    (api_key, idem_key)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return json.loads(row["response_json"])

    def record_usage(self, api_key: str, tenant: str, trace_id: str, hop: int, verified: bool, vex_units: int, fu_tokens: int, ts: str):
        """Record usage metrics"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usage_ledger(api_key, tenant, trace_id, hop, verified, vex_units, fu_tokens, ts)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
                """, (api_key, tenant, trace_id, hop, 1 if verified else 0, vex_units, fu_tokens, ts))
            conn.commit()

    def enqueue_billing(self, api_key: str, stripe_item: str, units: int, ts_unix: int):
        """Enqueue billing event"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO billing_queue(api_key, stripe_item, units, ts, retries)
                    VALUES(%s, %s, %s, %s, 0)
                """, (api_key, stripe_item, units, ts_unix))
            conn.commit()

    def dequeue_billing_batch(self, limit: int = 100):
        """Get a batch of billing events to process"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM billing_queue ORDER BY id ASC LIMIT %s",
                    (limit,)
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]

    def delete_billing_items(self, ids):
        """Delete processed billing items"""
        if not ids:
            return
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM billing_queue WHERE id = ANY(%s)",
                    (ids,)
                )
            conn.commit()

    def bump_billing_retries(self, ids):
        """Increment retry count for failed billing items"""
        if not ids:
            return
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE billing_queue SET retries = retries + 1 WHERE id = ANY(%s)",
                    (ids,)
                )
            conn.commit()

    def cleanup_old_idempotency(self, days: int = 7):
        """Clean up old idempotency records (PostgreSQL-specific maintenance)"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM idempotency WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'",
                    (days,)
                )
                deleted = cur.rowcount
            conn.commit()
            return deleted

def create_storage(connection_string: str):
    """Factory function to create PostgreSQL storage"""
    return PostgreSQLStorage(connection_string)
