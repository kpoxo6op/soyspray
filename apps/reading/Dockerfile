FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build
WORKDIR /build
COPY app/ ./
RUN node build.mjs && node --test test/*.test.mjs
# Keep deterministic gzip copies of text assets; woff2 fonts are already compressed.
RUN find dist -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.svg' -o -name '*.json' \) -exec gzip -9 -n -k {} +

FROM nginxinc/nginx-unprivileged:1.30-alpine@sha256:ee7b7bc02a4af72c98d4365151f92d9b380c482c48d8c84bbbe44bd3192ba463
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist/ /usr/share/nginx/html/
USER 101:101
EXPOSE 8080
