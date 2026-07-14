# Start or stop the lab

The Kong bank lab is off by default. Its code stays in the repository while
its pods use no cluster resources.

## Turn it on

Work on a branch, commit and push your changes, then run:

```sh
make kong-on
make status
make smoke
```

The first command runs the local checks before starting the lab. The other two
commands prove that the Argo applications are healthy and the APIs respond.
During startup, rerun `make status` until it reports `LAB STATE ON`, nine
healthy Applications, and `2/2` gateway replicas.

## Turn it off

From the same clean, pushed branch, run:

```sh
make kong-off
make status
```

This removes the Kong runtime, mock APIs, customer app, traffic generator,
dashboard, and docs site. The Kong CRDs stay installed, but CRDs do not run
pods or use ongoing CPU and memory.

`make status` should report `LAB STATE OFF`, only the `banklab-kong-crds`
Application, and `0` runtime pods.

Running the general `make deploy` command also leaves the lab off. Use
`make kong-on` whenever you explicitly want to practise with it.
