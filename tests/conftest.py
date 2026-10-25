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
