include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.DEFAULT_GOAL := check
LIVE_TV_ENABLED ?= false
LIVE_TV_REVISION ?= $(REVISION)
ifeq ($(LIVE_TV_ENABLED),true)
LIVE_TV_TAGS := authentik,live-tv
LIVE_TV_AUTHENTIK_ARGS := -e authentik_target_revision=$(LIVE_TV_REVISION)
else
LIVE_TV_TAGS := live-tv
LIVE_TV_AUTHENTIK_ARGS :=
endif

.PHONY: check deploy
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_live_tv.py

deploy:
	cd $(ROOT) && $(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags $(LIVE_TV_TAGS) $(LIVE_TV_AUTHENTIK_ARGS) \
		-e live_tv_enabled=$(LIVE_TV_ENABLED) \
		-e live_tv_target_revision=$(LIVE_TV_REVISION)


.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' 'live-tv' '$@' >&2; exit 2
