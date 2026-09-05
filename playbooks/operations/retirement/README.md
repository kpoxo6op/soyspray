# Banking lab retirement

This operation removes the remaining resources of the parked banking lab.
Merge the change that removes the lab from general deployment registration
first. The operation checks that registration and requires the runtime
Applications to be absent. It stops if another Application uses the lab
project or a named lab namespace contains a claim.

Push the branch and run `make go`. Check the retirement, then omit `--check`
to apply:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/retirement/bank-lab.yml --check
```

The operation verifies the CRD Application's complete resource scope. It
checks all Kong resource types before removing the Application, removes its
Argo deletion finalizer to prevent cascading deletion, and checks every Kong
type again before deleting the twelve explicitly named definitions. It uses
UID preconditions for deletions.

Only named namespaces with both synthetic-data and lab-environment labels
can be removed. The shared monitoring namespace is excluded. All
`gateway.networking.k8s.io` definitions stay in place, and their UIDs are
checked after retirement. The external autism status-page integration is
outside this operation.

Do not use `make kong-off` for retirement. That older parking path is not this
operation. After application, project, namespace, and Kong CRD absence is
verified, remove the obsolete lab source and deployment targets in a separate
PR. Retain the verification results outside Git.

There is no automatic recreation rollback. Reintroducing the lab requires a
deliberate new deployment with reviewed definitions. A retry of this operation
keeps unrelated resources and skips resources that are already absent.
