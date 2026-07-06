# GitOps

This directory contains staged Argo CD structures for the Kong OSS bank-lab
prerequisite layer.

Goal 001 defines the app-of-apps and project boundary shape but does not require
Argo CD to be installed and does not apply anything to the cluster. The
manifests use `REPLACE_WITH_REPO_URL` until the actual Git remote is confirmed.

Git remains the source of truth. Argo CD is expected to reconcile reviewed Git
state; it must not be used to bypass pull-request review.

Rollback should use Git revert followed by an explicit Argo CD sync when the
user chooses to operate the cluster.

