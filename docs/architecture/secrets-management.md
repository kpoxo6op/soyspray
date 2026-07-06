# Secrets Management

The bank lab must not commit plaintext secrets, kubeconfigs, private keys, API
tokens, or generated credentials.

Goal 001 prepares a SOPS/age structure only. It does not create a real age
private key and does not commit real encrypted production-like secrets.

## age Keys

Generate age keys outside the repo. Store private keys in a password manager or
offline backup. Commit only public recipients when real recipients are chosen.

## Placeholders

Values such as `CHANGE_ME_WITH_NON_REPO_SECRET`,
`REPLACE_WITH_AGE_PUBLIC_RECIPIENT`, and
`REPLACE_WITH_SOPS_ENCRYPTED_VALUE` are intentionally non-deployable.

## Later Rotation

Goal 008 is expected to implement API key, JWT key, certificate, and secret
rotation tests.

