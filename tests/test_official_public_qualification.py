import json
from pathlib import Path

import pandas as pd

from market_intel.foundation.official_http import OfficialHttpClient
from market_intel.foundation.public_qualification import (SampleStatus, compare_raw_normalized,
                                                          coverage_decision, reject_later_published_information)
from market_intel.foundation.source_registry import load_source_registry


class Response:
    def __init__(self, body=b"a,b\n1,2\n", status=200, content_type="text/csv"):
        self.content, self.status_code = body, status
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(body))}


class Session:
    def __init__(self, response):
        self.response, self.calls = response, 0
    def get(self, *args, **kwargs):
        self.calls += 1
        return self.response


def test_registry_is_versioned_and_complete():
    version, sources = load_source_registry(Path("specs/official_public_sources_v1.json"))
    assert version == "official_public_sources_v1"
    assert len(sources) >= 10
    assert any(s.organization == "AMFI" and s.qualification_status == "NOT_APPLICABLE" for s in sources)


def test_http_success_is_hashed_manifested_and_cached(tmp_path):
    session = Session(Response())
    client = OfficialHttpClient(allowed_hosts={"official.test"}, user_agent="identified", minimum_interval_seconds=0,
                                session=session)
    first = client.retrieve(organization="official", dataset="daily", url="https://official.test/x.csv",
                            raw_root=tmp_path, parser_version="v1", expected_content_types=("text/csv",))
    second = client.retrieve(organization="official", dataset="daily", url="https://official.test/x.csv",
                             raw_root=tmp_path, parser_version="v1", expected_content_types=("text/csv",))
    manifest = json.loads(Path(first.manifest_path).read_text())
    assert first.outcome == "SUCCEEDED" and manifest["content_hash"] == first.content_hash
    assert session.calls == 1 and second.content_hash == first.content_hash


def test_http_quarantines_captcha_html_and_wrong_schema(tmp_path):
    session = Session(Response(b"<html>CAPTCHA</html>", content_type="text/html"))
    client = OfficialHttpClient(allowed_hosts={"official.test"}, user_agent="identified", minimum_interval_seconds=0,
                                session=session)
    result = client.retrieve(organization="official", dataset="daily", url="https://official.test/x",
                             raw_root=tmp_path, parser_version="v1", expected_content_types=("text/csv",))
    assert result.outcome == "QUARANTINED"
    assert result.quarantine_reason == "CAPTCHA_OR_ACCESS_CONTROL"


def test_http_quarantines_truncated_and_unexpected_content(tmp_path):
    truncated = Response(b"abc", content_type="text/csv")
    truncated.headers["Content-Length"] = "100"
    client = OfficialHttpClient(allowed_hosts={"official.test"}, user_agent="identified",
                                minimum_interval_seconds=0, session=Session(truncated))
    result = client.retrieve(organization="official", dataset="daily", url="https://official.test/t",
                             raw_root=tmp_path, parser_version="v1", expected_content_types=("text/csv",))
    assert result.quarantine_reason == "TRUNCATED_OR_OVERSIZE"
    wrong = OfficialHttpClient(allowed_hosts={"official.test"}, user_agent="identified",
                               minimum_interval_seconds=0, session=Session(Response(b"PDF", content_type="application/pdf")))
    result = wrong.retrieve(organization="official", dataset="daily", url="https://official.test/w",
                            raw_root=tmp_path, parser_version="v1", expected_content_types=("text/csv",))
    assert result.quarantine_reason.startswith("UNEXPECTED_CONTENT_TYPE")


def test_raw_rows_reproduce_and_later_publications_are_rejected():
    raw = pd.DataFrame({"DATE": ["2020-01-01"], "CLOSE": [10.0]})
    normalized = pd.DataFrame({"trade_date": ["2020-01-01"], "close": [10.0]})
    assert compare_raw_normalized(raw, normalized, {"DATE": "trade_date", "CLOSE": "close"}).status == "PASS"
    facts = pd.DataFrame({"published_at": pd.to_datetime(["2020-01-01", "2020-01-03"]), "value": [1, 2]})
    assert reject_later_published_information(facts, pd.Timestamp("2020-01-02"))["value"].tolist() == [1]


def test_coverage_decision_is_mechanical_and_not_promoted_by_sample():
    decision = coverage_decision(full_population=SampleStatus.FAIL, identity=SampleStatus.UNKNOWN,
        corporate_actions=SampleStatus.UNKNOWN, terminal_outcomes=SampleStatus.FAIL, shorter_interval_proven=False)
    assert decision == "public sources remain insufficient without manual evidence collection"
