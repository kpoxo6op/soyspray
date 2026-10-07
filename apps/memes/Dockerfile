FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2
ARG SOURCE_REVISION=local
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV SOURCE_REVISION=${SOURCE_REVISION} PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=4
WORKDIR /app
COPY web-requirements.lock ./
RUN pip install --no-cache-dir -r web-requirements.lock
COPY memes/__init__.py memes/catalog.py memes/recommender.py memes/metrics.py memes/store.py memes/server.py memes/admin.py memes/schema.sql ./memes/
COPY memes/static/ ./memes/static/
USER 1000:1000
EXPOSE 8080
CMD ["python", "-m", "memes.server"]
