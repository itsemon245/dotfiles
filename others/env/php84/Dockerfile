FROM php:8.4-cli

# System deps + build deps for common PHP extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    git unzip zip curl ca-certificates \
    libzip-dev \
    libicu-dev \
    libpng-dev libjpeg-dev libfreetype6-dev \
    libmagickwand-dev imagemagick \
    && rm -rf /var/lib/apt/lists/*

# PHP extensions
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" \
      bcmath intl pcntl sockets pdo_mysql zip gd

# PECL extensions: imagick + redis
RUN pecl install imagick redis \
    && docker-php-ext-enable imagick redis

# Composer (copied from official image)
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer

# Defaults that help dev
ENV COMPOSER_ALLOW_SUPERUSER=1
WORKDIR /app

