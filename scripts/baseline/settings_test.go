package parser

import (
	"context"
	"net/url"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/BumpyClock/hermes/internal/extractors/custom"
	"github.com/PuerkitoBio/goquery"
)

func TestBaselineDeadSettings(t *testing.T) {
	const target = "https://www.nytimes.com/baseline"
	const body = `<html><body><h1>Baseline settings probe</h1><b class="author">First Writer</b><b class="author">Second Writer</b><time>2025-06-10 12:30:00</time><article><p>Original audit text for testing whether configured settings affect the legacy result.</p></article><span class="score">9</span><a class="next" href="/next">Next</a></body></html>`
	e, ok := custom.GetCustomExtractorByDomain("www.nytimes.com")
	if !ok {
		t.Fatal("missing registered NYTimes")
	}
	saved := *e
	defer func() { *e = saved }()
	*e = custom.CustomExtractor{
		Domain:        "www.nytimes.com",
		Title:         &custom.FieldExtractor{Selectors: []custom.SelectorEntry{{Selector: "h1"}}},
		Author:        &custom.FieldExtractor{Selectors: []custom.SelectorEntry{{Selector: ".author"}}},
		DatePublished: &custom.FieldExtractor{Selectors: []custom.SelectorEntry{{Selector: "time"}}},
		Content:       &custom.ContentExtractor{Selectors: []custom.ContentSelectorGroup{{"article"}}},
	}
	parse := func() *Result {
		doc, err := goquery.NewDocumentFromReader(strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		u, err := url.Parse(target)
		if err != nil {
			t.Fatal(err)
		}
		result, err := New().extractAllFieldsWithContext(context.Background(), doc, target, u, ParserOptions{ContentType: "html", Fallback: false})
		if err != nil {
			t.Fatal(err)
		}
		return result
	}
	before := parse()
	e.Author.AllowMultiple = true
	e.DatePublished.Format = "deliberately-invalid-format"
	e.DatePublished.Timezone = "Asia/Tokyo"
	e.Extend = map[string]*custom.FieldExtractor{"score": {Selectors: []custom.SelectorEntry{{Selector: ".score"}}}}
	e.NextPageURL = &custom.FieldExtractor{Selectors: []custom.SelectorEntry{{Selector: ".next", Attribute: "href"}}}
	after := parse()
	if !reflect.DeepEqual(before, after) {
		t.Fatalf("settings changed output:\nbefore=%+v\nafter=%+v", before, after)
	}
	if after.Author != "First Writer" || after.NextPageURL != "" {
		t.Fatalf("unexpected field values: %+v", after)
	}
	want := time.Date(2025, 6, 10, 12, 30, 0, 0, time.UTC)
	if after.DatePublished == nil || !after.DatePublished.Equal(want) {
		t.Fatalf("date not parsed as UTC: %+v", after.DatePublished)
	}
	if _, err := parseDate("2025年06月10日"); err == nil {
		t.Fatal("unexpected Japanese date support")
	}
}
