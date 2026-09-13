package validation

import (
	"context"
	"fmt"
	"net"
)

// Installed only in the pinned scratch snapshot. IP validation still runs normally.
type baselineResolver struct{}

func (baselineResolver) LookupIPAddr(ctx context.Context, host string) ([]net.IPAddr, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if ip := net.ParseIP(host); ip != nil {
		return []net.IPAddr{{IP: ip}}, nil
	}
	switch host {
	case "www.npr.org", "www.theguardian.com", "deadspin.com":
		return []net.IPAddr{{IP: net.ParseIP("93.184.216.34")}}, nil
	default:
		return nil, fmt.Errorf("offline baseline: hostname not in fixture allowlist: %s", host)
	}
}
