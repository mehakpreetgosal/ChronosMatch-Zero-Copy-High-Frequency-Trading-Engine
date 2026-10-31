"""
GC PROOF - show the Garbage Collector never runs while orders match.

Run:  pytest tests/test_gc_proof.py -v -s
Override size: set env var GC_PROOF_ORDERS=1000000
"""
import gc
import os

from market.firehose import build_order_pool
from tests.conftest import ENGINE_NAME, OrderBook


def _orders():
    cython = ENGINE_NAME == "Cython engine"
    default = 1_000_000 if cython else 100_000
    return int(os.environ.get("GC_PROOF_ORDERS", default)), cython


def test_no_garbage_collection_while_matching(capsys):
    n, is_cython = _orders()
    book = OrderBook()
    pool = build_order_pool(size=100_000, seed=99)
    pool_len = len(pool)

    starts = []
    callback = lambda phase, info: starts.append(info["generation"]) if phase == "start" else None
    gc.callbacks.append(callback)
    stats_before = sum(s["collections"] for s in gc.get_stats())
    try:
        add = book.add_order
        for oid in range(1, n + 1):
            price, qty, side = pool[oid % pool_len]
            add(oid, price, qty, side)
    finally:
        gc.callbacks.remove(callback)
    stats_after = sum(s["collections"] for s in gc.get_stats())

    collections = stats_after - stats_before
    with capsys.disabled():
        print(f"\n[gc-proof] engine={ENGINE_NAME}  orders={n:,}  "
              f"gc collections={collections}  (callback saw {len(starts)})")

    if is_cython:
        assert collections == 0, "GC ran during matching - find remaining Python objects (cython -a)"
        assert len(starts) == 0
    else:
        assert collections >= 0  # informational only for the reference book
