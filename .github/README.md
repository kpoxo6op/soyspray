# GitHub automation

This folder contains repository automation run by GitHub.

- [`workflows/`](workflows/) contains the continuous-integration workflow.

Local and GitHub checks use the same `make check` entry point so failures can
be reproduced without changing the cluster.
