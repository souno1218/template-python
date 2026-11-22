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

"""Tests for the agent skills in skills/ and the plugin manifests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
BUNDLES = REPO / "bundles"
VALIDATE = SKILLS / "okf-generate" / "scripts" / "validate.py"
SCAN = SKILLS / "okf-consume" / "scripts" / "scan.py"

PLUGIN_NAME = "okf"
VERSION = "0.1.0"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _load_json(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    head, _, body = text[4:].partition("\n---\n")
    return yaml.safe_load(head), body


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True, check=False
    )


def _write(root: Path, relpath: str, text: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---- plugin manifests --------------------------------------------------------


def test_manifests_name_version_and_description_agree():
    claude_market = _load_json(".claude-plugin/marketplace.json")
    claude_plugin = _load_json("skills/.claude-plugin/plugin.json")
    codex_market = _load_json(".agents/plugins/marketplace.json")
    codex_plugin = _load_json("skills/.codex-plugin/plugin.json")
    antigravity = _load_json(".antigravity-plugin/plugin.json")

    claude_entry = claude_market["plugins"][0]
    codex_entry = codex_market["plugins"][0]

    names = [claude_entry, claude_plugin, codex_entry, codex_plugin, antigravity]
    assert {m["name"] for m in names} == {PLUGIN_NAME}

    versioned = [claude_entry, claude_plugin, codex_plugin, antigravity]
    assert {m["version"] for m in versioned} == {VERSION}

    described = [claude_entry, claude_plugin, codex_plugin, antigravity]
    assert len({m["description"] for m in described}) == 1


def test_manifests_make_the_skills_dir_the_plugin_root():
    # The marketplaces stay at the repository root, where `owner/repo` installs
    # look for them. The plugin is skills/, so an install copies only the skills.
    claude_entry = _load_json(".claude-plugin/marketplace.json")["plugins"][0]
    codex_entry = _load_json(".agents/plugins/marketplace.json")["plugins"][0]
    claude_plugin = _load_json("skills/.claude-plugin/plugin.json")
    codex_plugin = _load_json("skills/.codex-plugin/plugin.json")

    assert claude_entry["source"] == "./skills"
    assert codex_entry["source"] == {"source": "local", "path": "./skills"}
    assert claude_plugin["skills"] == "./"
    assert codex_plugin["skills"] == "./"


# ---- skill folders -----------------------------------------------------------


# A skill is a folder with a SKILL.md. Other folders, such as a local evals/
# directory that git ignores, are not skills.
SKILL_DIRS = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def test_expected_skills_exist():
    assert [p.name for p in SKILL_DIRS] == ["okf-consume", "okf-generate"]


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
def test_skill_frontmatter_follows_agent_skills_limits(skill_dir: Path):
    meta, body = _frontmatter(skill_dir / "SKILL.md")
    assert meta["name"] == skill_dir.name
    assert NAME_RE.match(meta["name"]) and len(meta["name"]) <= 64
    assert 0 < len(meta["description"]) <= 1024
    assert len(body.splitlines()) < 500


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
def test_skill_frontmatter_has_license_version_and_publisher(skill_dir: Path):
    meta, _ = _frontmatter(skill_dir / "SKILL.md")
    assert meta["license"] == _load_json("skills/.claude-plugin/plugin.json")["license"]
    # Agent Skills metadata maps string keys to string values.
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in meta["metadata"].items())
    assert meta["metadata"]["version"] == VERSION
    assert meta["metadata"]["publisher"] == "google"


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
def test_skill_relative_links_resolve(skill_dir: Path):
    for md in skill_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        text = re.sub(r"(?ms)^(`{3,}|~{3,}).*?^\1[ \t]*$", "", text)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in LINK_RE.findall(text):
            if "://" in target or target.startswith("#"):
                continue
            assert (md.parent / target.split("#")[0]).exists(), f"{md}: {target}"



# ---- validate.py (OKF v0.3) --------------------------------------------------


def _codes(result: subprocess.CompletedProcess) -> set[str]:
    return {f["code"] for f in json.loads(result.stdout)["findings"]}


@pytest.mark.parametrize(
    "bundle", sorted(p for p in BUNDLES.iterdir() if p.is_dir()), ids=lambda p: p.name
)
def test_validate_passes_on_shipped_bundles(bundle: Path):
    result = _run(VALIDATE, str(bundle))
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_reports_each_conformance_error(tmp_path: Path):
    _write(tmp_path, "bad_yaml.md", "---\ntype: [unclosed\n---\n")
    _write(tmp_path, "dupe.md", "---\ntype: Metric\ntitle: A\ntitle: B\n---\n")
    _write(tmp_path, "tables/index.md", "---\ntitle: Tables\n---\n\n# Tables\n")
    _write(tmp_path, "log.md", "---\ntype: Log\n---\n\n# History\n\n## May 2026\n")

    result = _run(VALIDATE, str(tmp_path), "--json")
    assert result.returncode == 1
    assert {"E002", "E004", "E005", "E006", "E007"} <= _codes(result)


def test_validate_warns_but_passes_on_files_that_are_not_concepts(tmp_path: Path):
    _write(tmp_path, "README.md", "# About this bundle\n")
    _write(tmp_path, "notes.md", "---\ntitle: Notes\n---\n\nNo type here.\n")

    result = _run(VALIDATE, str(tmp_path), "--json")
    assert result.returncode == 0
    assert "W120" in _codes(result)


def test_validate_allows_bundle_metadata_in_root_index_only(tmp_path: Path):
    _write(
        tmp_path,
        "index.md",
        '---\nokf_version: "0.3"\ntitle: Acme\ndescription: Acme finance metrics.\n'
        "license: CC-BY-4.0\nx-acme-owner: finance\n---\n\n# Acme\n",
    )
    _write(tmp_path, "orders.md", "---\ntype: BigQuery Table\n---\n")
    assert _run(VALIDATE, str(tmp_path)).returncode == 0

    _write(tmp_path, "sub/index.md", '---\nokf_version: "0.3"\n---\n\n# Sub\n')
    assert _run(VALIDATE, str(tmp_path)).returncode == 1


def test_validate_strict_fails_on_warnings(tmp_path: Path):
    _write(
        tmp_path,
        "orders.md",
        "---\ntype: BigQuery Table\nstatus: retired\ntags: sales, orders\n"
        'generated: { by: someone, at: "2026-06-30T10:00" }\n---\n\n'
        "Orders.[^missing]\n\nSee [customers](customers.md).\n",
    )
    result = _run(VALIDATE, str(tmp_path), "--json")
    assert result.returncode == 0
    assert {"W101", "W103", "W105", "W108", "W110", "W115"} <= _codes(result)
    assert _run(VALIDATE, str(tmp_path), "--strict").returncode == 1


def test_validate_accepts_date_only_timestamps(tmp_path: Path):
    _write(
        tmp_path,
        "policy.md",
        '---\ntype: Policy\nstale_after: "2099-12-31"\n'
        'generated: { by: "human:jsmith", at: "2026-06-30" }\n'
        "sources:\n  - { id: p, resource: https://example.com/p, last_modified: 2026-06-01 }\n"
        "---\n\nText.[^p]\n\n[^p]: Policy\n",
    )
    codes = _codes(_run(VALIDATE, str(tmp_path), "--json"))
    assert "W101" not in codes
    assert "W122" in codes  # generated.at SHOULD be a date-time (section 5)


def test_validate_checks_attested_computation_contract(tmp_path: Path):
    _write(
        tmp_path,
        "computations/revenue.md",
        "---\ntype: Attested Computation\nparameters:\n  - { name: year }\n"
        "executor: { resource: /skills/run.md }\n---\n\nNo computation here.\n",
    )
    assert {"W111", "W112", "W113", "W114", "W116"} <= _codes(
        _run(VALIDATE, str(tmp_path), "--json")
    )


def test_validate_finds_a_computation_under_any_heading_level(tmp_path: Path):
    _write(
        tmp_path,
        "computations/revenue.md",
        "---\ntype: Attested Computation\nruntime: sqlite\n"
        "parameters:\n  - { name: year, type: integer }\n---\n\n"
        "## Computation\n\n```sql\nSELECT 1\n```\n",
    )
    codes = _codes(_run(VALIDATE, str(tmp_path), "--json"))
    assert "W112" not in codes and "W113" not in codes


def test_validate_resolves_bare_paths_from_the_file_directory(tmp_path: Path):
    concept = (
        "---\ntype: Attested Computation\nruntime: sqlite\n"
        "executor: { resource: skills/run.md, receipt: [result] }\n---\n\n"
        "# Computation\n\n```sql\nSELECT 1\n```\n"
    )
    _write(tmp_path, "skills/run.md", "---\ntype: Skill\n---\n")
    _write(tmp_path, "computations/revenue.md", concept)

    # No okf_version: a v0.2 bundle may fall back to the bundle root, with a warning.
    assert "W119" in _codes(_run(VALIDATE, str(tmp_path), "--json"))

    # okf_version 0.3: no fallback, so the path does not resolve.
    _write(tmp_path, "index.md", '---\nokf_version: "0.3"\n---\n\n# B\n')
    codes = _codes(_run(VALIDATE, str(tmp_path), "--json"))
    assert "W116" in codes and "W119" not in codes


def test_validate_checks_superseded_by(tmp_path: Path):
    _write(tmp_path, "old.md", "---\ntype: Metric\nstatus: deprecated\nsuperseded_by: /new.md\n---\n")
    _write(tmp_path, "stray.md", "---\ntype: Metric\nsuperseded_by: /old.md\n---\n")
    codes = _codes(_run(VALIDATE, str(tmp_path), "--json"))
    assert {"W116", "W123"} <= codes


def test_validate_reports_staleness_and_old_verification_as_info(tmp_path: Path):
    _write(
        tmp_path,
        "metric.md",
        '---\ntype: Metric\nstale_after: "2026-01-01T00:00:00Z"\n'
        'generated: { by: "agent/v1", at: "2026-07-02T00:00:00Z" }\n'
        'verified: { by: "human:jsmith", at: "2026-07-01T00:00:00Z" }\n---\n',
    )
    result = _run(VALIDATE, str(tmp_path), "--json", "--now", "2026-10-27T00:00:00Z")
    assert result.returncode == 0
    assert {"I201", "I204"} <= _codes(result)


def test_validate_rejects_a_missing_bundle(tmp_path: Path):
    assert _run(VALIDATE, str(tmp_path / "absent")).returncode == 2


# ---- scan.py (OKF v0.3) ------------------------------------------------------


def _scan(bundle: Path, *args: str) -> dict:
    result = _run(SCAN, str(bundle), "--json", *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _concepts(bundle: Path, *args: str) -> dict:
    return {c["id"]: c for c in _scan(bundle, *args)["concepts"]}


def test_scan_reads_the_shipped_acme_bundle():
    concepts = _concepts(BUNDLES / "acme_retail", "--now", "2026-10-27T00:00:00Z")
    revenue = concepts["computations/revenue-ytd"]
    assert revenue["runtime"] == "bigquery"
    assert revenue["stale"] is False
    assert concepts["metrics/gross-margin-legacy"]["status"] == "deprecated"
    assert "index" not in concepts and "log" not in concepts

    later = _concepts(BUNDLES / "acme_retail", "--now", "2027-01-02T00:00:00Z")
    assert later["computations/revenue-ytd"]["stale"] is True

    summary = _scan(BUNDLES / "acme_retail")
    assert summary["okf_version"] == "0.3"
    assert summary["bundle"]["title"]


def test_scan_counts_only_current_verification(tmp_path: Path):
    _write(
        tmp_path,
        "rewritten.md",
        '---\ntype: Metric\ngenerated: { by: "agent/v1", at: "2026-07-02T00:00:00Z" }\n'
        'verified: { by: "human:jsmith", at: "2026-07-01T00:00:00Z" }\n---\n',
    )
    _write(
        tmp_path,
        "team.md",
        '---\ntype: Metric\ngenerated: { by: "agent/v1", at: "2026-07-01T00:00:00Z" }\n'
        'verified: { by: "team:finance", at: "2026-07-03T00:00:00Z" }\n---\n',
    )
    concepts = _concepts(tmp_path)
    assert concepts["rewritten"]["trust"] == "unverified"
    assert concepts["rewritten"]["verified_before_change"] is True
    assert concepts["team"]["trust"] == "machine-confirmed"


def test_scan_applies_v03_value_rules(tmp_path: Path):
    _write(tmp_path, "README.md", "# Not a concept\n")
    _write(tmp_path, "a.md", "---\ntype: Metric\nstatus: retired\ntags: sales, orders\n---\n")
    _write(tmp_path, "b.md", '---\ntype: Metric\nstale_after: "2026-01-01"\n---\n')
    _write(tmp_path, "c.md", "---\ntype: Metric\nstale_after: soon\n---\n")
    _write(tmp_path, "d.md", "---\ntype: Metric\nstatus: deprecated\nsuperseded_by: /b.md\n---\n")

    result = _scan(tmp_path, "--now", "2026-01-01T00:00:00Z")
    concepts = {c["id"]: c for c in result["concepts"]}
    assert "README" not in concepts and result["summary"]["not_concepts"] == 1
    assert concepts["a"]["tags"] == ["sales, orders"]
    assert concepts["a"]["current"] is False
    assert concepts["b"]["stale"] is True  # a date means the start of that day in UTC
    assert concepts["c"]["stale"] is True  # an unparseable stale_after is never fresh
    assert concepts["d"]["superseded_by"] == "/b.md"

    current = {c["id"] for c in _scan(tmp_path, "--current")["concepts"]}
    assert current == {"b", "c"}


def test_scan_filters_by_type_and_status():
    by_type = _scan(BUNDLES / "acme_retail", "--type", "attested computation")["concepts"]
    assert {c["id"] for c in by_type} == {
        "computations/revenue-ytd",
        "computations/gross-margin-period",
    }
    deprecated = _scan(BUNDLES / "acme_retail", "--deprecated")["concepts"]
    assert [c["id"] for c in deprecated] == ["metrics/gross-margin-legacy"]


def test_scan_grep_searches_the_body(tmp_path: Path):
    _write(tmp_path, "policies/shipping.md", "---\ntype: Policy\ntitle: Shipping policy\n---\nFree over $50.\n")
    _write(
        tmp_path,
        "playbooks/macros.md",
        "---\ntype: Playbook\ntitle: Reply macros\n---\n- Standard shipping is free on orders of $45 or more.\n",
    )
    found = {c["id"] for c in _scan(tmp_path, "--grep", "SHIPPING")["concepts"]}
    assert found == {"policies/shipping", "playbooks/macros"}
