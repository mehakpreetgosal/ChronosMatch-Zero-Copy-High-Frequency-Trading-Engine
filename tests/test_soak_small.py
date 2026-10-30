"""Week 4: small soak (fast) - engine -> ledger counts must match exactly."""
import os
import tempfile

from tools.soak_test import run_soak


def test_small_soak_ledger_matches_engine():
    with tempfile.TemporaryDirectory() as d:
        r = run_soak(50_000, os.path.join(d, "t.db"), quiet=True)
    assert r["engine_trades"] > 0
    assert r["checks"], "no checks ran"
    assert r["all_checks_passed"], r["checks"]
