# ChronosMatch - Zero-Copy High-Frequency Trading Engine (Weeks 1-2)

Python normally can't do high-frequency trading: the Garbage Collector causes latency
spikes and passing data between processes needs slow serialization (JSON/Pickle).
ChronosMatch avoids both:

* **Zero-copy IPC** - orders travel between processes through a memory-mapped ring
  buffer (`mmap` + `struct`): no pickling, no sockets.
* **Cython matching engine** - Limit Order Book with Price-Time priority, written with
  C types/pointers so the matching loop uses no Python objects (no GC, no GIL needed).

```
 [market firehose]  --24-byte orders-->  [mmap ring buffer]  --> [Cython order book]
   (asyncio, 100k/s)                      (shared memory)             |
                                                                      v
                                              [live snapshot] --> [curses dashboard]
```

## Team and ownership (Weeks 1-2)
| Person | Role | Week 1 | Week 2 |
|---|---|---|---|
| 1 | Core Engine Lead | design help, code review | `engine/orderbook_cy.pyx`, `setup.py`, `engine/matching.py` |
| 2 | IPC Lead | `ipc/ring_buffer.py` | `tools/ipc_audit.py` (1M-order IPC audit), `engine/runner.py` |
| 3 | Market & Testing | `market/firehose.py` | `tests/test_engine.py`, `tests/reference_book.py`, `tests/benchmark_report.py` (engine verification) |
| 4 | UI & Docs | repo setup, `market/order_generator.py` | `ui/dashboard.py`, `ui/snapshot.py`, README, `run_pipeline.py` |

## Shared formats
* **Order record (24 bytes):** `struct '<QqIB3x'` -> `order_id, price_in_cents, quantity, side`
  (`side`: 0 = Buy, 1 = Sell). Prices are integer cents, never floats.
* **Engine interface:** `add_order(order_id, price, qty, side) -> [(buy_id, sell_id, price, qty), ...]`
  (trades execute at the resting order's price), plus `best_bid()`, `best_ask()`,
  `resting_qty(side)`, `depth(side, n)`.

## Setup
```
pip install -r requirements.txt
python setup.py build_ext --inplace      # compiles the Cython engine
```
*Windows:* compiling needs the free **Microsoft C++ Build Tools** ("Desktop development
with C++"). Without a compiler everything still runs on an automatic pure-Python
fallback engine (`engine/orderbook_py.py`) - just slower. `python -c "from engine.matching import ENGINE_NAME; print(ENGINE_NAME)"`
tells you which one you have.

## Run
```
python run_pipeline.py --ui              # whole system + live terminal dashboard (q quits)
python run_pipeline.py --duration 10     # headless run + summary
python -m ui.dashboard --fake            # dashboard with fake data (UI development)
python -m market.firehose --stub         # firehose only, no ring buffer needed
pytest -v                                # all tests
python -m tests.benchmark_report         # engine-verification table (mid-review)
python -m tools.ipc_audit                # 1M-order IPC audit    (mid-review)
```

## Project layout
```
ipc/ring_buffer.py        mmap SPSC ring buffer (zero-copy bus)
engine/orderbook_cy.pyx   Cython Limit Order Book (C structs, bitmap level search)
engine/orderbook_py.py    pure-Python fallback with the same interface
engine/matching.py        import point: Cython if built, else fallback
engine/runner.py          engine process: ring buffer -> order book -> snapshot
market/firehose.py        asyncio firehose (100,000 orders/s target)
market/order_generator.py mock Buy/Sell order generator
ui/snapshot.py            shared-memory book snapshot (seqlock)
ui/dashboard.py           curses dashboard: bid/ask ladder, spread, throughput
tools/ipc_audit.py        1M-order two-process audit vs. pickling baseline
tests/                    ring buffer, engine, verification, dashboard tests
docs/                     generated review reports + MIDREVIEW.md runbook
```

## Git rules
Own branch (`name-feature`), Pull Request, Person 1 reviews/merges. Never push to `main`.
