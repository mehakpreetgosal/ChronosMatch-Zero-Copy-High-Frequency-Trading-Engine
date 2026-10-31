"""Week 4 tests: Whale rule = one order clearing >= WHALE_LEVELS price levels."""
from config import WHALE_LEVELS
from metrics.whale import is_whale, levels_cleared, whale_summary

BUY, SELL = 0, 1


def _fill_bids(book, levels, qty=10, base=10_000):
    for i in range(levels):
        book.add_order(100 + i, base + i * 10, qty, BUY)


def test_default_threshold_is_three():
    assert WHALE_LEVELS == 3


def test_no_trades_is_not_a_whale():
    assert levels_cleared([]) == 0 and not is_whale([])


def test_sweeping_three_levels_is_a_whale(book):
    _fill_bids(book, 3)
    trades = book.add_order(1, 9_000, 30, SELL)
    assert levels_cleared(trades) == 3
    assert is_whale(trades)


def test_two_levels_is_not_a_whale(book):
    _fill_bids(book, 2)
    trades = book.add_order(1, 9_000, 20, SELL)
    assert levels_cleared(trades) == 2
    assert not is_whale(trades)


def test_many_fills_at_one_level_is_not_a_whale(book):
    for i in range(10):
        book.add_order(100 + i, 10_000, 5, BUY)  # 10 orders, ONE level
    trades = book.add_order(1, 10_000, 50, SELL)
    assert len(trades) == 10
    assert levels_cleared(trades) == 1
    assert not is_whale(trades)


def test_buy_side_whale(book):
    for i in range(4):
        book.add_order(100 + i, 10_000 + i * 10, 10, SELL)
    trades = book.add_order(1, 11_000, 40, BUY)
    assert levels_cleared(trades) == 4 and is_whale(trades)


def test_partial_last_level_still_counts(book):
    _fill_bids(book, 3, qty=10)
    trades = book.add_order(1, 9_000, 25, SELL)  # clears 2 fully, 3rd partially
    assert levels_cleared(trades) == 3 and is_whale(trades)


def test_threshold_can_be_overridden(book):
    _fill_bids(book, 2)
    trades = book.add_order(1, 9_000, 20, SELL)
    assert is_whale(trades, threshold=2)


def test_whale_summary_for_ui(book):
    _fill_bids(book, 3)
    trades = book.add_order(1, 9_000, 30, SELL)
    s = whale_summary(trades)
    assert s == {"levels_cleared": 3, "total_qty": 30,
                 "worst_price": 10_020, "best_price": 10_000}
