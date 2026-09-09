"""Tests for the long-task-planning evals infrastructure.

Covers:
  - fixture validity (case schemas, anchor ids, type coverage A-L+hybrid)
  - the static scorer on the known-good example plan (data-driven)
  - prose parsing + scoring (incl. the G2 gaming guard)
  - a full prepare -> score -> report round trip on one fixture (no subagents)
  - aggregation + report rendering on synthetic results
  - prompt/orchestration hygiene (placeholders, ablation templates)
  - runner<->schema conformance (spec + result shapes)

Run:
    $env:UV_CACHE_DIR = "<repo>/.cache/uv"
    uv run --no-project python -m unittest discover -s tests/planning-evals -t .
"""

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals" / "long-task-planning"
FIXTURES = EVALS / "fixtures"
EXAMPLE = ROOT / "examples" / "long-task-planning"

sys.path.insert(0, str(EVALS / "runners"))
sys.path.insert(0, str(EVALS / "scorers"))

import aggregate  # noqa: E402
import eval_runner  # noqa: E402
import static_scorer  # noqa: E402
from prose_parser import parse_plan_md  # noqa: E402


@contextlib.contextmanager
def scratch_dir(parent: Path):
    """Plain os.mkdir scratch dir (no explicit mode — see fixture notes:
    the eval sandbox's mkdir hook denies access under 0o700 dirs, which is
    exactly what tempfile.mkdtemp passes)."""
    d = parent / f"scratch_{os.getpid()}_{time.time_ns()}"
    os.mkdir(d)
    try:
        yield d
    finally:
        _remove_tree(d)


def _case_json(d: Path) -> dict:
    return json.loads((d / "case.json").read_text(encoding="utf-8"))


def _remove_tree(d: Path) -> None:
    """Remove a directory tree, falling back to pwsh Remove-Item.

    The eval sandbox denies Python ``os.unlink`` on some files (e.g. the
    object files a fixture ``work/repo/.git`` holds) even though pwsh
    ``Remove-Item`` can delete them, so a plain ``shutil.rmtree`` can leave a
    tree behind. Try Python first, then shell out."""
    d = Path(d)
    if not d.exists():
        return
    shutil.rmtree(d, ignore_errors=True)
    if d.exists():
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Remove-Item -Recurse -Force -LiteralPath '{d}'"],
            capture_output=True)


class TestFixtures(unittest.TestCase):
    def _fixture_dirs(self):
        return [d for d in sorted(FIXTURES.iterdir())
                if d.is_dir() and (d / "case.json").exists()]

    def test_at_least_12_cases(self):
        self.assertGreaterEqual(len(self._fixture_dirs()), 12,
                                "bootstrap §15 requires >= 12 independent cases")

    def test_case_schemas_valid(self):
        for d in self._fixture_dirs():
            errs = static_scorer.validate_json_against(
                _case_json(d), EVALS / "schemas" / "case.schema.json")
            self.assertEqual(errs, [], f"{d.name}: {errs[:3]}")

    def test_anchor_ids_unique_and_wellformed(self):
        for d in self._fixture_dirs():
            c = _case_json(d)
            ids = [a["id"] for a in c["anchors"]]
            self.assertEqual(len(ids), len(set(ids)), f"{d.name}: duplicate anchor ids")
            for i in ids:
                self.assertRegex(i, r"^A[0-9]+$", f"{d.name}: bad anchor id {i}")
                self.assertTrue(c["anchors"][ids.index(i)]["files"], f"{d.name}: {i} has no files")

    def test_anchor_files_exist_in_repo(self):
        for d in self._fixture_dirs():
            c = _case_json(d)
            repo = d / c["repo_fixture"]
            for a in c["anchors"]:
                for f in a["files"]:
                    self.assertTrue((repo / f).exists(), f"{d.name}: anchor file missing {f}")

    def test_type_coverage_all_twelve_plus_hybrid(self):
        types = {_case_json(d)["type"] for d in self._fixture_dirs()}
        for t in "ABCDEFGHIJKL":
            self.assertIn(t, types, f"no case of type {t}")
        self.assertIn("hybrid", types)

    def test_scope_bait_does_not_conflict_with_anchors(self):
        """must_not_expand entries may be existing files ('do not modify'
        traps, e.g. case-06 legacy_export) or invented modules — but they
        must never be anchor files (a forbidden anchor is a self-contradiction)."""
        for d in self._fixture_dirs():
            c = _case_json(d)
            anchor_files = {f for a in c["anchors"] for f in a["files"]}
            for p in c["expected"].get("must_not_expand_scope", []):
                base = p.split("/")[-1]
                self.assertFalse(
                    p in anchor_files or base in anchor_files,
                    f"{d.name}: scope bait {p} conflicts with an anchor")


