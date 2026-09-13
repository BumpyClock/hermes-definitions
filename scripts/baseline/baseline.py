#!/usr/bin/env python3
"""Frozen source inventory and offline conformance tooling (standard library only)."""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2cc319bac8ce6d869f64b4268a74ce293cfe336b"
WORK = ROOT / ".baseline-work"
SOURCE = WORK / "source"
ENGINE = ROOT.parent / "hermes"
TOOLS = Path(__file__).resolve().parent
COHORTS = {
    "attribute-text-cleanup-43": [
        "NYTimesExtractor", "NewsMynaviJpExtractor", "ElecomCoJpExtractor",
        "WiredJpExtractor", "LifehackerJpExtractor", "WwwGizmodoJpExtractor",
        "DaringFireballExtractor", "CNNExtractor", "DeadspinExtractor",
        "RedditExtractor", "ArstechnicaComExtractor", "MaTtiasBeExtractor"],
    "dom-noscript-44": [
        "DeadlineExtractor", "LATimesExtractor", "WashingtonPostExtractor",
        "BuzzFeedExtractor", "WwwCnetComExtractor", "FoolExtractor", "NDTVExtractor",
        "TwitterExtractor", "WwwThevergeComExtractor", "SIExtractor", "NYMagExtractor",
        "WwwFortinetComExtractor", "PolygonExtractor", "VoxExtractor"],
    "complex-exception-45": [
        "MediumExtractor", "ApartmentTherapyExtractor",
        "WwwNationalgeographicComExtractor", "NewsNationalgeographicComExtractor",
        "WikipediaExtractor", "YouTubeExtractor", "AbendblattDeExtractor"],
}


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def environment():
    env = os.environ.copy()
    env.update(GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               GOTMPDIR=str(WORK / "go-tmp"), TMPDIR=str(WORK / "go-tmp"))
    (WORK / "go-tmp").mkdir(parents=True, exist_ok=True)
    return env


def snapshot(engine):
    if SOURCE.exists():
        raise ValueError("snapshot already exists; use the existing snapshot or remove only .baseline-work/source explicitly")
    archive = subprocess.check_output(["git", "-C", str(engine), "archive", REVISION])
    SOURCE.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(SOURCE, filter="data")
    (WORK / "revision").write_text(REVISION + "\n")


def inventory():
    for name, record in inventory_records().items():
        write_json(ROOT / "inventory" / name, record)


