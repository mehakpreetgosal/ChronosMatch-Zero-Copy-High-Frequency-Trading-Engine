"""
ChronosMatch - Engine Verification 
"""
import random
import time

BUY, SELL = 0, 1


# ------------------------- Core matching behaviour -------------------------
def test_exact_match(book):
    """Buy 100 @ 10000 then Sell 100 @ 10000 -> one trade, book empty."""
    assert book.add_order(1, 10_000, 100, BUY) == []
    trades = book.add_order(2, 10_000, 100, SELL)
    assert trades == [(1, 2, 10_000, 100)]
    assert book.best_bid() is None and book.best_ask() is None


def test_partial_fill_leaves_remainder(book):
    book.add_order(1, 10_000, 100, BUY)
    trades = book.add_order(2, 10_000, 40, SELL)
    assert trades == [(1, 2, 10_000, 40)]
    assert book.best_bid() == (10_000, 60)
    assert book.best_ask() is None


def test_no_match_when_prices_do_not_cross(book):
    book.add_order(1, 9_900, 50, BUY)
    trades = book.add_order(2, 10_100, 50, SELL)
    assert trades == []
    assert book.best_bid() == (9_900, 50)
    assert book.best_ask() == (10_100, 50)


def test_incoming_sell_matches_resting_buy_at_better_price(book):
    """Sell at 9,900 hits a resting Buy at 10,000: trade at the resting price."""
    book.add_order(1, 10_000, 10, BUY)
    trades = book.add_order(2, 9_900, 10, SELL)
    assert trades == [(1, 2, 10_000, 10)]


def test_incoming_buy_matches_resting_sell(book):
    book.add_order(1, 10_000, 25, SELL)
    trades = book.add_order(2, 10_050, 25, BUY)
    assert trades == [(2, 1, 10_000, 25)]


# ------------------------------ Priority rules -----------------------------
def test_price_priority_best_price_first(book):
    book.add_order(1, 9_950, 10, BUY)
    book.add_order(2, 10_000, 10, BUY)  # better bid
    trades = book.add_order(3, 9_900, 10, SELL)
    assert trades == [(2, 3, 10_000, 10)]
    assert book.best_bid() == (9_950, 10)


def test_time_priority_same_price_fifo(book):
    book.add_order(1, 10_000, 10, BUY)  # earlier
    book.add_order(2, 10_000, 10, BUY)  # later
    trades = book.add_order(3, 10_000, 10, SELL)
    assert trades == [(1, 3, 10_000, 10)]
    assert book.best_bid() == (10_000, 10)  # order 2 still waiting


def test_multi_level_sweep_whale_order(book):
    """One large Sell clears several price levels (the 'Whale' case)."""
    book.add_order(1, 10_020, 10, BUY)
    book.add_order(2, 10_010, 10, BUY)
    book.add_order(3, 10_000, 10, BUY)
    trades = book.add_order(4, 10_000, 35, SELL)
    assert trades == [
        (1, 4, 10_020, 10),
        (2, 4, 10_010, 10),
        (3, 4, 10_000, 10),
    ]
    assert book.best_bid() is None
    assert book.best_ask() == (10_000, 5)  # leftover 5 rests as a Sell


def test_one_buy_fills_multiple_resting_sells_in_time_order(book):
    book.add_order(1, 10_000, 5, SELL)
    book.add_order(2, 10_000, 5, SELL)
    trades = book.add_order(3, 10_000, 8, BUY)
    assert trades == [(3, 1, 10_000, 5), (3, 2, 10_000, 3)]
    assert book.best_ask() == (10_000, 2)


# ------------------------------- Stress tests ------------------------------
def _random_orders(n, seed=7):
    rng = random.Random(seed)
    return [
        (i, 10_000 + rng.randint(-50, 50), rng.randint(1, 200), rng.randint(0, 1))
        for i in range(1, n + 1)
    ]


def test_quantity_conservation(book):
    """Total submitted per side = traded + still resting."""
    orders = _random_orders(20_000)
    traded = 0
    for oid, price, qty, side in orders:
        for _, _, _, q in book.add_order(oid, price, qty, side):
            traded += q
    buy_in = sum(q for _, _, q, s in orders if s == BUY)
    sell_in = sum(q for _, _, q, s in orders if s == SELL)
    assert buy_in == traded + book.resting_qty(BUY)
    assert sell_in == traded + book.resting_qty(SELL)


def test_book_never_crossed(book):
    """After every order, best bid must be strictly below best ask."""
    for oid, price, qty, side in _random_orders(5_000, seed=11):
        book.add_order(oid, price, qty, side)
        bid, ask = book.best_bid(), book.best_ask()
        if bid and ask:
            assert bid[0] < ask[0]


def test_matches_reference_oracle(book, make_reference):
    """Engine output must be identical to the reference for the same input."""
    ref = make_reference()
    for oid, price, qty, side in _random_orders(10_000, seed=3):
        assert book.add_order(oid, price, qty, side) == ref.add_order(oid, price, qty, side)


# ------------------------------- Timing proof ------------------------------
def test_match_latency_report(book, capsys):
    """Measures nanoseconds for a single instant match (for the review table)."""
    samples = []
    for i in range(1, 2_001, 2):
        book.add_order(i, 10_000, 10, BUY)
        t0 = time.perf_counter_ns()
        trades = book.add_order(i + 1, 10_000, 10, SELL)
        samples.append(time.perf_counter_ns() - t0)
        assert len(trades) == 1
    samples.sort()
    median, p99 = samples[len(samples) // 2], samples[int(len(samples) * 0.99)]
    with capsys.disabled():
        print(f"\n[latency] match median={median:,} ns  p99={p99:,} ns  "
              f"({median/1000:.1f} us median)")
    # Generous ceiling so the test is stable; the Cython engine should be far lower.
    assert median < 1_000_000  # < 1 ms
