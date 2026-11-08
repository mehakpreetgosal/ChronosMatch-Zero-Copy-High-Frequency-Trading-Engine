# Mid-Project Review Runbook (Weeks 1-2)

## What the review asks for
1. **IPC Audit** - prove zero-copy works: 1M orders between two Python processes, no pickling.
2. **Engine Verification** - prove the Order Book matches a Buy with a corresponding Sell instantly.

## Demo script (about 5 minutes)
1. `python -c "from engine.matching import ENGINE_NAME; print(ENGINE_NAME)"` -> should print `Cython engine`.
2. **IPC audit** (Person 2): `python -m tools.ipc_audit`
   Show: 1,000,000 received / 0 corrupt, and the speed-up over `multiprocessing.Queue` (pickling).
3. **Engine verification** (Person 3): `python -m tests.benchmark_report`
   Show: all tests PASS (exact match, partial fill, price priority, time priority, multi-level sweep,
   100k-order comparison against an independent reference book) and the match latency in ns.
4. **Live system** (Person 4): `python run_pipeline.py --ui --duration 30`
   Show: firehose at ~100k orders/s, bid/ask ladder updating, spread, engine ns/order.
5. **Why Cython** (Person 1): open `engine/orderbook_cy.pyx` - `_process()` is `nogil`
   and touches only C types. Optional: `cython -a engine/orderbook_cy.pyx` and open the HTML.

## Talking points
* No pickling: orders are 24 raw bytes written with `struct.pack_into` into shared memory.
* Ring buffer is lock-free: producer owns the write position, consumer owns the read position.
* Order book: price levels are a flat C array; resting orders live in a pre-allocated pool
  linked by integer indexes (FIFO per level = time priority); a two-level bitmap finds the
  next populated price level without scanning empty prices.
* Honest limits: Week 3 removes the remaining Python objects/GC risk and adds nanosecond
  metrics; Week 4 adds the SQLite ledger and the Whale highlight.
