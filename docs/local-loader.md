# Local definitions: initial schema

Only `definitions/` contains loadable site rules. Pass that directory, not this
repository root, to `hermes.LoadDefinitions` or `hermes parse --definitions`.
Fixtures, inventory and schema bookkeeping are not extraction rules.

Load once at application startup, handle the returned error, then supply the
snapshot to `hermes.New(hermes.WithDefinitions(snapshot))`. To activate edited
rules, explicitly load a new snapshot and construct new clients; old clients
continue using their original rules. There is no filesystem watch, acquisition,
remote updater, bundled production definition or automatic activation.

Schema `1` is the initial local subset. The authoritative language and numerical
limits are documented in Hermes `docs/api/definitions.md`, and
`hermes.DefinitionCapabilities()` reports runtime support. This subset implements
exact/www and explicit wildcard host matching, ordered text/attribute metadata,
combined content groups, removal selectors and `default_cleaner` (default true).
It rejects transforms, JSON algorithms, date-format/timezone options and all
unknown settings. Metadata operates on Hermes's normalized document:
`meta[property][content]` becomes `meta[name][value]`.

`fixtures/bbc/cases.json` records synthetic provenance and test expectations.
This pilot is not fresh-site evidence or a production compatibility claim.
