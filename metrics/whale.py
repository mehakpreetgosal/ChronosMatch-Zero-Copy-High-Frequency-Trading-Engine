"""
ChronosMatch - Whale detection (Week 4, Person 3)

A Whale is ONE incoming order whose trades span WHALE_LEVELS or more distinct
price levels (config.py). Works purely from the trade list the engine returns,
so it works today with the reference book and later with the Cython engine.
(Once Person 1 adds levels_cleared to the engine, compare it with this value.)
"""
from config import WHALE_LEVELS


def levels_cleared(trades):
    """Number of distinct price levels touched by one incoming order's trades.
    trades: list of (buy_id, sell_id, price, qty)."""
    return len({t[2] for t in trades})


def is_whale(trades, threshold=None):
    return levels_cleared(trades) >= (WHALE_LEVELS if threshold is None else threshold)


def whale_summary(trades):
    """Dict for the UI banner (Person 4): size and levels of the whale order."""
    return {
        "levels_cleared": levels_cleared(trades),
        "total_qty": sum(t[3] for t in trades),
        "worst_price": max(t[2] for t in trades) if trades else 0,
        "best_price": min(t[2] for t in trades) if trades else 0,
    }
