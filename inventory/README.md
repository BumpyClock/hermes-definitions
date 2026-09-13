# Inventory reconciliation

All records use engine revision `2cc319bac8ce6d869f64b4268a74ce293cfe336b`.
Runtime registry evaluation verifies the previously reviewed counts: **125 active,
33 function-bearing**. There is no membership drift at this pin.

Inventory and seed case statuses must remain `current-layout-unverified`.
The validator rejects `fresh-validated` and `repaired`, with or without claimed
validation evidence. These records freeze baseline observations; subsequent
captures and repair outcomes belong in separate cohort-owned evidence artifacts.

Reviewed human names map to these less-obvious registry identities:

| Reviewed name | Registry ID |
| --- | --- |
| Gizmodo Japan | `WwwGizmodoJpExtractor` |
| Ars Technica | `ArstechnicaComExtractor` |
| CNET | `WwwCnetComExtractor` |
| The Verge | `WwwThevergeComExtractor` |
| Fortinet | `WwwFortinetComExtractor` |
| Sports Illustrated | `SIExtractor` |
| Hamburger Abendblatt | `AbendblattDeExtractor` |
| MyNavi News | `NewsMynaviJpExtractor` |
| The Motley Fool | `FoolExtractor` |

The complete membership is in per-site `cohort` properties. `source.json` freezes
the active identity set independently of file enumeration, while validation
rejects omissions, duplicate records and replacements with unknown IDs.
Validation verifies the isolated source against the local pinned Git object and
re-executes the inventory harness offline, comparing all inventory JSON records
with the shared generator output. This checks configuration, source bytes and
locations, resolved-domain ownership, dormant/settings facts, fixture mappings
and digests, and textual test references; it does not trust a digest's shape.
Only ignored scratch output is written. An existing snapshot and cached Go
dependencies/toolchain are prerequisites. Missing or unexpected records fail.
The reviewed 12/14/7 lists are explicit in `scripts/baseline/baseline.py`.
Four 23-site selector/string cohorts are deterministic and balance tag-renaming
sites before filling remaining positions. This describes the initial allocation;
validation accepts exhaustive allocations within the approved 24-site bound.

`dormant.json` records all compiled definition literal locations and unregistered
getters. There are 125 compiled literals and 125 registered getters: no dormant Go
implementation was found. The commented `Refinery29Extractor` registry reference
has **no getter or Go definition at the pin**. Its existing HTML fixture does not
make it an active extractor. It remains separately recorded and is not activated.

`domains.json` records the registry's resolved lowercase domain map. Declared
aliases remain in each site record; the parser's add/remove-`www.` fallback is
described separately rather than fabricated as a declared alias. This baseline
does not replace domain resolution with filename matching.

`fixtures.json` inventories every file under the pinned `internal/fixtures/`,
with its size and SHA-256. Site records associate fixture filenames by canonical
domain/declared aliases and the parser's `www.` fallback, including `--variant`
files. Textual test references capture source paths, lines and matched text;
neither a fixture's presence nor a textual reference proves its assertions pass.
Unmatched fixture files are retained in the global immutable fixture inventory,
not silently assigned to a site or promoted into new definitions.

Source paths and line numbers refer to the pin, not the evolving engine checkout.
The inventory generator is a test installed only into the pinned scratch copy;
it executes the actual registry and serializes configured values, including empty
or ineffective settings. It does not activate commented references.