class TestCandidateScoring(unittest.TestCase):
    """Data-driven scoring of the known-good example plan.

    The synthetic case is built from the plan's own artifacts (anchor per
    leaf task's first owned path; must-have edge taken from the real DAG),
    so the test stays valid if the example narrative changes.
    """

    @classmethod
    def setUpClass(cls):
        cands = json.loads((EXAMPLE / "candidate-tasks.json").read_text(encoding="utf-8"))["tasks"]
        dag = json.loads((EXAMPLE / "dag.json").read_text(encoding="utf-8"))
        cls.by_id = {t["id"]: t for t in cands}
        cls.dag = dag
        cls.case = {
            "id": "case-99-synthetic",
            "type": "E",
            "title": "synthetic scoring case",
            "description": "built from the example plan for scorer tests",
            "task_prompt_file": "input.md",
            "repo_fixture": ".",
            "anchors": [
                {"id": "A1", "files": [cls.by_id["T01"]["owned_paths"][0]], "description": "t01"},
                {"id": "A2", "files": [cls.by_id["T02"]["owned_paths"][0]], "description": "t02"},
                {"id": "A3", "files": [cls.by_id["T03"]["owned_paths"][0]], "description": "t03"},
                {"id": "A4", "files": [cls.by_id["T04"]["owned_paths"][0]], "description": "t04"},
            ],
            "expected": {
                "must_freeze": [{"anchor_ids": ["A1"], "kind": "contract", "note": "n"}],
                "must_not_expand_scope": [],
                "must_have_edges": [
                    {"from_anchor": "A1", "to_anchor": "A4", "types": ["data"],
                     "note": "real dag edge T01->T04"}
                ],
                "must_not_have_edges": [
                    {"from_anchor": "A2", "to_anchor": "A3",
                     "reason": "no T02<->T03 edge in the example dag (fake serialization removed)"}
                ],
                "parallelizable_groups": [{"anchor_ids": ["A1", "A2"]}],
                "acceptable_task_count_range": [3, 6],
                "max_anchors_per_task": 3,
            },
        }
        cls.res = static_scorer.score_candidate_plan(cls.case, EXAMPLE)

    def test_produced_and_structural(self):
        self.assertTrue(self.res["produced"])
        sv = self.res["structural_validity"]
        self.assertEqual(sv["lint_exit"], 0, "example plan must lint clean")
        self.assertEqual(sv["findings"]["blocker"], 0)
        self.assertEqual(sv["audit_verdict"], "PASS")

    def test_contract_completeness(self):
        cc = self.res["contract_completeness"]
        self.assertIsInstance(cc, float)
        self.assertGreater(cc, 0.0)
        self.assertLessEqual(cc, 1.0)

    def test_must_have_edge_hit(self):
        mh = self.res["dependency_precision"]["must_have"]
        self.assertEqual(mh["total"], 1)
        self.assertEqual(mh["hit"], 1, mh["details"])

    def test_must_not_have_not_violated(self):
        mnh = self.res["dependency_precision"]["must_not_have"]
        self.assertEqual(mnh["total"], 1)
        self.assertEqual(mnh["violated"], 0, mnh["details"])

    def test_no_cycles(self):
        self.assertEqual(self.res["dependency_precision"]["cycles"], 0)

    def test_parallel_group_membership(self):
        par = self.res["parallelizable_groups"][0]
        self.assertIn("T01", par["tasks"])
        self.assertIn("T02", par["tasks"])
        self.assertIsInstance(par["ok"], bool)
        # consistency: a violation must name an ordered member pair
        if not par["ok"]:
            self.assertTrue(re.match(r"^[^->]+->[^->]+$", par["violated_by"]))

    def test_task_count_in_range(self):
        tc = self.res["task_count"]
        self.assertEqual(tc["actual"], 4, "example has 4 leaf candidates")
        self.assertTrue(tc["in_range"])

    def test_metric_coverage_marks_assessed_dimensions(self):
        cov = self.res["metric_coverage"]
        for k in ("contract_completeness", "context_locality", "ownership_collisions",
                  "dependency_precision", "integration_explicitness", "leaf_boundedness",
                  "scope_discipline"):
            self.assertEqual(cov.get(k), "assessed", k)
        self.assertIsInstance(self.res["judge_pending"], list)


class TestProseScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case01 = _case_json(FIXTURES / "case-01-weekly-batch-export")
        repo = FIXTURES / "case-01-weekly-batch-export" / "repo"
        cls.repo_files = [p.relative_to(repo).as_posix()
                          for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]

    def test_parser_extracts_tasks_and_files(self):
        text = ("# Plan\n\n## Phase 1\n\n"
                "1. Update analytics/metrics.py and analytics/queries.py\n"
                "2. Build analytics/csv_writer.py and analytics/scheduler.py "
                "in parallel\n\n"
                "## Out of scope\nnothing else.\n")
        parsed = parse_plan_md(text, self.repo_files)
        self.assertEqual(len(parsed["tasks"]), 2)
        self.assertIn("analytics/metrics.py", parsed["tasks"][0]["files"])
        self.assertTrue(parsed["parallel_marker_any"])

    def test_good_prose_plan_scores(self):
        text = """# Plan for the weekly batch export

Objective: deliver the Monday batch export job. The task is to extend the
analytics service with a scheduled CSV export of the weekly metrics.

## Phase 1

1. Refactor analytics/metrics.py and analytics/queries.py to expose the
   weekly aggregation (this depends on nothing else).
2. Implement analytics/csv_writer.py and wire analytics/scheduler.py —
   these two can be done in parallel once the aggregation exists.

## Integration

End-to-end: the scheduler triggers the export and the CSV bytes match the
query output.

## Out of scope

analytics/alerts.py and dashboard.py are out of scope for this task.

## Acceptance

Unit tests pass: test_analytics.py asserts the CSV rows and the
scheduler trigger for Monday 2026-07-06.

## Replan

If the aggregation refactor fails, reduce scope to a manual export first.
"""
        res = static_scorer.score_prose_plan(self.case01, text, self.repo_files)
        self.assertTrue(res["produced"])
        self.assertEqual(res["variant_kind"], "prose")
        self.assertIsNone(res["structural_validity"]["lint_exit"])
        self.assertIsInstance(res["contract_completeness"], float)
        self.assertGreaterEqual(res["contract_completeness"], 0.5)
        self.assertGreaterEqual(res["task_count"]["actual"], 2)
        # no gaming flags: parallelism named, files mentioned, count in range
        codes = {f["code"] for f in res["gaming_flags"]}
        self.assertNotIn("G2_ALL_SERIAL", codes)
        self.assertNotIn("G3_CONTEXT_STARVATION", codes)
        # merge cluster A1+A2 satisfied by task 1; separate cluster A3/A4 by task 2
        self.assertEqual(res["scope_discipline"]["creep_items_planned"], [])

    def test_linear_prose_triggers_g2(self):
        text = """# Linear plan

1. Update analytics/metrics.py first.
2. Then update analytics/queries.py after the metrics change is done.
3. Then build analytics/csv_writer.py after the queries are done.
4. Then add analytics/scheduler.py last.

## Out of scope

analytics/alerts.py.

## Acceptance

tests pass.
"""
        res = static_scorer.score_prose_plan(self.case01, text, self.repo_files)
        codes = {f["code"] for f in res["gaming_flags"]}
        self.assertIn("G2_ALL_SERIAL", codes,
                      "a plan with zero parallel markers must be flagged")