def inventory_records():
    if (WORK / "revision").read_text().strip() != REVISION:
        raise ValueError("wrong source revision")
    harness = SOURCE / "internal/extractors/custom/baseline_inventory_test.go"
    harness.write_bytes((TOOLS / "inventory_test.go").read_bytes())
    env = environment()
    env["BASELINE_INVENTORY"] = str(WORK / "raw-inventory.json")
    run(["go", "test", "./internal/extractors/custom", "-run", "^TestBaselineInventory$", "-count=1"], cwd=SOURCE, env=env)
    raw = json.loads((WORK / "raw-inventory.json").read_text())
    records = {}
    sites = raw["sites"]
    assigned = {}
    for cohort, names in COHORTS.items():
        for name in names:
            if name not in sites:
                raise ValueError(f"reviewed identity needs reconciliation: {name}")
            if name in assigned:
                raise ValueError(f"duplicate cohort: {name}")
            assigned[name] = cohort
    simple = sorted(set(sites) - set(assigned))
    groups = [[] for _ in range(4)]
    # Deal tag-renames first so both total size and transform counts stay balanced.
    for name in sorted(simple, key=lambda n: (not bool(sites[n]["configuration"].get("Content", {}).get("transforms")), n)):
        group = min(range(4), key=lambda i: (len(groups[i]), i))
        groups[group].append(name)
        assigned[name] = f"selector-string-{group + 1}"
    fixtures = []
    for path in sorted((SOURCE / "internal/fixtures").rglob("*")):
        if path.is_file():
            fixtures.append({"path": str(path.relative_to(SOURCE)), "sha256": digest(path), "bytes": path.stat().st_size})
    tests = [(p, p.read_text().splitlines()) for p in sorted(SOURCE.rglob("*_test.go")) if not p.name.startswith("baseline_")]
    for name, site in sites.items():
        site.update(id=name, cohort=assigned[name], engine_revision=REVISION)
        site["source"]["sha256"] = digest(SOURCE / site["source"]["path"])
        domains = [site["configuration"]["Domain"]] + (site["configuration"]["SupportedDomains"] or [])
        site["fixtures"] = [f for f in fixtures if any(Path(f["path"]).name.split("--")[0].removesuffix(".html").removeprefix("www.") == d.removeprefix("www.") for d in domains)]
        site["fixture_mapping"] = "canonical/alias filename, including parser www fallback; not proof of assertion coverage"
        site["test_references"] = [
            {"path": str(p.relative_to(SOURCE)), "line": line, "text": text.strip()}
            for p, lines in tests for line, text in enumerate(lines, 1)
            if any(term in text for term in domains + [site["getter"], name])
        ]
        site["status"] = "current-layout-unverified"
        site["status_reason"] = "Frozen inventory only; no fresh capture attempted in bounded issue 31."
        records[f"sites/{name}.json"] = site
    active_getters = {s["getter"] for s in sites.values()}
    records["dormant.json"] = {
        "engine_revision": REVISION,
        "unregistered_getters": {n: s for n, s in raw["getters"].items() if n not in active_getters},
        "compiled_definition_literals": sorted(raw["definitions"], key=lambda d: (d["path"], d["line"])),
        "policy": "Not registered at frozen revision; do not activate during migration.",
        "commented_registry_entries": [
            {"id": "Refinery29Extractor", "getter": "GetRefinery29Extractor",
             "path": "internal/extractors/custom/index.go", "line": 78,
             "implementation_present": False,
             "fixture": "internal/fixtures/www.refinery29.com.html",
             "note": "Commented registry reference only; no Go getter or definition at this revision."}
        ],
    }
    records["fixtures.json"] = {"engine_revision": REVISION, "files": fixtures}
    records["domains.json"] = {"engine_revision": REVISION, "resolved_domains": raw["resolved_domains"],
               "fallback": "On exact miss, parser removes or adds www.; registry keys are lowercased."}
    records["source.json"] = {
        "engine_repository": "https://github.com/BumpyClock/hermes",
        "engine_revision": REVISION,
        "registry_path": "internal/extractors/custom/index.go",
        "registry_sha256": digest(SOURCE / "internal/extractors/custom/index.go"),
        "active_count": len(sites),
        "function_bearing_count": sum(s["function_bearing"] for s in sites.values()),
        "active_ids": sorted(sites),
        "reviewed_issues": [31, 43, 44, 45],
    }
    declarations = {key: [] for key in ["Format", "Timezone", "AllowMultiple", "Extend", "NextPageURL"]}
    for name, site in sorted(sites.items()):
        for field, config in site["configuration"].items():
            if isinstance(config, dict):
                for key in ("Format", "Timezone", "AllowMultiple"):
                    # FieldExtractor uses explicit lower-camel JSON tags.
                    json_key = key[0].lower() + key[1:]
                    if config.get(json_key):
                        declarations[key].append({"site": name, "field": field, "value": config[json_key]})
        for key in ("Extend", "NextPageURL"):
            if site["configuration"].get(key):
                declarations[key].append({"site": name, "value": site["configuration"][key]})
    consumers = {key: [] for key in declarations}
    for path in sorted(SOURCE.rglob("*.go")):
        if path.name.endswith("_test.go"):
            continue
        for line, text in enumerate(path.read_text().splitlines(), 1):
            for key in consumers:
                if re.search(r"\." + key + r"\b", text):
                    consumers[key].append({"path": str(path.relative_to(SOURCE)), "line": line, "text": text.strip()})
    records["settings.json"] = {"engine_revision": REVISION, "configured": declarations, "lexical_member_uses": consumers,
               "note": "Format hits are unrelated time.Time/result presentation calls; see settings-audit.md for consumer analysis."}
    return records


