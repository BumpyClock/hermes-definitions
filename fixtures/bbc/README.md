# Synthetic BBC pilot

These cases promote the inline synthetic seeds identified in `cases.json` from
Hermes commit `2cc319bac8ce6d869f64b4268a74ce293cfe336b`. They are not captured BBC
pages and do not establish current live-site compatibility. The nested case adds
the first seed's synthetic byline; both add a synthetic timestamp and image URL
to exercise metadata. No article network fetch is needed.

The assertions cover title, author, date, image, opening/final paragraphs,
recommendation boundaries, share-control exclusion and nonduplication.
Hermes owns the Go runner and its independent synthetic regression tests.
Run the optional canonical cases from the Hermes checkout:

```sh
HERMES_DEFINITIONS_PILOT=../hermes-definitions go test . -run TestCanonicalDefinitionsBBC -count=1
```

Fresh public sampling belongs to the later migration cohort.