class TestRunnerRoundTrip(unittest.TestCase):
    """prepare -> (host writes a baseline plan) -> score -> report, no subagents."""

    run_id = None

    @classmethod
    def setUpClass(cls):
        cls.run_id = f"selftest-{time.time_ns()}"
        rc = eval_runner.prepare(cls.run_id,
                                 ["case-01-weekly-batch-export"],
                                 ["baseline-a", "candidate"],
                                 ROOT / ".agents" / "skills")
        assert rc == 0, "prepare failed"
        cls.run_root = eval_runner.RUNS / cls.run_id
        ba = cls.run_root / "case-01-weekly-batch-export" / "baseline-a"
        # the 'host session' writes the baseline prose plan + wall time
        (ba / "out" / "plan.md").write_text(
            "# Baseline A plan\n\n"
            "Objective: deliver the Monday weekly batch export job for the analytics service. "
            "The task is to extend the existing analytics package with a scheduled CSV export "
            "of the weekly metrics rollup so the ops team gets a file every Monday morning without "
            "running any manual queries or shell commands at all.\n\n"
            "## Tasks\n\n"
            "1. Update analytics/metrics.py and analytics/queries.py so the weekly rollup can be "
            "computed from a single entry point; this is the foundation everything else builds on.\n"
            "2. Implement analytics/csv_writer.py and wire it into analytics/scheduler.py — these "
            "two can be done in parallel once the rollup entry point exists.\n\n"
            "## Out of scope\n\n"
            "analytics/alerts.py and dashboard.py are not touched by this work; no new services, "
            "no new dependencies, no changes to the existing daily paths.\n\n"
            "## Acceptance\n\n"
            "Unit tests in tests/test_analytics.py pass, and a new test asserts the CSV rows and "
            "the scheduler trigger for Monday 2026-07-06.\n",
            encoding="utf-8")
        (ba / "timing.json").write_text(
            json.dumps({"wall_time_seconds": 12.5}), encoding="utf-8")
        cls.rc_score = eval_runner.score(cls.run_id)

    @classmethod
    def tearDownClass(cls):
        _remove_tree(cls.run_root)
        for ext in (".md", ".json"):
            p = eval_runner.REPORTS / f"{cls.run_id}-report{ext}"
            if p.exists():
                p.unlink()

    def test_01_prepare_layout(self):
        ba = self.run_root / "case-01-weekly-batch-export" / "baseline-a"
        self.assertTrue((ba / "work" / "repo" / ".git").is_dir(), "baseline commit missing")
        self.assertTrue((ba / "work" / "repo" / "analytics" / "metrics.py").exists())
        self.assertTrue((ba / "task.md").exists())
        self.assertTrue((ba / "spec.json").exists())
        manifest = json.loads((self.run_root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["specs"]), 2)
        self.assertEqual(manifest["model"]["name"], "host-session-model")

    def test_02_prompts_rendered_no_leftover_placeholders(self):
        known = {"task_prompt", "work_dir", "plan_out", "telemetry_file",
                 "skills_dir", "glossary", "plan_check", "uv_cache", "ablation_block"}
        for variant in ("baseline-a", "candidate"):
            p = self.run_root / "case-01-weekly-batch-export" / variant / "prompt.md"
            left = set(re.findall(r"\{([a-z_]+)\}", p.read_text(encoding="utf-8")))
            self.assertTrue(left <= known, f"{variant}: unrendered placeholders {left - known}")

    def test_03_spec_validates(self):
        spec = json.loads((self.run_root / "case-01-weekly-batch-export" / "baseline-a"
                           / "spec.json").read_text(encoding="utf-8"))
        errs = static_scorer.validate_json_against(
            spec, EVALS / "schemas" / "run-spec.schema.json")
        self.assertEqual(errs, [])

    def test_04_score_round_trip(self):
        self.assertEqual(self.rc_score, 0)
        ba = self.run_root / "case-01-weekly-batch-export" / "baseline-a"
        cand = self.run_root / "case-01-weekly-batch-export" / "candidate"
        res_ba = json.loads((ba / "run-result.json").read_text(encoding="utf-8"))
        res_cand = json.loads((cand / "run-result.json").read_text(encoding="utf-8"))
        for res in (res_ba, res_cand):
            errs = static_scorer.validate_json_against(
                res, EVALS / "schemas" / "run-result.schema.json")
            self.assertEqual(errs, [], f"run-result schema drift: {errs[:3]}")
            for dim in ("success", "wall_time", "tokens", "context_read", "rework",
                        "integration_defects", "scope_creep", "replans",
                        "compactions", "local_recoverability"):
                self.assertIn(dim, res["e_vector"], dim)
        self.assertTrue(res_ba["planning"]["produced"])
        self.assertEqual(res_ba["e_vector"]["wall_time"], 12.5,
                         "timing.json must merge into the E vector")
        self.assertIsNone(res_ba["e_vector"]["tokens"])
        self.assertFalse(res_cand["planning"]["produced"],
                         "empty candidate out/ must score as produced=false")

    def test_05_report(self):
        rc = eval_runner.report(self.run_id)
        self.assertEqual(rc, 0)
        md_p = eval_runner.REPORTS / f"{self.run_id}-report.md"
        js_p = eval_runner.REPORTS / f"{self.run_id}-report.json"
        self.assertTrue(md_p.exists())
        self.assertTrue(js_p.exists())
        md = md_p.read_text(encoding="utf-8")
        md_low = md.lower()
        for needle in ("contract completeness", "dependency precision",
                       "ownership", "scope discipline", "e vector",
                       "per-case matrix", "do not read single metrics"):
            self.assertIn(needle, md_low, f"report missing section: {needle}")
        payload = json.loads(js_p.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["runs"]), 2)


