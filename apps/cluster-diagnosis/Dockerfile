# The incident loop has no third-party dependencies: the standard library is the
# whole runtime, which keeps the image small and the supply chain short.
FROM python:3.13-slim

ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.title="soyspray cluster diagnosis" \
      org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="$SOURCE_REVISION"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY app/ /app/

USER 10001:10001
EXPOSE 9911

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:9911/healthz',timeout=4)"

ENTRYPOINT ["python3", "/app/diagnosis.py"]
