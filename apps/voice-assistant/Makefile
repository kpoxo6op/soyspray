include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.DEFAULT_GOAL := check
VOICE_ASSISTANT_REVISION ?= $(REVISION)
VOICE_ASSISTANT_ENABLED ?= true
VOICE_PE_HOST ?= home-assistant-voice-0a9b95.local
VOICE_PE_CONFIG := .build/voice-pe/gi-voice-pe.yaml
ESPHOME := uvx --from esphome==2025.5.1 esphome

.PHONY: check deploy voice-pe-render voice-pe-check voice-pe-compile voice-pe-upload
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_home_assistant_voice.py

deploy:
	cd $(ROOT) && $(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags voice_assistant \
		-e voice_assistant_target_revision=$(VOICE_ASSISTANT_REVISION) \
		-e voice_assistant_enabled=$(VOICE_ASSISTANT_ENABLED)

voice-pe-render:
	cd $(ROOT) && $(PYTHON) scripts/render_gi_voice_pe.py --output $(VOICE_PE_CONFIG)

voice-pe-check: voice-pe-render
	cd $(ROOT) && $(ESPHOME) config $(VOICE_PE_CONFIG) >/dev/null

voice-pe-compile: voice-pe-check
	cd $(ROOT) && $(ESPHOME) compile $(VOICE_PE_CONFIG)

voice-pe-upload: voice-pe-compile
	cd $(ROOT) && $(ESPHOME) upload $(VOICE_PE_CONFIG) --device $(VOICE_PE_HOST)


.DEFAULT:
	@printf 'unknown: %s has no maintained %s operation.\n' 'voice-assistant' '$@' >&2; exit 2
