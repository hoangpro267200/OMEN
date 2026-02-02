"""Tests for retry decorators."""

import pytest

from omen.domain.errors import (
    SourceUnavailableError,
    PublishError,
    PublishRetriesExhaustedError,
)
from omen.infrastructure.retry import with_source_retry, with_publish_retry


def test_source_retry_returns_when_no_exception():
    @with_source_retry(max_attempts=3)
    def ok():
        return "ok"

    assert ok() == "ok"


def test_source_retry_raises_after_max_attempts():
    calls = 0

    @with_source_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)
    def fail():
        nonlocal calls
        calls += 1
        raise SourceUnavailableError("down")

    with pytest.raises(SourceUnavailableError, match="down"):
        fail()
    assert calls == 3


def test_source_retry_succeeds_on_second_attempt():
    calls = 0

    @with_source_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)
    def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise SourceUnavailableError("down")
        return "ok"

    assert flaky() == "ok"
    assert calls == 2


def test_publish_retry_raises_exhausted_after_max_attempts():
    @with_publish_retry(max_attempts=2, min_wait=0.01, max_wait=0.05)
    def fail():
        raise PublishError("nope")

    with pytest.raises(PublishRetriesExhaustedError) as exc_info:
        fail()
    assert exc_info.value.attempts == 2
    assert "2 attempts" in exc_info.value.message


def test_publish_retry_returns_when_success():
    @with_publish_retry(max_attempts=3)
    def ok():
        return True

    assert ok() is True
