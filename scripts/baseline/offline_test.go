package hermes

import (
	"context"
	"errors"
	"net/http"
	"testing"
)

type baselineDenyTransport struct{ calls int }

func (d *baselineDenyTransport) RoundTrip(*http.Request) (*http.Response, error) {
	d.calls++
	return nil, errors.New("unexpected fixture HTTP request")
}

func TestBaselineOfflineSecurity(t *testing.T) {
	const body = `<html><head><title>Offline fixture boundary</title></head><body><article><p>This original article tests that supplied HTML never performs an HTTP fetch.</p></article></body></html>`
	transport := &baselineDenyTransport{}
	client := New(WithTransport(transport))
	for _, host := range []string{"www.npr.org", "www.theguardian.com", "deadspin.com", "93.184.216.34"} {
		if _, err := client.ParseHTML(context.Background(), body, "https://"+host+"/baseline"); err != nil {
			t.Fatal(err)
		}
	}
	for _, target := range []string{"https://127.0.0.1/a", "https://10.0.0.1/a", "https://[::1]/a", "https://unplanned.example/a"} {
		_, err := client.ParseHTML(context.Background(), body, target)
		var pe *ParseError
		if !errors.As(err, &pe) || pe.Code != ErrInvalidURL {
			t.Fatalf("expected invalid URL denial for %s; got %v", target, err)
		}
	}
	if transport.calls != 0 {
		t.Fatalf("unexpected HTTP requests: %d", transport.calls)
	}
}
