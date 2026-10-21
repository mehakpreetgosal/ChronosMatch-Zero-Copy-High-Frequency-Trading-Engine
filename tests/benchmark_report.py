"""
Generates a results table (Markdown) for the Mid-Project Review.
Run (from project root):  python -m tests.benchmark_report
Then paste the printed table into your docs / presentation.
"""
import re
import subprocess
import sys

from tests.conftest import ENGINE_NAME


def main():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-s", "--tb=short",
         "-p", "no:cacheprovider", "tests/test_engine.py"],
        capture_output=True, text=True,
    )
    # DOTALL: the latency test prints a line before its PASSED marker
    found = re.findall(r"::(\w+)\s.*?(PASSED|FAILED)", proc.stdout, re.DOTALL)
    rows = [(name, "PASS" if res == "PASSED" else "FAIL") for name, res in found]
    print(f"### Engine verification ({ENGINE_NAME})\n")
    print("| Test | Result |\n|---|---|")
    for name, res in rows:
        print(f"| {name} | {res} |")
    for line in proc.stdout.splitlines():
        if line.strip().startswith("[latency]"):
            print(f"\n{line.strip()}")
    print(f"\n{sum(r == 'PASS' for _, r in rows)}/{len(rows)} tests passed")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
