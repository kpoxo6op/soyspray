# Testing Strategy

The lab should prove behaviour through tests and evidence, not through hope.

## Static Validation

Checks repository structure, required files, unsafe filenames, and basic content
expectations. Goal 000 implements this layer.

## Documentation Validation

Builds or validates the MkDocs site so docs are part of the local gate. Goal 000
implements this layer.

## Policy-As-Code Tests

Validates policy fixtures and, in later goals, checks ownership, auth,
rate-limit, exposure, and forbidden-plugin rules. Goal 000 includes placeholder
policy tests only.

## Unit Tests

Checks local scripts and repository contracts without cluster access. Goal 000
includes foundation tests.

## API Contract Tests

Later goals should validate OpenAPI specs and generated API examples.

## Integration Tests

Later goals should verify cluster behaviour after GitOps sync.

## Negative Tests

Every security and routing feature should include failure tests such as missing
API key, invalid JWT, wrong ACL group, forbidden plugin, unknown route, and
rate-limit exceeded.

## Failure-Mode Tests

Later goals should simulate backend outage, Redis outage, expired certificate,
bad route release, GitOps drift, and failed upgrade.

## Performance Baseline Tests

Later goals should measure baseline route performance, plugin overhead, p95 and
p99 latency, CPU, memory, errors, and safe operating limits.

## Evidence Reports

Each goal writes a report under `reports/` with commands run, results, known
limitations, and remaining risks.

