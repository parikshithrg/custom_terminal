"""Offline tests for strict, bounded R10N-E pair confirmation."""

from __future__ import annotations

from datetime import date

import pytest

import tools.confirm_nse_fno_r10ne as confirmation
from tools.download_nse_fno_reports import DownloadError, build_plan


DATES = (date(2026, 9, 10), date(2025, 7, 8))


class Response:
    def __init__(self, url: str, *, status: int = 200, headers=None, history=None):
        self.url = url
        self.status_code = status
        self.headers = {"Content-Length": "123", "ETag": "not-retained", **(headers or {})}
        self.history = history or []
        self.closed = False

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def head(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def exact_responses() -> list[Response]:
    return [Response(spec.url) for value in DATES for spec in build_plan(value, "both")]


def test_confirms_exactly_four_direct_heads_with_sanitized_metadata() -> None:
    responses = exact_responses()
    session = Session(responses)
    results = confirmation.confirm_exact_pairs(DATES, session=session)
    assert len(results) == len(session.calls) == 4
    assert all(call[1]["allow_redirects"] is False for call in session.calls)
    assert [item.url for item in results] == [call[0] for call in session.calls]
    assert all(item.response_metadata == {"content-length": "123"} for item in results)
    assert all(response.closed for response in responses)
    assert not session.closed


@pytest.mark.parametrize("status", [300, 301, 302, 303, 304, 305, 306, 307, 308, 399])
def test_every_3xx_class_stops_on_first_request(status: int) -> None:
    first_url = build_plan(DATES[0], "both")[0].url
    session = Session([
        Response(first_url, status=status, headers={"Location": "https://example.test/misleading"}),
        *exact_responses(),
    ])
    with pytest.raises(DownloadError, match="rejected HTTP"):
        confirmation.confirm_exact_pairs(DATES, session=session)
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False


def test_direct_200_does_not_follow_or_retain_misleading_location() -> None:
    responses = exact_responses()
    responses[0].headers["Location"] = "https://example.test/misleading"
    results = confirmation.confirm_exact_pairs(DATES, session=Session(responses))
    assert len(results) == 4
    assert "location" not in results[0].response_metadata


def test_hidden_history_and_changed_final_url_fail_closed() -> None:
    first_url = build_plan(DATES[0], "both")[0].url
    for response, match in (
        (Response(first_url, history=[object()]), "history"),
        (Response(first_url + "/changed"), "changed response URL"),
    ):
        session = Session([response, *exact_responses()])
        with pytest.raises(DownloadError, match=match):
            confirmation.confirm_exact_pairs(DATES, session=session)
        assert len(session.calls) == 1


def test_non_200_is_not_retried() -> None:
    first_url = build_plan(DATES[0], "both")[0].url
    session = Session([Response(first_url, status=404), *exact_responses()])
    with pytest.raises(DownloadError, match="received 404"):
        confirmation.confirm_exact_pairs(DATES, session=session)
    assert len(session.calls) == 1
    assert len(session.responses) == 4


def test_internal_session_is_closed_and_injected_session_is_preserved(monkeypatch) -> None:
    internal = Session(exact_responses())
    monkeypatch.setattr(confirmation.requests, "Session", lambda: internal)
    confirmation.confirm_exact_pairs(DATES)
    assert internal.closed

    injected = Session(exact_responses())
    confirmation.confirm_exact_pairs(DATES, session=injected)
    assert not injected.closed


@pytest.mark.parametrize("dates", [
    (), (DATES[0],), (DATES[0], DATES[0]), tuple(reversed(DATES)),
    (DATES[0], date(2024, 1, 1)),
])
def test_wrong_or_duplicate_date_scope_fails_before_session_creation(dates) -> None:
    session = Session([])
    with pytest.raises(ValueError):
        confirmation.confirm_exact_pairs(dates, session=session)
    assert session.calls == []
