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

# Defaults that help dev
ENV COMPOSER_ALLOW_SUPERUSER=1
WORKDIR /app

