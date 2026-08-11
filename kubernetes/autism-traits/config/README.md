# Nginx configuration

[`nginx.conf`](nginx.conf) serves the static Vite bundle from `/site`.

The Content Security Policy permits local files only. The container does not
need network egress.