def validate_pinned_inventory(engine):
    verify_snapshot(engine)
    expected = inventory_records()
    paths = {str(p.relative_to(ROOT / "inventory")): p for p in (ROOT / "inventory").rglob("*.json")}
    if paths.keys() != expected.keys():
        raise ValueError("missing or unexpected inventory records")
    for name, record in expected.items():
        actual = json.loads(paths[name].read_text())
        # Cohort allocation is separately checked for exhaustive membership and
        # the approved <=24 bound, not locked to the initial 23-site split.
        if name.startswith("sites/"):
            record = dict(record, cohort=actual.get("cohort"), status_reason=actual.get("status_reason"))
        if actual != record:
            raise ValueError(f"pinned inventory mismatch: {name}")


def validate(engine=ENGINE):
    sites = [json.loads(p.read_text()) for p in sorted((ROOT / "inventory/sites").glob("*.json"))]
    source = json.loads((ROOT / "inventory/source.json").read_text())
    aggregate = validate_inventory(sites, source)
    validate_pinned_inventory(engine)
    cases = [validate_case(path) for path in sorted((ROOT / "fixtures/baseline").glob("*/case.json"))]
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("duplicate case identity")
    if not {"NPRExtractor", "TheGuardianExtractor", "DeadspinExtractor"} <= {c["site"] for c in cases}:
        raise ValueError("missing bootstrap seed case")
    print(json.dumps(aggregate, sort_keys=True))
    return sites


def validate_inventory(sites, source):
    ids = [s["id"] for s in sites]
    if len(ids) != 125 or len(set(ids)) != 125:
        raise ValueError("missing or duplicate active inventory identities")
    if sorted(ids) != source["active_ids"]:
        raise ValueError("active source identity mismatch")
    if source["engine_revision"] != REVISION:
        raise ValueError("source pin mismatch")
    if source["active_count"] != 125 or source["function_bearing_count"] != 33:
        raise ValueError("source count mismatch")
    if sum(s["function_bearing"] for s in sites) != 33:
        raise ValueError("function-bearing inventory drift")
    aggregate = {}
    for s in sites:
        if s["engine_revision"] != REVISION or not s["configuration"]["Domain"]:
            raise ValueError(f"invalid identity: {s['id']}")
        if s["status"] != "current-layout-unverified":
            raise ValueError("frozen baseline inventory must remain current-layout-unverified")
        if not s.get("status_reason") or not re.fullmatch(r"[0-9a-f]{64}", s["source"]["sha256"]):
            raise ValueError("missing inventory provenance")
        if not isinstance(s["configuration"]["SupportedDomains"], (list, type(None))):
            raise ValueError("invalid aliases")
        cohort = s["cohort"]
        allowed = set(COHORTS) | {f"selector-string-{i}" for i in range(1, 5)}
        if cohort not in allowed:
            raise ValueError(f"unknown cohort: {cohort}")
        aggregate.setdefault(cohort, []).append(s["id"])
        if s["function_bearing"] != (cohort in COHORTS):
            raise ValueError(f"wrong function ownership: {s['id']}")
    for cohort, expected in COHORTS.items():
        if sorted(aggregate.get(cohort, [])) != sorted(expected):
            raise ValueError(f"reviewed cohort mismatch: {cohort}")
    for i in range(1, 5):
        if not 1 <= len(aggregate.get(f"selector-string-{i}", [])) <= 24:
            raise ValueError("selector cohort bound violated")
    return {c: len(names) for c, names in sorted(aggregate.items())}


def validate_case(path):
    case = json.loads(path.read_text())
    validate_case_record(case, path)
    return case


