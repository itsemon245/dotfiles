# Docker-backed PHP (Short Guide)

This setup makes **PHP run in Docker by default** while behaving like native PHP on the host.
It is optimized for Laravel + Vite workflows.

---

## What this gives you

- One shared PHP image (no per-project Dockerfiles)
- Works with `pnpm run dev` and Vite watchers
- No host PHP version management
- Clean access to Dockerized MySQL/Redis
- Explicit escape hatch for system PHP

---

## Commands

| Command | Purpose |
|------|--------|
| `php` | Dockerized PHP (version configurable) |
| `composer` | Dockerized Composer |
| `sysphp` | Host PHP (bypass Docker) |

---

## Docker Services

The `docker-compose.yml` provides these services on the `env_system` network:

- **mysql** (MariaDB 11.8) - Port 3306
- **postgres** (PostgreSQL 17) - Port 5432
- **redis** (Redis 8.0.2) - Port 6379
- **phpmyadmin** - Port 8080
- **pgadmin** - Port 8081
- **redisinsight** - Port 5540

Start services: `docker compose up -d`

---

## Environment Configuration

Create a `.env` file in this directory to configure:
- Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `MYSQL_ROOT_PASSWORD`, etc.)
- Port mappings (`REDIS_PORT`, `POSTGRES_PORT`, `MYSQL_PORT`, etc.)
- Service-specific settings (PgAdmin email/password, upload limits, etc.)

All services use the `env_system` network for DNS resolution.

---

## Configure PHP Version

### Permanent Update

Edit the `PHP_VERSION` variable at the top of:
- `bin/php` script (line 5)
- `bin/composer` script (line 5)
- `php/Dockerfile` (line 2)

**After permanent update, rebuild the Docker image:**

```bash
PHPV=8.4 && docker build --build-arg PHP_VERSION=$PHPV -t my/php:$PHPV-dev ~/dotfiles/others/env/php
```

Replace `8.4` with your desired version. The `PHPV` variable ensures consistency between the build arg and image tag.

### On-Demand Update

Set the `PHP_VERSION` environment variable:

```bash
PHP_VERSION=8.5 php -v
PHP_VERSION=8.5 composer install
```

Or set it for the current session:

```bash
export PHP_VERSION=8.5
php -v
composer install
```

---

## Build PHP Docker Image

Build the image with the configured PHP version:

```bash
PHPV=8.4 && docker build --build-arg PHP_VERSION=$PHPV -t my/php:$PHPV-dev ~/dotfiles/others/env/php
```

**Notes:**
- `PHPV` variable ensures the version is consistent between build arg and image tag
- The `PHP_VERSION` build arg should match the version in `bin/php` and `bin/composer` scripts
- Alternative: Set the variable first, then run the build command:
  ```bash
  export PHPV=8.4
  docker build --build-arg PHP_VERSION=$PHPV -t my/php:$PHPV-dev ~/dotfiles/others/env/php
  ```

---

## Usage

```bash
composer install
php artisan migrate
php artisan serve --host=0.0.0.0 --port=8000
```

Ports `8000–8009` are pre-mapped.

---

## Database config (.env)

```env
DB_HOST=mysql
DB_PORT=3306
```

Services are resolved via Docker DNS on the `env_system` network.

---

## Node / Vite compatibility

No changes required.  
Commands like this work automatically:

```js
command: "php artisan ziggy:generate --types"
```

---

## System PHP (intentional)

```bash
sysphp -v
sysphp script.php
```

---

## Why this exists

- No per-project Docker setup
- No breaking team workflows
- Easy to add PHP 8.5/8.6 later
- Same behavior on any machine with Docker

