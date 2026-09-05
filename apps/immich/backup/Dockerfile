FROM restic/restic:0.18.1@sha256:39d9072fb5651c80d75c7a811612eb60b4c06b32ffe87c2e9f3c7222e1797e76
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="$SOURCE_REVISION" \
      org.opencontainers.image.description="Versioned Immich recovery scripts for native PostgreSQL and Restic"
COPY --chmod=0555 dump.sh backup.sh /scripts/
COPY --chmod=0444 dump.sql /scripts/
USER 1000:1000
ENTRYPOINT ["/bin/sh", "-c", "cp -R /scripts/. /work/"]