def case_file(path, name, missing=False):
    if not isinstance(name, str) or not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("case files must be local basenames")
    directory = path.parent
    target = directory / name
    boundary = ROOT.resolve() / "fixtures/baseline"
    if directory.is_symlink() or not directory.resolve().is_relative_to(boundary):
        raise ValueError("case directory escapes baseline")
    if target.is_symlink() or not target.resolve().is_relative_to(directory.resolve()):
        raise ValueError("case file symlink or escape")
    if not target.is_file() and not (missing and not target.exists()):
        raise ValueError("case file must be regular")
    if target.exists() and target.stat().st_nlink != 1:
        raise ValueError("case file must not share a hard-linked inode")
    return target


def registered_owner(host):
    domains = json.loads((ROOT / "inventory/domains.json").read_text())["resolved_domains"]
    host = host.lower()
    fallback = host.removeprefix("www.") if host.startswith("www.") else "www." + host
    return domains.get(host, domains.get(fallback))


def legacy_file(case, path, missing=False):
    target = case_file(path, case["legacy"], missing=missing)
    input_path = case_file(path, case["input"])
    for protected in (input_path, path):
        if target == protected or (
            target.exists() and protected.exists() and target.samefile(protected)
        ):
            raise ValueError("legacy destination overlaps case input or manifest")
    return target


def validate_case_record(case, path, require_golden=True):
    required = {"id", "site", "engine_revision", "definition_identity", "input", "input_sha256", "provenance", "status", "expected", "legacy"}
    if not required <= case.keys():
        raise ValueError(f"missing evidence fields: {path}")
    if case["engine_revision"] != REVISION:
        raise ValueError("case source mismatch")
    active_ids = json.loads((ROOT / "inventory/source.json").read_text())["active_ids"]
    if case["site"] not in active_ids:
        raise ValueError("case site is not active")
    if case["status"] != "current-layout-unverified":
        raise ValueError("frozen baseline case must remain current-layout-unverified")
    if case["definition_identity"] != {"kind": "legacy-compiled", "revision": REVISION}:
        raise ValueError("wrong baseline definition identity")
    for key in ("kind", "created_at", "source_url", "source_fixture", "source_fixture_sha256", "retention_basis", "notes"):
        if key not in case["provenance"] or not case["provenance"][key]:
            raise ValueError(f"missing provenance: {key}")
    datetime.date.fromisoformat(case["provenance"]["created_at"])
    source_url = urlparse(case["provenance"]["source_url"])
    if source_url.scheme not in ("https", "http") or not source_url.hostname:
        raise ValueError("invalid provenance URL")
    input_path = case_file(path, case["input"])
    legacy_path = legacy_file(case, path, missing=not require_golden)
    site = json.loads((ROOT / "inventory/sites" / f"{case['site']}.json").read_text())
    if not case["input"].endswith(".html") or any(
        registered_owner(host) != site["configuration"]["Domain"]
        for host in (case["input"].removesuffix(".html"), source_url.hostname)
    ):
        raise ValueError("case route/provenance site identity mismatch")
    if digest(input_path) != case["input_sha256"]:
        raise ValueError("fixture digest mismatch")
    fixture_manifest = json.loads((ROOT / "inventory/fixtures.json").read_text())["files"]
    if not any(f["path"] == case["provenance"]["source_fixture"] and f["sha256"] == case["provenance"]["source_fixture_sha256"] for f in fixture_manifest):
        raise ValueError("source fixture identity mismatch")
    if not any(f["path"] == case["provenance"]["source_fixture"] and f["sha256"] == case["provenance"]["source_fixture_sha256"] for f in site["fixtures"]):
        raise ValueError("source fixture belongs to another site")
    expected = case["expected"]
    if not expected.get("metadata") or not expected.get("content_contains") or not expected.get("content_excludes"):
        raise ValueError("metadata, positive content and negative content assertions required")
    if require_golden:
        rows = [json.loads(line) for line in legacy_path.read_text().splitlines()]
        check_rows(case, rows)


