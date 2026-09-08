# Voice commands

Use `make check APP=voice-assistant` to check voice configuration. Use
`make -f apps/voice-assistant/Makefile bootstrap` only for the private Home
Assistant token and GI model. Merge the pull request to deploy through Argo
from `main`.

Use `make voice-pe-render`, `make voice-pe-check`, or
`make voice-pe-compile` for firmware preparation. `make voice-pe-upload
VOICE_PE_HOST=device` runs the full local gate before upload.
