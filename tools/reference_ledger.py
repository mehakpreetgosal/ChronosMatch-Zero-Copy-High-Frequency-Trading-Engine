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
