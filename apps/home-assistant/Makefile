include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.DEFAULT_GOAL := check

.PHONY: check diff restore-check
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_home_assistant_voice.py tests/test_home_assistant_restore.py

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app home-assistant

restore-check:
	cd $(ROOT) && $(PYTHON) -m scripts.restore_durable --app home-assistant-config

.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' 'home-assistant' '$@' >&2; exit 2
