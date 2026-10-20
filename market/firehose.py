"""
ChronosMatch - Market Firehose (Week 1, Person 3)

Asyncio client that simulates a Nasdaq/NYSE tick firehose by blasting mock
Buy/Sell orders into the zero-copy IPC ring buffer.

Order format agreed by the team (fixed 24 bytes):
    struct.pack('<QqIB3x', order_id, price_in_cents, quantity, side)
    side: 0 = Buy, 1 = Sell

Buffer API agreed with Person 2:
    buf.write_order(order_id, price, qty, side) -> bool (False if buffer full)

Run (from the project root):
    python -m market.firehose --rate 100000 --duration 10
"""
import argparse
import asyncio
import random
import time

BUY, SELL = 0, 1


# --------------------------------------------------------------------------
# Buffer selection: use Person 2's real ring buffer if present, else a stub
# --------------------------------------------------------------------------
class StubBuffer:
    """Stand-in with the agreed API so you can work before the real buffer exists."""

    def __init__(self):
        self.count = 0

    def write_order(self, order_id, price, qty, side):
        self.count += 1
        return True


def get_buffer(use_stub=False):
    if use_stub:
        return StubBuffer()
    try:
        # >>> Adjust module/class name to match Person 2's implementation <<<
        from ipc.ring_buffer import RingBuffer
        return RingBuffer()
    except Exception as exc:  # ImportError or constructor mismatch
        print(f"[firehose] Real RingBuffer unavailable ({exc!r}); using StubBuffer.")
        return StubBuffer()


# --------------------------------------------------------------------------
# Order generation (Person 4 may supply a generator; this is the fallback)
# --------------------------------------------------------------------------
def build_order_pool(size=100_000, mid_price=10_000, spread=100, seed=42):
    """Pre-generate (price, qty, side) tuples so generation cost stays out of
    the hot loop. Prices are integer cents, never floats."""
    rng = random.Random(seed)
    return [
        (
            mid_price + rng.randint(-spread, spread),
            rng.randint(1, 500),
            rng.randint(BUY, SELL),
        )
        for _ in range(size)
    ]


# --------------------------------------------------------------------------
# The firehose
# --------------------------------------------------------------------------
async def firehose(buf, rate=100_000, duration=10, tick=0.01, pool=None):
    """Send `rate` orders/second for `duration` seconds in batches every `tick`.

    Batching matters: asyncio.sleep() cannot reliably fire 100,000 times/sec,
    but it can fire 100 times/sec carrying 1,000 orders each.
    Returns a stats dict.
    """
    pool = pool or build_order_pool()
    pool_len = len(pool)
    per_tick = max(1, int(rate * tick))

    sent = dropped = 0
    order_id = 1
    t_start = time.perf_counter()
    next_deadline = t_start

    while time.perf_counter() - t_start < duration:
        write = buf.write_order  # local lookup = faster hot loop
        for _ in range(per_tick):
            price, qty, side = pool[order_id % pool_len]
            if write(order_id, price, qty, side):
                sent += 1
            else:
                dropped += 1  # buffer full -> consumer too slow
            order_id += 1

        # Sleep only for the time remaining in this tick (keeps the rate steady)
        next_deadline += tick
        delay = next_deadline - time.perf_counter()
        await asyncio.sleep(delay if delay > 0 else 0)

    elapsed = time.perf_counter() - t_start
    return {
        "sent": sent,
        "dropped": dropped,
        "elapsed_s": round(elapsed, 3),
        "orders_per_sec": round(sent / elapsed),
    }


def main():
    p = argparse.ArgumentParser(description="ChronosMatch market firehose")
    p.add_argument("--rate", type=int, default=100_000, help="target orders/sec")
    p.add_argument("--duration", type=float, default=10, help="seconds to run")
    p.add_argument("--stub", action="store_true", help="force StubBuffer")
    args = p.parse_args()

    buf = get_buffer(use_stub=args.stub)
    stats = asyncio.run(firehose(buf, rate=args.rate, duration=args.duration))
    print("[firehose] Results:")
    for k, v in stats.items():
        print(f"   {k:>15}: {v:,}" if isinstance(v, int) else f"   {k:>15}: {v}")
    status = "PASS" if stats["orders_per_sec"] >= args.rate * 0.95 else "BELOW TARGET"
    print(f"[firehose] Target {args.rate:,}/s -> {status}")


if __name__ == "__main__":
    main()
