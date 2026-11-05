"""
ChronosMatch - Soak test + final benchmark (Week 4, Person 3)

Pipeline:  order generator -> TimedBook(engine) -> 48-byte trade records
           -> batched SQLite ledger -> verification

Checks:
  1. every trade the engine produced is in the ledger (counts AND quantities match)
  2. quantity conservation (submitted = traded + resting)
  3. GC collections during matching (target: 0 for the Cython engine)
  4. whale count in ledger == whale count seen live
Writes docs/final_benchmark.md for the final review.

Run (project root):
    python -m tools.soak_test --orders 1000000
"""
import argparse
import gc
import json
import os
import platform
import sys
import time

from config import WHALE_LEVELS
from market.firehose import build_order_pool
from metrics.latency import TimedBook, pack_trade
from metrics.whale import levels_cleared
from tests.conftest import ENGINE_NAME, OrderBook
from tools.reference_ledger import ReferenceLedger

BATCH = 1000  # trades per ledger commit


def run_soak(n_orders=1_000_000, db_path="ledger.db", ledger_factory=None, quiet=False):
    book = TimedBook(OrderBook(), capacity=n_orders + 1)
    ledger = (ledger_factory or ReferenceLedger)(db_path)
    pool = build_order_pool(size=100_000, seed=2024)
    pool_len = len(pool)

    gc_events = []
    gc.callbacks.append(lambda phase, info: gc_events.append(phase) if phase == "start" else None)
    gc_before = sum(s["collections"] for s in gc.get_stats())

    engine_trades = engine_qty = whales = submitted_buy = submitted_sell = 0
    pending = []
    t_wall = time.perf_counter()

    for oid in range(1, n_orders + 1):
        price, qty, side = pool[oid % pool_len]
        if side == 0:
            submitted_buy += qty
        else:
            submitted_sell += qty
        trades = book.add_order(oid, price, qty, side)
        if trades:
            lv = levels_cleared(trades)
            if lv >= WHALE_LEVELS:
                whales += 1
            t_in, t_out = book.last_t_in, book.last_t_out
            for buy_id, sell_id, tprice, tqty in trades:
                pending.append(pack_trade(buy_id, sell_id, tprice, tqty, lv, t_in, t_out))
                engine_qty += tqty
            engine_trades += len(trades)
            if len(pending) >= BATCH:
                ledger.write_batch(pending)
                pending = []

    if pending:
        ledger.write_batch(pending)
    elapsed = time.perf_counter() - t_wall

    gc.callbacks.pop()
    gc_after = sum(s["collections"] for s in gc.get_stats())

    ledger_trades, ledger_qty = ledger.count(), ledger.total_qty()
    ledger_whales = ledger.whale_count(WHALE_LEVELS)
    ledger.close()

    resting_buy = book.resting_qty(0)
    resting_sell = book.resting_qty(1)
    lat_all, lat_match = book.all_orders.summary(), book.matching_orders.summary()

    checks = {
        "ledger_trade_count_matches": ledger_trades == engine_trades,
        "ledger_qty_matches": ledger_qty == engine_qty,
        "buy_qty_conserved": submitted_buy == engine_qty + resting_buy,
        "sell_qty_conserved": submitted_sell == engine_qty + resting_sell,
        "whales_match_ledger": ledger_whales == whales,
    }
    result = {
        "engine": ENGINE_NAME,
        "python": platform.python_version(),
        "orders": n_orders,
        "elapsed_s": round(elapsed, 3),
        "orders_per_sec": round(n_orders / elapsed),
        "engine_trades": engine_trades,
        "ledger_trades": ledger_trades,
        "whales": whales,
        "gc_collections_during_run": gc_after - gc_before,
        "latency_all": lat_all,
        "latency_matching": lat_match,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    if not quiet:
        print_result(result)
    return result


def print_result(r):
    print(f"\nEngine under test : {r['engine']}")
    print(f"Orders processed  : {r['orders']:,} in {r['elapsed_s']} s "
          f"({r['orders_per_sec']:,} orders/s incl. ledger writes)")
    print(f"Trades            : engine={r['engine_trades']:,}  ledger={r['ledger_trades']:,}")
    print(f"Whale orders      : {r['whales']:,} (>= {WHALE_LEVELS} levels)")
    print(f"GC collections    : {r['gc_collections_during_run']}")
    for key in ("latency_all", "latency_matching"):
        s = r[key]
        print(f"{key:<17} : median={s['median_ns']:,} ns  p99={s['p99_ns']:,} ns  max={s['max_ns']:,} ns")
    for name, ok in r["checks"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


def write_report(r, path="docs/final_benchmark.md"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    la, lm = r["latency_all"], r["latency_matching"]
    sub_ms = "YES" if la["p99_ns"] < 1_000_000 else "NO"
    lines = [
        "# ChronosMatch - Final Benchmark Report", "",
        f"* Engine tested: **{r['engine']}**  (Python {r['python']})",
        f"* Orders processed: **{r['orders']:,}** in {r['elapsed_s']} s",
        f"* Throughput (engine + ledger writes): **{r['orders_per_sec']:,} orders/s**",
        f"* Trades matched: {r['engine_trades']:,} | stored in SQLite ledger: {r['ledger_trades']:,}",
        f"* Whale orders (>= {WHALE_LEVELS} price levels): {r['whales']:,}",
        f"* Garbage collections during matching: **{r['gc_collections_during_run']}**",
        f"* Sub-millisecond execution (p99 < 1 ms): **{sub_ms}**", "",
        "## Latency (nanoseconds, t_out - t_in)", "",
        "| Group | Count | Min | Median | p99 | Max |", "|---|---|---|---|---|---|",
        f"| All orders | {la['count']:,} | {la['min_ns']:,} | {la['median_ns']:,} | {la['p99_ns']:,} | {la['max_ns']:,} |",
        f"| Orders that traded | {lm['count']:,} | {lm['min_ns']:,} | {lm['median_ns']:,} | {lm['p99_ns']:,} | {lm['max_ns']:,} |",
        "", "## Verification checks", "", "| Check | Result |", "|---|---|",
    ]
    lines += [f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in r["checks"].items()]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(path.replace(".md", ".json"), "w") as f:
        json.dump(r, f, indent=2)
    print(f"\nReport written to {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=1_000_000)
    ap.add_argument("--db", default="ledger.db")
    args = ap.parse_args()
    r = run_soak(args.orders, args.db)
    write_report(r)
    sys.exit(0 if r["all_checks_passed"] else 1)


if __name__ == "__main__":
    main()
