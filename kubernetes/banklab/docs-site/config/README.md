# Documentation runtime configuration

This folder is mounted into the in-cluster documentation pod.

- [`build.sh`](build.sh) detects a new Git revision, builds it with strict
  MkDocs validation, and atomically publishes the successful result.
- [`nginx.conf`](nginx.conf) serves the published site and the health endpoint.

The temporary build directory prevents a partial site from replacing the last
working revision.
