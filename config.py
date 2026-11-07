"""Shared team settings. Change a value here and everyone picks it up."""

# A "Whale" = ONE incoming order that clears this many (or more) price levels.
WHALE_LEVELS = 3

# Trade record agreed by the team (fixed 48 bytes):
#   buy_id, sell_id, price_cents, qty, levels_cleared, t_in_ns, t_out_ns
TRADE_FORMAT = "<QQqIH2xQQ"
