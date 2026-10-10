FROM python:3.12-slim@sha256:3d5ed973e45820f5ba5e46bd065bd88b3a504ff0724d85980dcd05eab361fcf4
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SOURCE_REVISION=${SOURCE_REVISION}
COPY custom_components/gi_voice /component
COPY install.py /install.py
ENTRYPOINT ["python3", "/install.py"]
