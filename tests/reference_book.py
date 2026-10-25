
from collections import deque

BUY, SELL = 0, 1


class ReferenceOrderBook:
    def __init__(self):
        self.bids = {}  # price -> deque([order_id, qty])
        self.asks = {}

    def add_order(self, order_id, price, qty, side):
        trades = []
        if side == BUY:
            while qty > 0 and self.asks:
                best = min(self.asks)
                if best > price:
                    break
                qty = self._fill(self.asks, best, order_id, qty, trades, BUY)
            if qty > 0:
                self.bids.setdefault(price, deque()).append([order_id, qty])
        else:
            while qty > 0 and self.bids:
                best = max(self.bids)
                if best < price:
                    break
                qty = self._fill(self.bids, best, order_id, qty, trades, SELL)
            if qty > 0:
                self.asks.setdefault(price, deque()).append([order_id, qty])
        return trades

    @staticmethod
    def _fill(book_side, price, taker_id, qty, trades, taker_side):
        level = book_side[price]
        while qty > 0 and level:
            maker = level[0]
            traded = min(qty, maker[1])
            buy_id, sell_id = (
                (taker_id, maker[0]) if taker_side == BUY else (maker[0], taker_id)
            )
            trades.append((buy_id, sell_id, price, traded))
            qty -= traded
            maker[1] -= traded
            if maker[1] == 0:
                level.popleft()
        if not level:
            del book_side[price]
        return qty

    def best_bid(self):
        if not self.bids:
            return None
        p = max(self.bids)
        return p, sum(q for _, q in self.bids[p])

    def best_ask(self):
        if not self.asks:
            return None
        p = min(self.asks)
        return p, sum(q for _, q in self.asks[p])

    def resting_qty(self, side):
        book = self.bids if side == BUY else self.asks
        return sum(q for lvl in book.values() for _, q in lvl)
