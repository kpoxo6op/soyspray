FROM python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d

ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.description="Node-local Jellyfin and books recovery backup"

ADD --checksum=sha256:680838f19d67151adba227e1570cdd8af12c19cf1735783ed1ba928bc41f363d \
    https://github.com/restic/restic/releases/download/v0.18.1/restic_0.18.1_linux_amd64.bz2 /tmp/restic.bz2
RUN apk add --no-cache bzip2 \
    && bunzip2 /tmp/restic.bz2 \
    && install -m 0555 /tmp/restic /usr/local/bin/restic \
    && rm /tmp/restic

COPY --chmod=0555 scripts/backup.py /scripts/backup.py
USER 0:0
ENTRYPOINT ["/usr/local/bin/python3", "/scripts/backup.py"]
