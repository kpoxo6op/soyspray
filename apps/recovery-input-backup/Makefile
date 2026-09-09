include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_recovery_input_backup.py
	cd $(ROOT) && $(ANSIBLE) apps/recovery-input-backup/install.yml --check

.DEFAULT:
	@printf 'unknown: recovery-input-backup has no maintained %s operation.\n' '$@' >&2; exit 2
