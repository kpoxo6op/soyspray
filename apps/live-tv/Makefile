include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.DEFAULT_GOAL := check
.PHONY: check bootstrap
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_live_tv.py

bootstrap:
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-app-inputs.yml --tags authentik,live-tv


.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' 'live-tv' '$@' >&2; exit 2