class TestSchemasConformance(unittest.TestCase):
    """Pin the runner<->schema contract so future drift fails fast."""

    def test_spec_shape(self):
        spec = {
            "run_id": "r1", "case_id": "case-01-weekly-batch-export",
            "variant": "ablation-full-minus-integration",
            "ablation_remove": "full-minus-integration",
            "model": {"name": "host-session-model", "note": "n"},
            "run_index": 0, "created_at": "2026-07-08T00:00:00Z",
            "skills_dir": "D:/x", "protocol_version": "1",
            "paths": {"run_dir": "D:/r", "work_dir": "D:/w", "task_prompt": "D:/t",
                      "prompt_file": "D:/p", "plan_out": "D:/o", "telemetry_file": "D:/tl"},
        }
        self.assertEqual(static_scorer.validate_json_against(
            spec, EVALS / "schemas" / "run-spec.schema.json"), [])

    def test_result_shape(self):
        res = {
            "run_id": "r1", "case_id": "case-01-weekly-batch-export",
            "planner_variant": "baseline-a", "model": "host-session-model",
            "seed_or_run_index": 0, "phase": "planning-only",
            "planning": {
                "produced": True,
                "structural_validity": {"lint_exit": None,
                                        "findings": {"blocker": 0, "major": 0, "minor": 0},
                                        "audit_verdict": None, "audit_rounds": None,
                                        "note": "n/a for prose plans (no schema artifacts)"},
            },
            "execution": None,
            "e_vector": {"success": None, "wall_time": 1.5, "tokens": None,
                         "context_read": 2.0, "rework": None, "integration_defects": None,
                         "scope_creep": 0, "replans": None, "compactions": None,
                         "local_recoverability": None},
            "artifacts": {"plan_dir": "D:/o", "score_file": "D:/r.json",
                          "trace": None, "diff": None, "tests": None},
            "notes": {"tokens": "not observable", "compactions": "not observable"},
        }
        self.assertEqual(static_scorer.validate_json_against(
            res, EVALS / "schemas" / "run-result.schema.json"), [])


