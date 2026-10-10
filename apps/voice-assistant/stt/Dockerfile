FROM python:3.12-slim@sha256:3d5ed973e45820f5ba5e46bd065bd88b3a504ff0724d85980dcd05eab361fcf4
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 \
    HOME=/tmp OMP_NUM_THREADS=2
WORKDIR /app
RUN pip install --no-cache-dir 'wyoming-faster-whisper[sherpa]==3.8.1' \
    'sherpa-onnx==1.13.8' 'av==16.1.0'
COPY models.lock.json download_models.py /app/
RUN python download_models.py --output /models
COPY serve.py probe.py NOTICE.md /app/
USER 1000:1000
ENTRYPOINT ["python", "/app/serve.py"]
CMD ["--uri", "tcp://0.0.0.0:10300", "--data-dir", "/models", "--download-dir", "/models", "--local-files-only", "--language", "en", "--stt-library", "sherpa", "--model", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8", "--cpu-threads", "2", "--beam-size", "1"]
