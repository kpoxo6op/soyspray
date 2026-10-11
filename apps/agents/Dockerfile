FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build
WORKDIR /build
RUN apt-get update && apt-get install --yes --no-install-recommends python3 git && rm -rf /var/lib/apt/lists/*
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
COPY tests/test_lab.py ./qa/test_lab.py
RUN npm run build && npm test
RUN --network=none AGENTS_LAB_SCRIPT=/build/src/lab.py python3 -I -m unittest discover -s qa -v
RUN --network=none python3 -I src/lab.py run --root /build/offline-lab \
    && python3 -I src/lab.py verify --root /build/offline-lab \
    && python3 -I src/lab.py cleanup --root /build/offline-lab \
    && test ! -e /build/offline-lab

FROM nginxinc/nginx-unprivileged:1.30-alpine@sha256:ee7b7bc02a4af72c98d4365151f92d9b380c482c48d8c84bbbe44bd3192ba463
USER root
RUN apk add --no-cache python3
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY --from=build /build/dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
COPY evidence.py start-web.sh /opt/
RUN chmod 0555 /opt/start-web.sh /opt/evidence.py
USER 101:101
EXPOSE 8080
ENTRYPOINT ["/opt/start-web.sh"]