def check_rows(case, rows):
    host = case["input"].removesuffix(".html")
    expected_ids = {f"{case['input']}/{route}/{fmt}/{method}" for route in (host, "93.184.216.34") for fmt in ("html", "markdown", "text") for method in ("html", "fetch")}
    if len(rows) != 12 or {r["id"] for r in rows} != expected_ids:
        raise ValueError("missing/duplicate snapshot routes")
    for row in rows:
        if row.get("error") or not row.get("result"):
            raise ValueError(f"baseline parse failed: {row}")
        result = row["result"]
        content = result["content"]
        for text in case["expected"]["content_contains"]:
            if text not in content:
                raise ValueError(f"missing article text {text!r}: {row['id']}")
        if "placeholder_video_id" in content:
            raise ValueError("fabricated YouTube placeholder is never golden-correct")
        if f"/{host}/" in row["id"]:
            for text in case["expected"]["content_excludes"]:
                if text in content:
                    raise ValueError(f"unwanted content {text!r}: {row['id']}")
            for field, value in case["expected"]["metadata"].items():
                if result.get(field) != value:
                    raise ValueError(f"metadata mismatch {field}: {row['id']}: {result.get(field)!r}")
            if "/html/" in row["id"]:
                for text in case["expected"].get("html_contains", []):
                    gaps = [g for g in case.get("known_gaps", []) if g.get("kind") == "missing-html" and g.get("assertion") == text and g.get("reason") and g.get("repair_owner")]
                    if gaps and text in content:
                        raise ValueError(f"known gap repaired; review baseline difference: {row['id']}")
                    if text not in content and not gaps:
                        raise ValueError(f"missing HTML structure {text!r}: {row['id']}")


def prepare_evaluator():
    path = SOURCE / "internal/validation/url.go"
    text = path.read_text()
    original = "resolver := &net.Resolver{}"
    replacement = "resolver := baselineResolver{}"
    if original in text:
        path.write_text(text.replace(original, replacement))
    elif replacement not in text:
        raise ValueError("unexpected DNS seam")
    (SOURCE / "internal/validation/baseline_dns.go").write_bytes((ROOT / "scripts/baseline/offline_dns.go").read_bytes())
    path = SOURCE / "scripts/contract-snapshot/main.go"
    text = path.read_text()
    marker = 'func main() {\n'
    guard = '\thttp.DefaultTransport = transport(func(*http.Request) (*http.Response, error) { return nil, fmt.Errorf("offline baseline: unexpected HTTP request") })\n'
    if guard not in text:
        path.write_text(text.replace(marker, marker + guard))


def verify_snapshot(engine):
    archive = subprocess.check_output(["git", "-C", str(engine), "archive", REVISION])
    additions = {
        "internal/extractors/custom/baseline_inventory_test.go": "inventory_test.go",
        "internal/validation/baseline_dns.go": "offline_dns.go",
        "internal/parser/baseline_settings_test.go": "settings_test.go",
        "baseline_offline_test.go": "offline_test.go",
    }
    tracked = set()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            tracked.add(member.name)
            original = tar.extractfile(member).read()
            actual = (SOURCE / member.name).read_bytes()
            permitted = original
            if member.name == "internal/validation/url.go":
                permitted = original.replace(b"resolver := &net.Resolver{}", b"resolver := baselineResolver{}")
            if member.name == "scripts/contract-snapshot/main.go":
                permitted = original.replace(b"func main() {\n", b'func main() {\n\thttp.DefaultTransport = transport(func(*http.Request) (*http.Response, error) { return nil, fmt.Errorf("offline baseline: unexpected HTTP request") })\n')
            if actual not in (original, permitted):
                raise ValueError(f"pinned source changed unexpectedly: {member.name}")
    for path in SOURCE.rglob("*"):
        if not path.is_file():
            continue
        name = str(path.relative_to(SOURCE))
        if name in tracked:
            continue
        if name not in additions or path.read_bytes() != (TOOLS / additions[name]).read_bytes():
            raise ValueError(f"unexpected snapshot file: {name}")


