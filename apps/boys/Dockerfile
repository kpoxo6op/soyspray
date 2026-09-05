FROM python:3.13-alpine@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0

ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY app/ /app/
USER 1000:1000
EXPOSE 8080 8443
CMD ["python", "/app/server.py"]
