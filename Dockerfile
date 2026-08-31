# Этап 1: сборка wheel-пакета
FROM python:3.11-slim AS builder

WORKDIR /build
COPY . .
RUN python -m pip install build && \
    python -m build

# Этап 2: окружение для запуска
FROM python:3.11-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Шрифт для рендера изображений
COPY ./data/fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

# Системные зависимости
RUN apt-get -yqq update && \
    apt-get -yqq install --no-install-recommends \
        wkhtmltopdf \
        ffmpeg \
        curl \
        jq \
        libmagic1 \
        unzip && \
    apt-get -yq clean && \
    apt-get -yq purge --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/dist/*.whl /app/

# Скачивание WebUI с международного реестра npmjs (CN-зеркала удалены)
RUN PACKAGE_INFO=$(curl -s https://registry.npmjs.org/kirara-ai-webui) && \
    LATEST_VERSION=$(printf %s $PACKAGE_INFO | jq -r '.["dist-tags"].latest') && \
    TARBALL_URL=$(printf %s $PACKAGE_INFO | jq -r --arg VERSION "$LATEST_VERSION" '.versions[$VERSION].dist.tarball') && \
    curl -L -o webui.tgz "$TARBALL_URL" && \
    mkdir -p /tmp/webui && \
    tar -xzf webui.tgz -C /tmp/webui && \
    mkdir -p /app/web && \
    cp -r /tmp/webui/package/dist/* /app/web/ && \
    rm -rf /tmp/webui webui.tgz && \
    pip install --no-cache-dir *.whl && \
    pip cache purge && \
    rm *.whl

RUN apt-get -yqq remove --purge curl jq unzip

COPY ./docker/start.sh /app/docker/
COPY ./data /tmp/data
EXPOSE 8080

CMD ["/bin/bash", "/app/docker/start.sh"]