def evaluate(engine, record=False):
    cases = []
    for path in sorted((ROOT / "fixtures/baseline").glob("*/case.json")):
        case = json.loads(path.read_text())
        validate_case_record(case, path, require_golden=not record)
        cases.append((path, case))
    if not cases or len({case["id"] for _, case in cases}) != len(cases):
        raise ValueError("missing or duplicate case identities")
    validate_pinned_inventory(engine)
    prepare_evaluator()
    binary = WORK / "contract-snapshot"
    run(["go", "build", "-o", str(binary), "./scripts/contract-snapshot"], cwd=SOURCE, env=environment())
    for path, case in cases:
        output = subprocess.check_output([str(binary), "-fixtures", str(path.parent), "-match", case["input"]])
        rows = [json.loads(line) for line in output.splitlines()]
        check_rows(case, rows)
        if record:
            legacy_file(case, path, missing=True).write_bytes(output)
        else:
            expected = [json.loads(line) for line in (path.parent / case["legacy"]).read_text().splitlines()]
            if rows != expected:
                raise ValueError(f"legacy output changed: {case['id']}")
        print(f"{case['id']}: 12 offline routes passed")


def audit(engine):
    verify_snapshot(engine)
    prepare_evaluator()
    for target, source in (("internal/parser/baseline_settings_test.go", "settings_test.go"),
                           ("baseline_offline_test.go", "offline_test.go")):
        (SOURCE / target).write_bytes((ROOT / "scripts/baseline" / source).read_bytes())
    run(["go", "test", ".", "./internal/parser", "-run", "^TestBaseline(DeadSettings|OfflineSecurity)$", "-count=1"], cwd=SOURCE, env=environment())


def compare(candidate):
    record = json.loads(candidate.read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", record.get("engine_revision", "")):
        raise ValueError("candidate requires an exact engine revision")
    identity = record.get("definition_identity", {})
    if identity.get("kind") != "snapshot" or not re.fullmatch(r"[0-9a-f]{64}", identity.get("sha256", "")):
        raise ValueError("candidate requires loaded definition snapshot SHA-256")
    rows = record["observations"]
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate candidate observations")
    baseline_rows = {}
    cases = []
    for path in sorted((ROOT / "fixtures/baseline").glob("*/case.json")):
        case = validate_case(path)
        legacy = [json.loads(line) for line in (path.parent / case["legacy"]).read_text().splitlines()]
        baseline_rows.update({r["id"]: r for r in legacy})
        cases.append((case, legacy))
    if by_id.keys() != baseline_rows.keys():
        raise ValueError("candidate route set differs from baseline")
    failures = []
    for case, legacy in cases:
        try:
            check_rows(case, [by_id[r["id"]] for r in legacy])
        except ValueError as error:
            failures.append({"case": case["id"], "assertion": str(error)})
    differences = [key for key in sorted(by_id) if by_id[key] != baseline_rows[key]]
    print(json.dumps({"candidate_engine": record["engine_revision"],
                      "candidate_definitions": identity, "changed_observations": differences,
                      "assertion_review": failures}, indent=2, sort_keys=True))
    if differences or failures:
        raise ValueError("candidate differences require review; no baseline files were updated")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["snapshot", "inventory", "validate", "evaluate", "record", "audit", "compare"])
    parser.add_argument("--engine", type=Path, default=ROOT.parent / "hermes")
    parser.add_argument("--candidate", type=Path, help="local candidate observation envelope for compare")
    args = parser.parse_args()
    if args.command == "snapshot":
        snapshot(args.engine)
    elif args.command == "inventory":
        verify_snapshot(args.engine)
        inventory()
        validate(args.engine)
    elif args.command in ("evaluate", "record"):
        evaluate(args.engine, record=args.command == "record")
    elif args.command == "audit":
        audit(args.engine)
    elif args.command == "compare":
        if args.candidate is None:
            parser.error("compare requires --candidate")
        compare(args.candidate)
    else:
        validate(args.engine)


if __name__ == "__main__":
    main()
