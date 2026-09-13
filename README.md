# Hermes definitions

Canonical site rules will live in `definitions/`. Inventory and conformance inputs
live outside that directory so a definitions loader does not see bookkeeping as
site configuration. This bootstrap implements engine issue
[#31](https://github.com/BumpyClock/hermes/issues/31); it is not a migrated bundle
or a release.

## Frozen baseline

Engine: `BumpyClock/hermes` at
`2cc319bac8ce6d869f64b4268a74ce293cfe336b`.
There are **125 active entries, 33 function-bearing definitions, and 92
selector/string-only definitions**. `inventory/sites/*.json` records each
registry identity, canonical domain, declared aliases, complete runtime
configuration, source locations/digests, fixture identities, textual test
references and cohort. Arrays retain selector order; JSON object keys are sorted.
Function bodies remain identified by symbol, source location and pinned source,
not translated into invented operations.

The four selector/string cohorts contain 23 sites each. Sites with string
transforms are dealt first, then remaining sites, sorted by registry ID, to the
smallest cohort (numeric tie break). The 12/14/7 reviewed function cohorts follow
issues [43](https://github.com/BumpyClock/hermes/issues/43),
[44](https://github.com/BumpyClock/hermes/issues/44) and
[45](https://github.com/BumpyClock/hermes/issues/45).
See [inventory reconciliation](inventory/README.md).

## Offline checks

Requirements: Python 3.12+ (`tarfile` data filter), the Go version in the pinned
engine's `go.mod` (1.27.1), the local engine Git object, and already-cached Go
dependencies. No packages are installed or downloaded by these commands.
Run from this repository, creating the isolated snapshot once before validation
or tests:

```sh
python3 scripts/baseline/baseline.py snapshot --engine ../hermes
python3 scripts/baseline/baseline.py validate --engine ../hermes
python3 -m unittest discover -s scripts/baseline -p 'test_*.py' -v
python3 scripts/baseline/baseline.py audit --engine ../hermes
python3 scripts/baseline/baseline.py evaluate --engine ../hermes
```

`snapshot` creates an isolated ignored `.baseline-work/source/` using `git
archive` of the pin, never the engine working tree. It refuses an existing
snapshot. For subsequent checks, skip `snapshot`. To rebuild, remove only that
generated directory deliberately, then rerun `snapshot`. Go scratch files are
also under `.baseline-work/`; module networking and toolchain downloads are off.
Before source-dependent checks, every archived file is verified against the
pinned Git object, allowing only the documented harness instrumentation.

`inventory` is an explicit regeneration operation, not an ordinary validation
step. Run `python3 scripts/baseline/baseline.py inventory --engine ../hermes`
only when regenerating baseline-owned inventory files; do not run it over
cohort-owned outcome edits. `validate` leaves baseline records untouched and derives the cohort count
view deterministically, rejecting missing/duplicate/unknown identities, bad
cohorts, malformed evidence, bad fixture digests and fresh-validation/repair claims
on frozen inventory or seed records. Their status must remain
`current-layout-unverified`, even when claimed validation evidence is supplied.
Future cohort outcomes belong in separate per-site artifacts, not a shared
rewritten matrix.

Validation requires the existing isolated snapshot, local pinned Git object and
cached Go toolchain/dependencies, just like evaluation. It verifies snapshot bytes
against the Git pin and reruns the inventory harness into ignored scratch storage.
The generator and validator share the same record extraction: every inventory JSON
file, configuration, alias/resolved owner, source digest, dormant/settings fact and
fixture mapping/digest must match the pinned facts. Missing and unexpected records
fail. Cohort membership remains exhaustive and bounded at 24, not fixed at 23.

`evaluate` uses the engine's existing **public ParseHTML and Parse**
`scripts/contract-snapshot` seam. It compares all public result fields and helpers
against per-case legacy JSONL, and checks independent metadata, substantive prose,
HTML structure and site-specific noise assertions. Each of three cases runs both
entry points, HTML/Markdown/text, and a custom-site/generic-IP route: 36 observations.
Generic routes assert substantive prose, but do not pretend to know site-specific
clean selectors. A missing Deadspin iframe is an explicit **known repair gap**,
not approved golden behavior. A repair must update that evidence through review.

`record` is an explicit maintainer action to replace legacy observations after
assertions pass; ordinary evaluation never updates expected results. To compare a
future local-loader engine, export the same observation IDs/result envelope from
its public ParseHTML/snapshot seam with explicit engine and loaded-definition
digest identities, then review differences against these records. This bootstrap
does not require issue #32, released artifacts or a second public extraction API.

Both commands preflight **all** cases before source instrumentation, builds or
golden writes. Record permits missing initial goldens, but input and destination
paths must be confined regular files (or a missing destination), with no symlinks,
hard links, traversal or overlap with the input/manifest. Case input hostnames and
provenance URLs must resolve to the declared frozen site, including aliases and
the documented `www.` fallback; the provenance fixture must belong to that site.

The runnable comparison accepts a local JSON envelope with `engine_revision`
(full commit), `definition_identity: {"kind": "snapshot", "sha256": "<digest>"}`
and `observations` (the 36 snapshot rows):

```sh
python3 scripts/baseline/baseline.py compare --candidate candidate-observations.json
```

It rejects missing/duplicate routes or identities, reports changed observation IDs
and assertion failures, and exits nonzero for differences needing review. It never
fetches definitions, executes a candidate, updates goldens or assumes a repaired
legacy gap is automatically approved.

## Network boundary

Legacy URL validation itself resolves DNS even for supplied HTML. In the
**isolated snapshot only**, the harness replaces resolver construction with an
allowlisted in-memory resolver. It maps the three fixture hosts to a public test
address, returns IP literals unchanged, and rejects all other hostnames. All
normal private-network/localhost validation remains in place; private-network
options are not enabled. The existing snapshot's injected HTTP transport serves
the fixture for Parse; default HTTP requests fail. Embedded URLs are never fetched.
The audit asserts public invalid-URL error codes for private IPs and unknown hosts,
and zero HTTP calls on ParseHTML. No production engine file is modified.

## Evidence and retention

See [the evidence contract](fixtures/baseline/README.md) and
[settings audit](inventory/settings-audit.md).
The three small inputs use original synthetic text and selector-level layouts
informed by existing fixtures. No publisher prose, images, scripts, or complete
captured page is republished. Existing fixture names and SHA-256 values preserve
provenance without asserting rights to redistribute those pages. No repository
license or capture permission policy is invented here.

This is offline baseline evidence, **not fresh-site validation**. All sites
remain `current-layout-unverified`; no live crawl or access attempt was made.
Future cohorts own current samples, selector repairs, media repairs, missing
input/edge cases and final qualification. No performance claim is made.
