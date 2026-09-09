include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check
check:
	cd $(ROOT) && $(PYTHON) apps/cluster-diagnosis/tests/test_adapter.py

.DEFAULT:
	@printf 'unknown: cluster-diagnosis has no maintained %s operation.\n' '$@' >&2; exit 2
