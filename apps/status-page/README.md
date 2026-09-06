# Status page commands

`make status-page-check` validates the existing status configuration. `make status-page` runs the full deployment check and configures the page through the maintained script. `make status-page-fallback` validates and applies its existing fallback mode.

This folder owns commands only. It does not change the page, endpoints, credentials, or application ownership. Unsupported operations report `unknown` with a cause.
