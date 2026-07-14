# Kong bank lab role defaults

[`main.yml`](main.yml) keeps the lab disabled unless startup is explicit. It
also lists the eight runtime Argo CD applications and the key-auth credentials
created at runtime.

`kong_bank_lab_target_revision` defaults to `HEAD`. A branch revision can be
supplied for a controlled pre-merge deployment; committed Argo application
manifests must remain on `HEAD`.
