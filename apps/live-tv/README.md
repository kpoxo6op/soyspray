# Live TV commands

Use `make check APP=live-tv` to check the workload and input contracts. Use
`make -f apps/live-tv/Makefile bootstrap` only to create or verify the private
Dispatcharr and Jellyfin inputs. Merge the pull request to deploy through Argo
from `main`.

Retirement is a separate deliberate operation. Bootstrap does not stop or
delete workloads. See [the input role](../../apps/live-tv/bootstrap).