class TestAggregate(unittest.TestCase):
    def _res(self, case_id, variant, wall, cc):
        return {
            "run_id": "agg", "case_id": case_id, "planner_variant": variant,
            "model": "m", "phase": "planning-only",
            "planning": {
                "produced": True,
                "contract_completeness": cc,
                "structural_validity": {"lint_exit": 0,
                                        "findings": {"blocker": 0, "major": 0, "minor": 0}},
                "dependency_precision": {"must_have": {"hit": 1, "total": 1},
                                         "must_not_have": {"violated": 0, "total": 0}},
                "scope_discipline": {"creep_items_planned": [], "out_of_scope_named": []},
                "gaming_flags": [], "judge_pending": [],
            },
            "execution": None,
            "e_vector": {"success": True, "wall_time": wall, "tokens": None,
                         "context_read": None, "rework": None, "integration_defects": None,
                         "scope_creep": 0, "replans": 0, "compactions": None,
                         "local_recoverability": None},
            "artifacts": {"plan_dir": "x", "score_file": "y"},
        }

    def test_aggregate_and_render(self):
        results = [self._res("case-01-weekly-batch-export", "candidate", 10.0, 0.9),
                   self._res("case-02-durable-sms", "candidate", 30.0, 0.7),
                   self._res("case-01-weekly-batch-export", "baseline-a", 5.0, 0.8)]
        agg = aggregate.aggregate(results)
        self.assertEqual(agg["candidate"]["runs"], 2)
        self.assertEqual(agg["candidate"]["e_vector"]["wall_time"]["mean"], 20.0)
        rows = {r["metric"]: r for r in agg["candidate"]["metrics"]}
        self.assertAlmostEqual(rows["Contract completeness"]["mean"], 0.8)
        with scratch_dir(Path(__file__).parent) as d:
            md_p, js_p = aggregate.write_report("agg-test", results, d)
            self.assertTrue(md_p.exists() and js_p.exists())
            md = md_p.read_text(encoding="utf-8")
            self.assertIn("## Variant: `candidate`", md)
            self.assertIn("## Variant: `baseline-a`", md)
            payload = json.loads(js_p.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["runs"]), 3)


class TestPromptsAndOrchestration(unittest.TestCase):
    PROMPTS = EVALS / "runners" / "prompts"
    KNOWN = {"task_prompt", "work_dir", "plan_out", "telemetry_file",
             "skills_dir", "glossary", "plan_check", "uv_cache", "ablation_block",
             "ablation_note",
             "round"}  # 'round' is rendered host-side by the audit orchestration

    def test_all_core_prompts_exist(self):
        for name in ("candidate.md", "baseline-a.md", "baseline-b.md", "audit.md",
                     "executor.md", "revision.md"):
            self.assertTrue((self.PROMPTS / name).is_file(), name)

    def test_placeholder_hygiene(self):
        for f in sorted(self.PROMPTS.glob("*.md")):
            left = set(re.findall(r"\{([a-z_]+)\}", f.read_text(encoding="utf-8")))
            self.assertTrue(left <= self.KNOWN, f"{f.name}: unknown placeholders {left - self.KNOWN}")

    def test_ablation_templates_cover_all_ablations(self):
        for a in eval_runner.ABLATIONS:
            self.assertIn(a, eval_runner.ABLATION_TEMPLATE, a)
            self.assertIn("## Stage override", eval_runner.ABLATION_TEMPLATE[a])

    def test_orchestration_invariants_documented(self):
        txt = (EVALS / "runners" / "ORCHESTRATION.md").read_text(encoding="utf-8")
        for needle in ("case.json", "telemetry", "audit", "timing.json", "subagent"):
            self.assertIn(needle.lower(), txt.lower(), f"ORCHESTRATION.md missing: {needle}")

    def test_workflow_template_placeholders(self):
        txt = (EVALS / "runners" / "workflow_template.js").read_text(encoding="utf-8")
        self.assertIn("{{RUN_ID}}", txt)
        self.assertIn("{{SPECS_JSON}}", txt)
        self.assertIn("planWithAudit", txt)


def run() -> int:
    """Hook for tests/planning-evals/run_tests.py (same convention as
    the planning-skills suite). Returns the failure count."""
    import unittest as _ut

    loader = _ut.TestLoader()
    suite = _ut.TestSuite()
    for name, obj in sorted(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, _ut.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    result = _ut.TextTestRunner(verbosity=2).run(suite)
    return len(result.failures) + len(result.errors)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
