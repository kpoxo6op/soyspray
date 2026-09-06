include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.DEFAULT_GOAL := check
.PHONY: check deploy fallback
check:
	cd $(ROOT) && $(PYTHON) scripts/configure_status_page.py --check

deploy:
	cd $(ROOT) && $(PYTHON) scripts/configure_status_page.py

fallback: check
	cd $(ROOT) && $(PYTHON) scripts/configure_status_page.py --fallback


.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' 'status-page' '$@' >&2; exit 2
