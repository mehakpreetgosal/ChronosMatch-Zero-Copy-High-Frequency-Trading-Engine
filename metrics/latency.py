"""
ChronosMatch - Metrics Tracking (Week 3, Person 3)

* Trade record packing/unpacking (48-byte format shared by the whole team)
* LatencyRecorder: stores nanosecond latencies in a pre-allocated C array so
  recording a sample never creates new Python objects (keeps the GC quiet).
* TimedBook: wraps ANY order book (reference or Cython) and timestamps every
  order with time.perf_counter_ns() on the way in and out.
"""
import struct
import time
from array import array

from config import TRADE_FORMAT

TRADE_STRUCT = struct.Struct(TRADE_FORMAT)
assert TRADE_STRUCT.size == 48, "Trade record must be exactly 48 bytes"

_now = time.perf_counter_ns


def pack_trade(buy_id, sell_id, price, qty, levels_cleared, t_in_ns, t_out_ns):
    return TRADE_STRUCT.pack(buy_id, sell_id, price, qty, levels_cleared, t_in_ns, t_out_ns)


def unpack_trade(raw):
    """-> (buy_id, sell_id, price, qty, levels_cleared, t_in_ns, t_out_ns)"""
    return TRADE_STRUCT.unpack(raw)


class LatencyRecorder:
    """Fixed-capacity store of signed 64-bit nanosecond samples."""

    def __init__(self, capacity=2_000_000):
        self.capacity = capacity
        self._buf = array("q", bytes(8 * capacity))  # pre-allocated, zero-filled
        self.count = 0
        self.overflow = 0

    def record(self, ns):
        if self.count < self.capacity:
            self._buf[self.count] = ns
            self.count += 1
        else:
            self.overflow += 1

    def reset(self):
        self.count = 0
        self.overflow = 0

    def summary(self):
        """Return dict of min / median / p99 / max / mean in nanoseconds."""
        if self.count == 0:
            return {"count": 0, "min_ns": 0, "median_ns": 0, "p99_ns": 0,
                    "max_ns": 0, "mean_ns": 0}
        data = sorted(self._buf[: self.count])
        n = len(data)
        return {
            "count": n,
            "min_ns": data[0],
            "median_ns": data[n // 2],
            "p99_ns": data[min(n - 1, int(n * 0.99))],
            "max_ns": data[-1],
            "mean_ns": sum(data) // n,
        }

    def format(self, label="latency"):
        s = self.summary()
        return (f"[{label}] n={s['count']:,}  min={s['min_ns']:,} ns  "
                f"median={s['median_ns']:,} ns  p99={s['p99_ns']:,} ns  "
                f"max={s['max_ns']:,} ns")


class TimedBook:
    """Wrap an order book and measure how long every add_order() takes.

    t_in  = timestamp just before the order enters the engine
    t_out = timestamp right after the engine returns its trades
    latency = t_out - t_in   (integer nanoseconds, never floats)

    Two recorders:
      all_orders      - every order submitted
      matching_orders - only orders that produced at least one trade
    """

    def __init__(self, book, capacity=2_000_000):
        self._book = book
        self.all_orders = LatencyRecorder(capacity)
        self.matching_orders = LatencyRecorder(capacity)
        self.last_t_in = 0
        self.last_t_out = 0

    def add_order(self, order_id, price, qty, side):
        t_in = _now()
        trades = self._book.add_order(order_id, price, qty, side)
        t_out = _now()
        self.last_t_in, self.last_t_out = t_in, t_out
        dt = t_out - t_in
        self.all_orders.record(dt)
        if trades:
            self.matching_orders.record(dt)
        return trades

    def __getattr__(self, name):  # best_bid(), best_ask(), resting_qty() ...
        return getattr(self._book, name)
