"""
Chooses which engine the tests run against.

  * If Person 1's Cython engine is importable, tests run against it.
  * Otherwise they run against the pure-Python reference book.

>>> Edit the import below to match Person 1's module/class name. <<<
"""
import pytest

from tests.reference_book import ReferenceOrderBook

try:
    from engine.matching import OrderBook  # Person 1's compiled Cython class
    ENGINE_NAME = "Cython engine"
except Exception:
    OrderBook = ReferenceOrderBook
    ENGINE_NAME = "reference (pure-Python) book"


def pytest_report_header(config):
    return f"ChronosMatch tests running against: {ENGINE_NAME}"


@pytest.fixture
def book():
    return OrderBook()


@pytest.fixture
def make_reference():
    return ReferenceOrderBook
