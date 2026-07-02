# Docker-backed PHP (Short Guide)

This setup makes **PHP run in Docker by default** while behaving like native PHP on the host.
It is optimized for Laravel + Vite workflows.

---

## What this gives you

- One shared PHP image (no per-project Dockerfiles)
- Works with `pnpm run dev` and Vite watchers
- No host PHP version management
- Clean access to Dockerized MySQL/Redis/Postgres
- Explicit escape hatch for system PHP

---

## Commands

| Command | Purpose |
|------|--------|
| `php` | Dockerized PHP (version configurable) |
| `composer` | Dockerized Composer |
| `sysphp` | Host PHP (bypass Docker) |

---

## Networking

The PHP and Composer wrappers use `--network host` by default. This means the container shares the host's network stack directly — no bridge DNS, no port mapping needed. Your Laravel `.env` should use `localhost` for service hosts:

```env
DB_HOST=localhost
REDIS_HOST=localhost
```

This works because the Docker Compose services (Postgres, Redis, MySQL, etc.) expose their ports to the host.

> **Why not bridge networking?** Bridge networks rely on Docker's internal DNS and iptables NAT rules, which can break when other containers manipulate iptables (e.g., VPN containers like Gluetun). Host networking avoids this entirely and is simpler for a portable PHP setup where the goal is just to run PHP in a container, not to isolate it.

To override the network (e.g., for testing bridge mode), set `PHP_NETWORK`:

```bash
PHP_NETWORK=env_system php artisan serve
```

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

---

## Configure PHP Version

### Permanent Update

Set `PHP_VERSION` in your shell profile or environment. The `php` and `composer`
commands now live in `tools/.local/bin` and read the value at runtime through the
shared Python Docker wrapper.

The image build arg in `php/Dockerfile` should match the version you want to
build.

After a permanent update, rebuild the Docker image with the `php-build` command
documented below. The build command keeps the build arg, cache source, and image
tag consistent.

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
php-build 8.4
```

**Notes:**
- `php-build 8.4` builds `my/php:8.4-dev`. You can also use `php-build --php-version 8.4`.
- The `PHP_VERSION` build arg should match the runtime version exported for the `php` and `composer` tools.
- Run `php-build --help` for flags such as `--tag`, `--context`, `--builder`, `--legacy`, `--no-cache`, `--pull`, and `--dry-run`.
- `php-build` prefers BuildKit when `docker buildx` is installed. Without buildx, it falls back to Docker's legacy builder with a warning.
- Install `docker-buildx` for the best cache behavior, or use `php-build --buildkit` to fail fast when BuildKit is unavailable.
- `php-build` passes `--cache-from my/php:<version>-dev`; when BuildKit is available it also passes `BUILDKIT_INLINE_CACHE=1` so future builds have a better chance of reusing layers after ordinary Docker cleanup.
- If a late Dockerfile line is added, earlier steps should be cached. If the build restarts at an early `RUN apt-get ...` step, the intermediate build cache was probably pruned or a source image tag changed.
- Extra Docker build options go after `--`:
  ```bash
  php-build 8.4 -- --progress=plain
  ```

---

## Usage

```bash
composer install
php artisan migrate
php artisan serve
```

With host networking, ports are shared directly — no mapping needed.

---

## Database config (.env)

```env
DB_HOST=localhost
DB_PORT=3306
```

With host networking, use `localhost` — services are reached via their host-mapped ports.

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
