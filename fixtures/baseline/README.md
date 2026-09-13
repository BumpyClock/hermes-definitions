# Per-site baseline evidence

Each seed directory owns its `case.json`, input HTML and `legacy.jsonl`. Do not
append outcomes to another cohort's file. Aggregate by sorted paths using
`baseline.py validate`; frozen inventory and future migration outcomes are
separate records.

## Record contract

- `id`, `site`: stable case identity and exact frozen registry identity.
- `engine_revision`: full commit, never a branch name.
- `definition_identity`: baseline is `{kind: legacy-compiled, revision: <pin>}`.
  Later comparison records must independently identify their engine commit and
  loaded definitions (source, snapshot/bundle digest, and version when released).
  Do not relabel a new engine observation as this legacy identity.
- `input`, `input_sha256`, `legacy`: local basenames and exact input integrity.
  All cases are preflighted before evaluation builds or writes. Paths must be
  confined regular files without symlinks/hard links; legacy must not overlap the
  input or manifest. Only `record` permits a missing initial legacy file.
- `provenance`: `kind`, creation/capture date, source URL, source fixture path and
  digest, retention basis and notes. Synthetic creation date is not a capture date.
  Fresh captures should additionally name the actual article URL, capture time,
  access outcome and retention basis; failed access is not a parser failure.
- `status`: must remain `current-layout-unverified` in these frozen baseline
  cases, just as in the inventory. `fresh-validated` and `repaired` are rejected
  even if a record includes `validation_evidence`. Later cohort outcomes belong
  in separate evidence artifacts identifying their captures, checks and source
  identities; this validator does not implement that future outcome system.
- `expected.metadata`: exact custom-route field values.
- `expected.content_contains`: substantive phrases required on custom **and**
  generic routes, across Parse/ParseHTML and all three output formats.
- `expected.content_excludes`: site-specific noise absent on custom routes.
  Generic routes do not inherit site clean selectors; full observed results still
  compare exactly and expose any retained noise.
- `expected.html_contains`: custom HTML structure or media references.
- `known_gaps`: explicit `kind`, desired `assertion`, reason and repair owner.
  Currently only missing HTML is supported. A known gap does not turn desired
  behavior into a negative expectation: it flags a failure requiring review and
  fails if it changes unexpectedly. Never add gaps merely to bless placeholders.

The validator checks required provenance, status, active site identity, source
fixture identity, input digest, route completeness, metadata, substantive text,
noise and explicit structural gaps. Unit tests prove that missing/duplicate sites,
incorrect cohorts, corrupt evidence, wrong output and fabricated media fail.
The input filename's hostname and provenance URL must resolve to the declared
site through frozen resolved-domain ownership (exact, then add/remove `www.`).
The provenance fixture must be in that site's frozen fixture mapping, not merely
in the global manifest. Evaluation also verifies the complete pinned inventory
before running observations. Ordinary evaluation never writes goldens.
Later cohorts may extend their own cases; this small seed is not full coverage.

## Selected evidence

| Case | Representative behavior | Current-layout status |
| --- | --- | --- |
| NPR | Selector metadata, nested string tag renames to figure/figcaption, image/caption/prose preservation, ad/button exclusion | Unverified; synthetic layout |
| Guardian | Metadata/ISO date, substantive Unicode prose, related-content cleanup | Unverified; synthetic layout |
| Deadspin | Function-bearing lazy iframe case, surrounding prose and noise cleanup; **known iframe loss** after sanitization | Unverified; synthetic layout, repair needed |

Source fixture hashes identify existing evidence but do not assert that an old
page remains representative or licensed for republication. Original synthetic
prose avoids copying publisher content. All media URLs are inert strings: no image
or video is downloaded, and synthetic media IDs are not claimed to identify real
media. These inputs are canonical site conformance seeds, not a new engine API.
