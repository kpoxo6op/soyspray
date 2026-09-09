include $(dir $(lastword $(MAKEFILE_LIST)))common.mk
.DEFAULT_GOAL := check
.PHONY: check diff restore-check

check:
	cd $(ROOT) && $(PYTHON) scripts/validate_yaml.py
	$(if $(APP_TESTS),cd $(ROOT) && $(PYTHON) -m pytest -q $(APP_TESTS),@:)

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app $(APP_NAME) $(DIFF_MODE)

restore-check:
	$(if $(RESTORE_TARGET),cd $(ROOT) && $(PYTHON) -m scripts.restore_durable --app $(RESTORE_TARGET),@printf '%s\n' 'unknown: $(APP_NAME) has no maintained isolated restore check.' >&2; exit 2)

.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' '$(APP_NAME)' '$@' >&2; exit 2
