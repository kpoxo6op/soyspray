include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap finance smoke

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/gi/tests
	cd $(ROOT) && $(PYTHON) -m ruff check apps/gi/tests
	cd $(ROOT) && $(PYTHON) -m ruff format --check apps/gi/tests
	cd $(ROOT) && kubectl kustomize apps/gi/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/gi/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app gi

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/gi/bootstrap.yml

# Publish the private data file to the gi-finance Secret.
finance:
	cd $(ROOT) && $(ANSIBLE) apps/gi/finance.yml $(if $(FILE),-e gi_finance_file=$(FILE))

# Read-only checks of the running page: rollout, health, data file present,
# and anonymous requests refused by the sign-in.
smoke:
	kubectl -n gi rollout status deployment/gi --timeout=180s
	kubectl -n gi exec deployment/gi -- wget -q -O - http://127.0.0.1:8080/healthz
	@kubectl -n gi exec deployment/gi -- sh -c 'test -s /data/finance.json' \
	  && echo 'data file mounted' || { echo 'data file missing: run make -f apps/gi/Makefile finance' >&2; exit 1; }
	@code=$$(curl -s -o /dev/null -w '%{http_code}' https://gi.soyspray.vip/data/finance.json); \
	  case "$$code" in 302|401) echo "anonymous request refused ($$code)";; \
	  *) echo "anonymous request answered $$code" >&2; exit 1;; esac

.DEFAULT:
	@printf 'unknown: gi has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
