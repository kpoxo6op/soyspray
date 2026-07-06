# SOPS And age

Git must not contain plaintext secrets. Later goals should introduce encrypted
Kubernetes secrets using SOPS and age.

Goal 001 creates only the structure and examples. It does not generate or commit
a real age private key.

## Key Handling

- Generate age keys outside the repo.
- Store the private age key in a password manager or another offline backup.
- Commit only public age recipients once real recipients are chosen.
- Never commit `age.key`, `age.txt`, `.sops-age-key.txt`, private keys, or real
  secret values.

## Future Workflow

Future goals should add encrypted secrets, key backup notes, recovery testing,
and secret rotation tests. The example files here are non-deployable.

