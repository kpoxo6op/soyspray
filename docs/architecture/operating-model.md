# Operating Model

The lab simulates a bank platform team and its consumers. These personas are
synthetic, but their responsibilities should be realistic.

## Platform Admin

Owns platform direction, global standards, emergency controls, and final
approval of sensitive shared changes.

Must not bypass Git and make unreviewed Kong Admin API changes.

## Platform Operator

Owns day-to-day platform health, deployments, rollback, incident response,
observability, and evidence reports.

Must not approve security exceptions alone.

## API Team Maintainer

Owns an API product, OpenAPI spec, route request, consumer onboarding request,
tests, docs, SLO declaration, and rollback notes.

Must not directly mutate shared gateway configuration outside the Git workflow.

## Security Reviewer

Owns policy review, forbidden plugin rules, authentication expectations, data
classification checks, and security exceptions.

Must not become the default owner for API business behaviour.

## Read-Only Auditor

Reviews pull requests, CI logs, GitOps history, generated evidence, runbooks,
and incident reports.

Must not have write access to production-like platform configuration.

## Synthetic External Partner

Represents a partner client consuming external or partner APIs with explicit
authentication, authorization, rate limits, and support paths.

Must not access internal APIs or platform tools.

## Synthetic Internal Client Owner

Represents internal applications such as mobile banking, internet banking, CRM,
fraud, and payments systems.

Must not share credentials across clients or bypass onboarding.

