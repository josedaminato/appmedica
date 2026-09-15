"""Fixtures compartidas. El limiter de login es global en memoria y rompe la suite."""

import pytest

from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _disable_app_limiter():
    previous = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = previous
