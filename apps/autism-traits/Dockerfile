FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build
WORKDIR /build
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run check

FROM nginxinc/nginx-unprivileged:1.30-alpine@sha256:ee7b7bc02a4af72c98d4365151f92d9b380c482c48d8c84bbbe44bd3192ba463
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY --from=build /build/dist/ /site/
COPY config/nginx.conf /config/nginx.conf
USER 101:101
EXPOSE 8080 8443
ENTRYPOINT ["nginx", "-c", "/config/nginx.conf", "-g", "daemon off;"]
