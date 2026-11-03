"""
Minimal SQLite trade ledger (batched, WAL mode) - for testing the soak test
BEFORE Person 2's real ledger writer is ready. Same job: persist 48-byte trade
records permanently for auditing.
"""
import os
import sqlite3

from metrics.latency import unpack_trade


class ReferenceLedger:
    def __init__(self, path="ledger.db", fresh=True):
        if fresh and os.path.exists(path):
            for suffix in ("", "-wal", "-shm"):
                if os.path.exists(path + suffix):
                    os.remove(path + suffix)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS trades (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   buy_id INTEGER, sell_id INTEGER, price INTEGER, qty INTEGER,
                   levels_cleared INTEGER, t_in_ns INTEGER, t_out_ns INTEGER)"""
        )
        self.conn.commit()

    
    def write_batch(self, raw_records):
        """raw_records: list of 48-byte trade records. One commit per batch."""
        rows = [unpack_trade(r) for r in raw_records]
        self.conn.executemany(
            "INSERT INTO trades (buy_id, sell_id, price, qty, levels_cleared,"
            " t_in_ns, t_out_ns) VALUES (?,?,?,?,?,?,?)", rows)
        self.conn.commit()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

    def total_qty(self):
        return self.conn.execute("SELECT COALESCE(SUM(qty),0) FROM trades").fetchone()[0]

    def whale_count(self, threshold):
        return self.conn.execute(
            "SELECT COUNT(DISTINCT t_in_ns) FROM trades WHERE levels_cleared >= ?",
            (threshold,)).fetchone()[0]

    def close(self):
        self.conn.close()

