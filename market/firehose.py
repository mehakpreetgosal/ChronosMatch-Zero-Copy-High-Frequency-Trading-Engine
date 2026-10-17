import random
import asyncio, time

class StubBuffer:
    def __init__(self): self.count = 0
    def write_order(self, order_id, price, qty, side): self.count += 1

def make_order(i):
    return (i, random.randint(9900, 10100), random.randint(1, 500), random.randint(0, 1))

async def firehose(buf, rate=100_000, tick=0.01, duration=10):
    per_tick = int(rate * tick)          # 1000 orders every 10 ms
    order_id, end = 0, time.perf_counter() + duration
    while time.perf_counter() < end:
        start = time.perf_counter()
        for _ in range(per_tick):
            buf.write_order(*make_order(order_id))
            order_id += 1
        await asyncio.sleep(max(0, tick - (time.perf_counter() - start)))
    print(f"Sent {order_id} orders")

asyncio.run(firehose(StubBuffer()))
