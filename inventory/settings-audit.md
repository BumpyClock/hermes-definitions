# Legacy setting audit

Source: `BumpyClock/hermes@2cc319bac8ce6d869f64b4268a74ce293cfe336b`.
`settings.json` contains exact configured values/site identities and all lexical
member-use hits in non-test Go files. These are interpreted below, not assumed to
be consumers merely because names match.

| Setting | Configured state | Actual consumer / observable behavior | Migration treatment |
| --- | --- | --- | --- |
| `Format` | Four date fields: OSSNews, phpspot, Publickey1, Weekly ASCII | No `FieldExtractor.Format` read. `tryCustomExtractor` calls `parseDate(customFieldValue(...))` (`extract_all_fields.go:222-229`). `parseDate` has eight fixed Go layouts (467-487); Japanese layouts are not recognized there. The lexical `.Format` hits are time/result presentation, not field settings. Generic fallback has its own date parser. | Preserve in inventory; omit this ineffective legacy hint from equivalent YAML rather than inventing format semantics. Any needed Japanese-date repair requires explicit shared capability and fixtures. |
| `Timezone` | Eight date fields: Bookwalker, CBS Sports, Moongift, OSSNews, phpspot, Publickey1, SI, Weekly ASCII | No member reads anywhere. Fixed layouts use `time.Parse`; timezone-free values parse as UTC, not the configured zone. Explicit offsets in supported input layouts are honored by Go independently of this setting. | Omit dead hint only with this evidence; intended timezone behavior is a separate tested repair. |
| `AllowMultiple` | Present in type; never true in active definitions | No member reads. `customFieldValue` always takes `.First()` (299-305); `firstCustomField` returns first nonempty selector result (308-317). Not a collection operation. | Do not invent multivalue semantics. |
| `Extend` | Pitchfork `score`, Times of India `reporter` | No consumer. Custom extraction constructs a fixed internal result and never loops over extensions; public result has no extension map. | Omit dead fields from equivalent migration; adding outputs would be an API decision. |
| `NextPageURL` | Field exists but no active configuration | No consumer. Internal Result declares `next_page_url`, but extraction does not set it; public Result does not expose it. No active pagination traversal/options were found. | Do not activate pagination or add a public field. |

Run `python3 scripts/baseline/baseline.py audit` for an isolated differential probe.
It parses the same synthetic document with and without `AllowMultiple=true`,
an invalid `Format`, `Timezone=Asia/Tokyo`, `Extend` and `NextPageURL` configured.
All result fields remain identical; only the first author is returned, the
timezone-free date is UTC, and the next page remains empty. A Japanese date fails
the custom fixed-layout parser. This probe does not change production definitions.

Other inventory fields must not be assumed live merely because they are declared.
For example, custom `Dek` and `Excerpt` have no reads in `tryCustomExtractor`;
generic extraction/result-derived excerpts are separate behavior. Selectors,
clean rules, transforms and `DisableDefaultCleaner` do have runtime consumers.

## Known non-oracles

- `www_youtube_com.go:69-103` constructs `placeholder_video_id` and, in one
  transform, `"Video description"`. These are fabricated, not successful media
  extraction. No YouTube placeholder is a seed golden; validators reject that ID.
  Issue #45 owns honest media extraction.
- `wikipedia_org.go:63-73`: for a selected `.infobox img`, its `.infobox` ancestor
  already contains that image, so `parent.Find("img").Length() == 0` is false.
  The intended prepend is ineffective. The getter also installs an empty author
  selector list, not a literal "Wikipedia Contributors" value.
- The Deadspin seed's lazy iframe gets a derived YouTube URL, but the final
  sanitizer does not allow iframes (`internal/utils/security/sanitizer.go:20-22`).
  The public result loses that media. `case.json` records the desired URL plus
  a missing-HTML gap assigned to #43. Its legacy JSONL is observational evidence,
  not approval of media loss. No sanitizer was weakened here.

These are repair inventory entries, not work on the later migration tickets.
