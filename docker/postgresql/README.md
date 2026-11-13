# PostgreSQL configuration

The `db` container starts PostgreSQL with the `postgresql.conf` of this folder. It loads, in this order (the last one wins):

1. the configuration created by the image inside the data volume
2. the settings taken from `.env`
3. the `.conf` files inside `conf.d`

Settings from `.env`:

- `POSTGRESQL_MAX_CONNECTIONS`: value for `max_connections` (default 200)
- `POSTGRESQL_PROFILE`: name of a folder inside `profiles`, its `.conf` files are loaded. Nothing is loaded if unset.

Use `conf.d` for settings that must always apply, and `profiles` to keep alternative setups side by side,
e.g. `profiles/production/tuning.conf` is loaded with `POSTGRESQL_PROFILE=production`.
Both folders are empty by default, so PostgreSQL runs with the image configuration.

After changing the `.conf` files run `docker compose restart db`, after changing `.env` run `docker compose up -d db`.
