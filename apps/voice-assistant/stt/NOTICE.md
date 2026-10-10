# Model attribution

NVIDIA created Parakeet TDT 0.6B v2. This image uses the int8 ONNX conversion
distributed by k2-fsa/sherpa-onnx, without further modification.
The model is licensed under CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/
Original model and license: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2
Conversion: https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models

Whisper Base English and Small English were created by OpenAI and converted
to CTranslate2 by SYSTRAN. They use the MIT license:
https://github.com/openai/whisper/blob/main/LICENSE
https://huggingface.co/Systran/faster-whisper-base.en
https://huggingface.co/Systran/faster-whisper-small.en

The image retains both Whisper candidates for controlled comparisons; the
default is Parakeet. Model revisions and SHA-256 checksums are in models.lock.json.
