# Configure PHP version here (e.g., "8.4", "8.5", "8.6")
ARG PHP_VERSION=8.4

FROM php:${PHP_VERSION}-cli

# uv is provided as static binaries by Astral's official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# System deps + build deps for common PHP extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip zip curl ca-certificates python3 python3-venv \
    libzip-dev \
    libicu-dev \
    libpng-dev libjpeg-dev libfreetype6-dev \
    libmagickwand-dev imagemagick \
    libpq-dev \
    libxml2-dev \
    libonig-dev \
    && rm -rf /var/lib/apt/lists/*

# PHP extensions (core + database + common dev)
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" \
      bcmath \
      intl \
      pcntl \
      posix \
      sockets \
      pdo_mysql \
      mysqli \
      pdo_pgsql \
      pgsql \
      zip \
      gd \
      mbstring \
      xml \
      xmlreader \
      xmlwriter \
      fileinfo \
      exif \
      opcache

# PECL extensions: imagick + redis + xdebug
RUN pecl install imagick redis xdebug \
    && docker-php-ext-enable imagick redis xdebug

# Composer (copied from official image)
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer

# Custom PHP configuration
COPY php.ini /usr/local/etc/php/conf.d/custom.ini

# Node.js, npm, and pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm

# Ensure Puppeteer installs Chrome into a predictable, persistent path
ENV PUPPETEER_CACHE_DIR=/usr/local/share/puppeteer \
    PUPPETEER_DOWNLOAD_PATH=/usr/local/share/puppeteer \
    PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chrome

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p "$PUPPETEER_CACHE_DIR" \
    && npx puppeteer browsers install chrome \
    && CHROME_PATH="$(find "$PUPPETEER_CACHE_DIR" -type f -name chrome -path "*chrome-linux64/chrome" | head -n 1)" \
    && ln -sf "$CHROME_PATH" "$PUPPETEER_EXECUTABLE_PATH"

# ffmpeg (installed at the end to preserve cached layers)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install ExifTool
RUN apt-get update && apt-get install -y --no-install-recommends exiftool \
    && rm -rf /var/lib/apt/lists/*

# redis-cli, for code that shells out to it (artistly's AccumulatorService scans keys with it).
RUN apt-get update && apt-get install -y --no-install-recommends redis-tools \
    && rm -rf /var/lib/apt/lists/*

# OPcache for the CLI too (artisan, workers, test runs); see opcache-cli.ini. Loaded after
# custom.ini (zz-), so its settings win. At the end to keep the layers above cached.
COPY opcache-cli.ini /usr/local/etc/php/conf.d/zz-opcache-cli.ini

# SSH for Composer packages from private GitHub repositories. The wrappers pass
# the host's SSH agent in, so no key lives in the image. GitHub's published
# ed25519 host key is pinned system-wide because HOME (/tmp) is not persistent.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && echo 'github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl' > /etc/ssh/ssh_known_hosts

# Defaults that help dev
ENV COMPOSER_ALLOW_SUPERUSER=1 \
    REDIS_CLIENT=phpredis \
    HOME=/tmp \
    XDG_CONFIG_HOME=/tmp/.config \
    COMPOSER_CACHE_DIR=/tmp/composer-cache
WORKDIR /app

# Keep raw docker runs safe for bind-mounted project directories. The wrappers
# still pass --user at runtime, while php-build sets these defaults for the host.
ARG PHP_UID=1000
ARG PHP_GID=1000
# OpenSSH refuses to run as a uid with no passwd entry ("No user exists for uid").
RUN (getent group "${PHP_GID}" || groupadd -g "${PHP_GID}" dev) \
    && (getent passwd "${PHP_UID}" || useradd -u "${PHP_UID}" -g "${PHP_GID}" -d /tmp -M -s /bin/bash dev)
USER ${PHP_UID}:${PHP_GID}
