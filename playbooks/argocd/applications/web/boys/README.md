# Boys Argo CD application

[`boys-project.yaml`](boys-project.yaml) limits the application to the
`kpoxo6op/soyspray` repository, the `boys` namespace, and the required resource
kinds. Argo CD cannot create or read the runtime secrets.

[`boys-application.yaml`](boys-application.yaml) reconciles the
[boys package](../../../../../kubernetes/boys/README.md). The Ansible role
creates the shared PIN, session key, and dedicated tunnel token before it
applies this Application.
