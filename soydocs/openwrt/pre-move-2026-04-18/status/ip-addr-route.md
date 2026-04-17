Live capture from `ip -4 addr show` and `ip -4 route show`, sanitized.

lo
- `127.0.0.1/8`

eth0.10
- address: `<redacted-public-ip>/23`

br-lan
- address: `192.168.1.1/24`

tailscale0
- address: `<redacted-tailscale-ip>/32`

routes
- default via `<redacted-upstream-gateway>` dev `eth0.10`
- connected upstream subnet on `eth0.10`
- `192.168.1.0/24` via `br-lan`
