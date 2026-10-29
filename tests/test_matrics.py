"""Week 3 tests: trade record format, latency stats, timing wrapper."""
from metrics.latency import (LatencyRecorder, TRADE_STRUCT, TimedBook,
                             pack_trade, unpack_trade)

BUY, SELL = 0, 1


def test_trade_record_is_exactly_48_bytes():
    raw = pack_trade(1, 2, 10_000, 50, 3, 111, 222)
    assert len(raw) == 48 == TRADE_STRUCT.size


def test_trade_record_round_trip():
    fields = (11, 22, 10_050, 75, 4, 1_000_000, 1_000_900)
    assert unpack_trade(pack_trade(*fields)) == fields


def test_latency_summary_known_values():
    rec = LatencyRecorder(capacity=1000)
    for ns in range(1, 101):  # 1..100
        rec.record(ns)
    s = rec.summary()
    assert s["count"] == 100
    assert s["min_ns"] == 1 and s["max_ns"] == 100
    assert s["median_ns"] == 51
    assert s["p99_ns"] == 100
    assert s["mean_ns"] == 50


def test_latency_recorder_overflow_does_not_crash():
    rec = LatencyRecorder(capacity=3)
    for ns in (5, 6, 7, 8, 9):
        rec.record(ns)
    assert rec.count == 3 and rec.overflow == 2


def test_empty_summary_is_safe():
    assert LatencyRecorder(10).summary()["count"] == 0


def test_timed_book_records_and_returns_trades(book):
    tb = TimedBook(book, capacity=100)
    tb.add_order(1, 10_000, 10, BUY)
    trades = tb.add_order(2, 10_000, 10, SELL)
    assert trades == [(1, 2, 10_000, 10)]
    assert tb.all_orders.count == 2
    assert tb.matching_orders.count == 1  # only the second order traded
    assert tb.last_t_out > tb.last_t_in   # clock moves forward
    assert tb.best_bid() is None          # delegation to the wrapped book works
