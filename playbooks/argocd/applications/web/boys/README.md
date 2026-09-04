# Boys Argo CD application

[`boys-project.yaml`](boys-project.yaml) limits the application to the
`kpoxo6op/soyspray` repository, the `boys` namespace, and the required resource
kinds. The AppProject does not allow Secret resources.

[`boys-application.yaml`](boys-application.yaml) reconciles the
[boys package](../../../../../kubernetes/boys/README.md). The Ansible role
creates the shared PIN, session key, and dedicated tunnel token before it
applies this Application. Its Kustomize patch puts the runtime Secret resource
version in the web pod template, so a changed PIN or session key starts a new
pod.
