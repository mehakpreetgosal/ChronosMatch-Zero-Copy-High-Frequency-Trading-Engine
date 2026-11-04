"""
ChronosMatch - Soak test + final benchmark (Week 4, Person 3)

Pipeline:  order generator -> TimedBook(engine) -> 48-byte trade records
           -> batched SQLite ledger -> verification

Checks:
  1. every trade the engine produced is in the ledger (counts AND quantities match)
  2. quantity conservation (submitted = traded + resting)
  3. GC collections during matching (target: 0 for the Cython engine)
  4. whale count in ledger == whale count seen live
Writes docs/final_benchmark.md for the final review.

Run (project root):
    python -m tools.soak_test --orders 1000000
"""
import argparse
import gc
import json
import os
import platform
import sys
import time

from config import WHALE_LEVELS
from market.firehose import build_order_pool
from metrics.latency import TimedBook, pack_trade
from metrics.whale import levels_cleared
from tests.conftest import ENGINE_NAME, OrderBook
from tools.reference_ledger import ReferenceLedger

BATCH = 1000  # trades per ledger commit
