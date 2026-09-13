import copy
import contextlib
import io
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import baseline


class BaselineValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites = [json.loads(p.read_text()) for p in sorted((baseline.ROOT / "inventory/sites").glob("*.json"))]
        cls.source = json.loads((baseline.ROOT / "inventory/source.json").read_text())
        cls.path = baseline.ROOT / "fixtures/baseline/npr/case.json"
        cls.case = json.loads(cls.path.read_text())
        cls.rows = [json.loads(line) for line in (cls.path.parent / "legacy.jsonl").read_text().splitlines()]

    def test_inventory_is_disjoint_exhaustive_and_bounded(self):
        counts = baseline.validate_inventory(self.sites, self.source)
        self.assertEqual(sum(counts.values()), 125)

    def test_missing_duplicate_and_unknown_site_rejected(self):
        for sites in (self.sites[:-1], self.sites[:-1] + [self.sites[0]]):
            with self.assertRaises(ValueError):
                baseline.validate_inventory(sites, self.source)
        sites = copy.deepcopy(self.sites)
        sites[0]["id"] = "InventedExtractor"
        with self.assertRaises(ValueError):
            baseline.validate_inventory(sites, self.source)

    def test_wrong_cohort_rejected(self):
        sites = copy.deepcopy(self.sites)
        site = next(s for s in sites if s["function_bearing"])
        site["cohort"] = "selector-string-1"
        with self.assertRaises(ValueError):
            baseline.validate_inventory(sites, self.source)

    def test_unbalanced_selector_cohort_rejected(self):
        sites = copy.deepcopy(self.sites)
        candidates = [s for s in sites if s["cohort"] == "selector-string-2"]
        for s in candidates[:2]:
            s["cohort"] = "selector-string-1"
        with self.assertRaises(ValueError):
            baseline.validate_inventory(sites, self.source)

    def test_approved_24_22_selector_allocation_is_valid(self):
        sites = copy.deepcopy(self.sites)
        next(s for s in sites if s["cohort"] == "selector-string-2")["cohort"] = "selector-string-1"
        counts = baseline.validate_inventory(sites, self.source)
        self.assertEqual(counts["selector-string-1"], 24)
        self.assertEqual(counts["selector-string-2"], 22)

    def test_bad_provenance_digest_and_status_rejected(self):
        variants = []
        for field, value in (("status", "successful"), ("input_sha256", "0" * 64), ("engine_revision", "master"), ("input", "../escape.html")):
            case = copy.deepcopy(self.case)
            case[field] = value
            variants.append(case)
        case = copy.deepcopy(self.case)
        del case["provenance"]["retention_basis"]
        variants.append(case)
        case = copy.deepcopy(self.case)
        case["provenance"]["source_fixture_sha256"] = "0" * 64
        variants.append(case)
        for field, value in (("created_at", "yesterday"), ("source_url", "not-a-url")):
            case = copy.deepcopy(self.case)
            case["provenance"][field] = value
            variants.append(case)
        for case in variants:
            with self.assertRaises(ValueError):
                baseline.validate_case_record(case, self.path)

    def test_inventory_cannot_claim_fresh_validation_or_repair(self):
        for status in ("fresh-validated", "repaired"):
            for evidence in (None, {"commands": ["claimed check"], "outcome": "passed"}):
                with self.subTest(status=status, evidence=evidence):
                    sites = copy.deepcopy(self.sites)
                    sites[0].update(status=status, status_reason="Claimed later outcome")
                    if evidence is not None:
                        sites[0]["validation_evidence"] = evidence
                    with self.assertRaisesRegex(ValueError, "frozen baseline inventory"):
                        baseline.validate_inventory(sites, self.source)

    def test_cases_cannot_claim_fresh_validation_or_repair(self):
        for status in ("fresh-validated", "repaired"):
            for evidence in (None, {"commands": ["claimed check"], "outcome": "passed"}):
                with self.subTest(status=status, evidence=evidence):
                    case = copy.deepcopy(self.case)
                    case["status"] = status
                    if evidence is not None:
                        case["validation_evidence"] = evidence
                    with self.assertRaisesRegex(ValueError, "frozen baseline case"):
                        baseline.validate_case_record(case, self.path)

    def test_missing_route_metadata_and_noise_rejected(self):
        with self.assertRaises(ValueError):
            baseline.check_rows(self.case, self.rows[:-1])
        for field, value in (("title", "Wrong title"), ("content", "Missing article"), ("content", self.rows[0]["result"]["content"] + "REMOVE_SEED_ADVERTISEMENT")):
            rows = copy.deepcopy(self.rows)
            rows[0]["result"][field] = value
            with self.assertRaises(ValueError):
                baseline.check_rows(self.case, rows)

    def test_placeholder_never_approved(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["result"]["content"] += "placeholder_video_id"
        with self.assertRaises(ValueError):
            baseline.check_rows(self.case, rows)

    def test_wrong_case_attribution_rejected(self):
        for site in ("BBCExtractor", "TheGuardianExtractor"):
            case = copy.deepcopy(self.case)
            case["site"] = site
            with self.subTest(site=site), self.assertRaises(ValueError):
                baseline.validate_case_record(case, self.path)
        guardian = json.loads((baseline.ROOT / "fixtures/baseline/guardian/case.json").read_text())
        case = copy.deepcopy(self.case)
        for key in ("source_fixture", "source_fixture_sha256"):
            case["provenance"][key] = guardian["provenance"][key]
        with self.assertRaises(ValueError):
            baseline.validate_case_record(case, self.path)
        case = copy.deepcopy(self.case)
        case["provenance"]["source_url"] = "https://www.theguardian.com/"
        with self.assertRaises(ValueError):
            baseline.validate_case_record(case, self.path)

    def test_alias_and_www_case_preflight_without_initial_golden(self):
        with tempfile.TemporaryDirectory(dir=baseline.ROOT / "fixtures/baseline") as directory:
            path = Path(directory) / "case.json"
            for site_id, hosts in (("NPRExtractor", ("www.npr.org", "npr.org")),
                                   ("BuzzFeedExtractor", ("www.buzzfeednews.com", "buzzfeednews.com"))):
                site = json.loads((baseline.ROOT / f"inventory/sites/{site_id}.json").read_text())
                for host in hosts:
                    case = copy.deepcopy(self.case)
                    case.update(site=site_id, input=host + ".html")
                    case["provenance"].update(source_url="https://" + host,
                        source_fixture=site["fixtures"][0]["path"],
                        source_fixture_sha256=site["fixtures"][0]["sha256"])
                    shutil.copyfile(self.path.parent / self.case["input"], path.parent / case["input"])
                    baseline.validate_case_record(case, path, require_golden=False)
                    with self.assertRaises(ValueError):
                        baseline.validate_case_record(case, path)

    def test_record_creates_missing_goldens_and_evaluate_never_writes(self):
        with tempfile.TemporaryDirectory(dir=baseline.WORK) as directory:
            root = Path(directory)
            shutil.copytree(baseline.ROOT / "inventory", root / "inventory")
            shutil.copytree(baseline.ROOT / "fixtures/baseline", root / "fixtures/baseline")
            outputs = {str(p.parent): p.read_bytes() for p in root.rglob("legacy.jsonl")}
            for p in root.rglob("legacy.jsonl"):
                p.unlink()
            with patch.object(baseline, "ROOT", root), patch.object(baseline, "validate_pinned_inventory"), patch.object(baseline, "prepare_evaluator"), patch.object(baseline, "run"), patch.object(baseline.subprocess, "check_output", side_effect=lambda args: outputs[args[2]]), contextlib.redirect_stdout(io.StringIO()):
                baseline.evaluate(root, record=True)
                before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("legacy.jsonl")}
                baseline.evaluate(root)
                self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
            for directory, output in outputs.items():
                self.assertEqual((Path(directory) / "legacy.jsonl").read_bytes(), output)

    def test_record_preflights_all_cases_before_execution(self):
        with tempfile.TemporaryDirectory(dir=baseline.WORK) as directory:
            root = Path(directory)
            shutil.copytree(baseline.ROOT / "inventory", root / "inventory")
            shutil.copytree(baseline.ROOT / "fixtures/baseline", root / "fixtures/baseline")
            paths = sorted((root / "fixtures/baseline").glob("*/case.json"))
            sentinel = root / "sentinel"
            sentinel.write_text("untouched")
            original = {p: p.read_bytes() for p in root.rglob("legacy.jsonl")}
            last = json.loads(paths[-1].read_text())
            for target in (str(sentinel), "../../../sentinel", "escape.jsonl", "directory", "hardlink.jsonl", last["input"], "case.json"):
                if target == "escape.jsonl":
                    (paths[-1].parent / target).symlink_to(sentinel)
                elif target == "directory":
                    (paths[-1].parent / target).mkdir()
                elif target == "hardlink.jsonl":
                    (paths[-1].parent / target).hardlink_to(sentinel)
                last["legacy"] = target
                paths[-1].write_text(json.dumps(last))
                with patch.object(baseline, "ROOT", root), patch.object(baseline, "verify_snapshot") as verify, patch.object(baseline, "prepare_evaluator") as prepare, patch.object(baseline, "run") as run, patch.object(baseline.subprocess, "check_output", return_value=b""):
                    with self.assertRaises(ValueError):
                        baseline.evaluate(root, record=True)
                    verify.assert_not_called()
                    prepare.assert_not_called()
                    run.assert_not_called()
                self.assertEqual(sentinel.read_text(), "untouched")
                self.assertEqual(original, {p: p.read_bytes() for p in original})

    def test_record_rejects_real_case_aliases_before_execution(self):
        with tempfile.TemporaryDirectory(dir=baseline.WORK) as directory:
            root = Path(directory)
            shutil.copytree(baseline.ROOT / "inventory", root / "inventory")
            shutil.copytree(baseline.ROOT / "fixtures/baseline", root / "fixtures/baseline")
            path = root / "fixtures/baseline/npr/case.json"
            case = json.loads(path.read_text())
            if not (path.parent / "CASE.JSON").exists():
                self.skipTest("filesystem is case-sensitive; portable identity test covers the guard")
            sentinel = root / "sentinel"
            sentinel.write_text("untouched")
            for name in ("CASE.JSON", case["input"].upper()):
                with self.subTest(name=name):
                    target = path.parent / name
                    protected = path if name == "CASE.JSON" else path.parent / case["input"]
                    self.assertTrue(target.samefile(protected))
                    case["legacy"] = name
                    path.write_text(json.dumps(case))
                    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
                    with patch.object(baseline, "ROOT", root), patch.object(baseline, "validate_pinned_inventory") as inventory, patch.object(baseline, "prepare_evaluator") as prepare, patch.object(baseline, "run") as run, patch.object(baseline.subprocess, "check_output") as output, patch.object(Path, "write_bytes") as write:
                        with self.assertRaisesRegex(ValueError, "overlaps"):
                            baseline.evaluate(root, record=True)
                        for operation in (inventory, prepare, run, output, write):
                            operation.assert_not_called()
                    self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_record_rechecks_destination_identity_before_write(self):
        with tempfile.TemporaryDirectory(dir=baseline.WORK) as directory:
            root = Path(directory)
            shutil.copytree(baseline.ROOT / "inventory", root / "inventory")
            path = root / "fixtures/baseline/npr/case.json"
            shutil.copytree(self.path.parent, path.parent)
            case = json.loads(path.read_text())
            legacy = path.parent / case["legacy"]
            output = legacy.read_bytes()
            original_samefile = Path.samefile
            for protected in (path, path.parent / case["input"]):
                with self.subTest(protected=protected.name):
                    finished = False

                    def observations(args):
                        nonlocal finished
                        finished = True
                        return output

                    def identity(left, right):
                        if finished and left == legacy and right == protected:
                            return True
                        return original_samefile(left, right)

                    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in path.parent.iterdir()}
                    with patch.object(baseline, "ROOT", root), patch.object(baseline, "validate_pinned_inventory"), patch.object(baseline, "prepare_evaluator"), patch.object(baseline, "run"), patch.object(baseline.subprocess, "check_output", side_effect=observations), patch.object(Path, "samefile", autospec=True, side_effect=identity), patch.object(Path, "write_bytes") as write:
                        with self.assertRaisesRegex(ValueError, "overlaps"):
                            baseline.evaluate(root, record=True)
                        self.assertTrue(finished)
                        write.assert_not_called()
                    self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_validate_rejects_inventory_corruption(self):
        with tempfile.TemporaryDirectory(dir=baseline.WORK) as directory:
            root = Path(directory)
            shutil.copytree(baseline.ROOT / "inventory", root / "inventory")
            shutil.copytree(baseline.ROOT / "fixtures", root / "fixtures")
            mutations = [
                ("domains.json", lambda x: {}),
                ("domains.json", lambda x: dict(x, resolved_domains=dict(x["resolved_domains"], **{"www.npr.org": "www.bbc.com"}))),
                ("dormant.json", lambda x: {}),
                ("settings.json", lambda x: {}),
                ("fixtures.json", lambda x: dict(x, files=x["files"][:-1])),
                ("fixtures.json", lambda x: dict(x, files=[dict(x["files"][0], sha256="0" * 64)] + x["files"][1:])),
                ("source.json", lambda x: dict(x, registry_sha256="0" * 64)),
                ("sites/NPRExtractor.json", lambda x: dict(x, source=dict(x["source"], sha256="0" * 64))),
                ("sites/NPRExtractor.json", lambda x: dict(x, configuration=dict(x["configuration"], Domain="wrong.example"))),
                ("sites/NPRExtractor.json", lambda x: dict(x, configuration=dict(x["configuration"], SupportedDomains=["foreign.example"]))),
                ("sites/NPRExtractor.json", lambda x: dict(x, fixtures=[])),
            ]
            for name, mutate in mutations:
                path = root / "inventory" / name
                original = path.read_bytes()
                path.write_text(json.dumps(mutate(json.loads(original))))
                with self.subTest(name=name), patch.object(baseline, "ROOT", root):
                    with self.assertRaises(ValueError):
                        baseline.validate()
                path.write_bytes(original)
            for name in ("domains.json", "sites/NPRExtractor.json"):
                path = root / "inventory" / name
                original = path.read_bytes()
                path.unlink()
                with patch.object(baseline, "ROOT", root), self.assertRaises(ValueError):
                    baseline.validate()
                path.write_bytes(original)
            extra = root / "inventory/unexpected.json"
            extra.write_text("{}")
            with patch.object(baseline, "ROOT", root), self.assertRaises(ValueError):
                baseline.validate()
            extra.unlink()
            paths = [root / f"fixtures/baseline/{name}/case.json" for name in ("npr", "guardian")]
            cases = [json.loads(p.read_text()) for p in paths]
            cases[0]["site"], cases[1]["site"] = cases[1]["site"], cases[0]["site"]
            for path, case in zip(paths, cases):
                path.write_text(json.dumps(case))
            with patch.object(baseline, "ROOT", root), self.assertRaisesRegex(ValueError, "site identity"):
                baseline.validate()

    def test_known_media_loss_is_explicit_not_a_golden_assertion(self):
        path = baseline.ROOT / "fixtures/baseline/deadspin/case.json"
        case = json.loads(path.read_text())
        rows = [json.loads(line) for line in (path.parent / "legacy.jsonl").read_text().splitlines()]
        baseline.check_rows(case, rows)
        del case["known_gaps"]
        with self.assertRaises(ValueError):
            baseline.check_rows(case, rows)

    def test_candidate_comparison_identity_routes_and_differences(self):
        rows = []
        for path in sorted((baseline.ROOT / "fixtures/baseline").glob("*/legacy.jsonl")):
            rows.extend(json.loads(line) for line in path.read_text().splitlines())
        envelope = {"engine_revision": "1" * 40, "definition_identity": {"kind": "snapshot", "sha256": "2" * 64}, "observations": rows}
        with contextlib.redirect_stdout(io.StringIO()):
            baseline.compare(Mock(read_text=lambda: json.dumps(envelope)))
            for change in ("identity", "missing", "duplicate", "output"):
                bad = copy.deepcopy(envelope)
                if change == "identity":
                    bad["engine_revision"] = "master"
                elif change == "missing":
                    bad["observations"].pop()
                elif change == "duplicate":
                    bad["observations"].append(bad["observations"][0])
                else:
                    bad["observations"][0]["result"]["title"] = "Unexpected change"
                with self.assertRaises(ValueError):
                    baseline.compare(Mock(read_text=lambda: json.dumps(bad)))


if __name__ == "__main__":
    unittest.main()
