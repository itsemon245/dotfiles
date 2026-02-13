# Configure PHP version here (e.g., "8.4", "8.5", "8.6")
ARG PHP_VERSION=8.4

FROM php:${PHP_VERSION}-cli

# System deps + build deps for common PHP extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip zip curl ca-certificates \
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

# Defaults that help dev
ENV COMPOSER_ALLOW_SUPERUSER=1 \
    REDIS_CLIENT=phpredis
WORKDIR /app

