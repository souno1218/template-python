# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from reference_agent.bundle.document import (
    OKFDocument,
    OKFDocumentError,
    is_stale,
    normalize_verified,
    parse_timestamp,
    trust_tier,
)


def test_roundtrip_preserves_frontmatter_and_body():
    src = (
        "---\n"
        "type: BigQuery Table\n"
        "title: Sample\n"
        "description: A sample table.\n"
        "tags: [a, b]\n"
        "timestamp: 2026-05-27T00:00:00+00:00\n"
        "---\n"
        "\n"
        "# Sample\n"
        "\n"
        "Body text.\n"
    )
    doc = OKFDocument.parse(src)
    assert doc.frontmatter["type"] == "BigQuery Table"
    assert doc.frontmatter["tags"] == ["a", "b"]
    assert doc.body.startswith("# Sample")

    serialized = doc.serialize()
    reparsed = OKFDocument.parse(serialized)
    assert reparsed.frontmatter == doc.frontmatter
    assert reparsed.body.strip() == doc.body.strip()


def test_parse_no_frontmatter_treats_all_as_body():
    src = "# Hello\n\nNo frontmatter here.\n"
    doc = OKFDocument.parse(src)
    assert doc.frontmatter == {}
    assert "Hello" in doc.body


def test_parse_ignores_utf8_bom():
    doc = OKFDocument.parse("\ufeff---\ntype: X\n---\n\nBody.\n")
    assert doc.frontmatter == {"type": "X"}
    assert doc.body == "Body."


def test_parse_accepts_crlf_line_endings():
    doc = OKFDocument.parse("---\r\ntype: X\r\n---\r\n\r\nBody.\r\n")
    assert doc.frontmatter == {"type": "X"}
    assert doc.body == "Body."


def test_unterminated_frontmatter_raises():
    src = "---\ntype: X\nstill in frontmatter\n"
    with pytest.raises(OKFDocumentError):
        OKFDocument.parse(src)


def test_validate_rejects_missing_type():
    doc = OKFDocument(frontmatter={"title": "Y"})
    with pytest.raises(OKFDocumentError) as exc:
        doc.validate()
    assert "type" in str(exc.value)


def test_validate_accepts_type_only():
    # OKF v0.3 §4.1: `type` is the only always-required key.
    OKFDocument(frontmatter={"type": "X"}).validate()


def test_normalize_verified_treats_bare_mapping_as_list():
    fm = {"verified": {"by": "human:ahormati", "at": "2026-06-25T09:00:00Z"}}
    assert normalize_verified(fm) == [
        {"by": "human:ahormati", "at": "2026-06-25T09:00:00Z"}
    ]
    assert normalize_verified({}) == []


def test_trust_tier():
    assert trust_tier({}) == "unverified"
    assert trust_tier(
        {"verified": [{"by": "process:finance-nightly", "at": "x"}]}
    ) == "machine-confirmed"
    assert trust_tier(
        {"verified": [
            {"by": "process:finance-nightly", "at": "x"},
            {"by": "human:ahormati", "at": "y"},
        ]}
    ) == "human-reviewed"
    # A bare mapping is treated as a one-element list.
    assert trust_tier({"verified": {"by": "human:ahormati", "at": "z"}}) == "human-reviewed"
    # An event without both `by` and `at` is ignored.
    assert trust_tier({"verified": {"by": "human:ahormati"}}) == "unverified"


def test_trust_tier_uses_only_current_events():
    generated = {"by": "reference_agent/x", "at": "2026-06-20T14:00:00Z"}
    human_before = {"by": "human:ahormati", "at": "2026-06-01T09:00:00Z"}
    human_same = {"by": "human:ahormati", "at": "2026-06-20T14:00:00Z"}
    process_after = {"by": "process:nightly", "at": "2026-06-21T02:00:00+00:00"}
    # A review before the last change is history, not a current event (v0.3 §5.3).
    assert trust_tier({"generated": generated, "verified": [human_before]}) == "unverified"
    assert trust_tier(
        {"generated": generated, "verified": [human_before, process_after]}
    ) == "machine-confirmed"
    assert trust_tier({"generated": generated, "verified": [human_same]}) == "human-reviewed"
    # Date-only and YAML-native timestamps compare as instants.
    assert trust_tier(
        {"generated": {"by": "a/b", "at": "2026-06-20"}, "verified": {"by": "human:a", "at": date(2026, 6, 20)}}
    ) == "human-reviewed"
    # A timestamp that does not parse cannot make an event current.
    assert trust_tier(
        {"generated": generated, "verified": {"by": "human:ahormati", "at": "soon"}}
    ) == "unverified"


def test_is_stale():
    ref = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    assert is_stale({"stale_after": "2026-09-23T00:00:00Z"}, now=ref) is True
    assert is_stale({"stale_after": "2026-09-24T00:00:00Z"}, now=ref) is False
    assert is_stale({"stale_after": "2026-09-23T14:00:00+02:00"}, now=ref) is True
    assert is_stale({}, now=ref) is False
    assert is_stale({"stale_after": None}, now=ref) is False
    assert is_stale({"stale_after": ""}, now=ref) is False
    # A date-only value is the start of that day in UTC (v0.3 §5).
    assert is_stale({"stale_after": "2026-09-23"}, now=ref) is True
    assert is_stale({"stale_after": "2026-09-24"}, now=ref) is False
    # YAML-native values are accepted too.
    assert is_stale({"stale_after": date(2026, 9, 23)}, now=ref) is True
    assert is_stale({"stale_after": datetime(2026, 9, 24, tzinfo=timezone.utc)}, now=ref) is False
    # A value that does not parse is never fresh (v0.3 §5.5).
    assert is_stale({"stale_after": "not-a-date"}, now=ref) is True
    assert is_stale({"stale_after": "2026-09-23T00:00:00"}, now=ref) is True
    assert is_stale({"stale_after": "2026-09-23 00:00:00Z"}, now=ref) is True
    assert is_stale({"stale_after": "2026-02-30"}, now=ref) is True


def test_parse_timestamp():
    utc = timezone.utc
    assert parse_timestamp("2026-06-30T14:00:00Z") == datetime(2026, 6, 30, 14, tzinfo=utc)
    assert parse_timestamp("2026-06-30t14:00:00.5z") == datetime(2026, 6, 30, 14, 0, 0, 500000, tzinfo=utc)
    assert parse_timestamp("2026-06-30") == datetime(2026, 6, 30, tzinfo=utc)
    assert parse_timestamp(datetime(2026, 6, 30, 14)) is None
    assert parse_timestamp("20260630") is None
    assert parse_timestamp(20260630) is None


def test_serialize_keeps_timestamp_quoting():
    src = (
        "---\n"
        "type: Metric\n"
        "stale_after: 2026-09-23T00:00:00Z\n"
        "verified:\n"
        "- by: human:ahormati\n"
        "  at: 2026-06-30\n"
        "generated: {by: agent, at: '2026-05-28T14:30:00Z'}\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    out = OKFDocument.parse(src).serialize()
    assert "stale_after: 2026-09-23T00:00:00Z\n" in out
    assert "  at: 2026-06-30\n" in out
    assert "at: '2026-05-28T14:30:00Z'" in out
    # A new document quotes timestamp-like strings.
    new = OKFDocument(frontmatter={"type": "x", "stale_after": "2026-09-23"})
    assert "stale_after: '2026-09-23'" in new.serialize()

