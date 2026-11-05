FROM python:3.12-slim@sha256:3d5ed973e45820f5ba5e46bd065bd88b3a504ff0724d85980dcd05eab361fcf4
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 HOME=/tmp \
    OMP_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* && ffmpeg -hide_banner -version | head -1
WORKDIR /app
COPY runtime-requirements.lock models.lock.json download_model.py /app/
RUN pip install --no-cache-dir --no-deps -r runtime-requirements.lock && pip check
RUN python download_model.py --output /models
COPY app/horoscope.py /app/horoscope.py
USER 1000:1000
EXPOSE 8080
ENTRYPOINT ["python3", "/app/horoscope.py"]
