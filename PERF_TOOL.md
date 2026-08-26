# perf_tool — GeoNode performance test webapp

A small Flask app that times an action against this GeoNode instance end to
end and diffs Postgres's own `pg_stat_database` / `pg_stat_user_tables`
counters around it. Ported over from the `geonode` core repo's own
`PERF_TOOL.md`/`PERFORMANCE_FIX_PLAN.md` — same tool, adapted here for this
project's build-your-own-images layout (`docker/nginx`, `docker/postgresql`,
etc. each build a local image on top of a `geonode/*` base, versioned via
`.env`, rather than using the prebuilt images directly).

## Why this approach, and what "trustworthy" means here

Works with no special privilege at all, reading the same statistics views
GeoNode's own database role can already see — that's the guaranteed
baseline (`pg_stat_database`/`pg_stat_user_tables`, no superuser, no
`ALTER SYSTEM`, no docker log scraping). If `pg_stat_statements` is
*also* installed and readable, the tool additionally shows an exact
per-query breakdown; otherwise it says so plainly and sticks to the
table-level counters. See "Enabling `pg_stat_statements`" below — it's
wired up here via a `command:` flag on the `db` service already, so it
should be ready to go the first time this stack starts.

**The honest caveat**: `pg_stat_database`/`pg_stat_user_tables` are
database-wide counters, not scoped to one HTTP request. If something else is
hitting the same Postgres instance while a test runs (another user, a
celery beat tick, a concurrent test), that shows up in the delta too. This
is inherent to the method, not a bug — the fix is the same one used
manually: run against a quiet instance when precision matters, run several
iterations and look at the average, and prefer *relative* comparisons
(before a fix vs. after) over trusting one absolute number. The built-in
iteration and compare features exist for exactly this reason.

## Starting it

It's a service in this project's `docker-compose.yml`, named `perftool`:

```bash
docker compose up -d --build perftool
```

Reachable two ways:
- **`http://localhost/performance/`** — through this project's real nginx,
  alongside GeoNode itself. This is the intended way to use it day to day.
- **`http://localhost:5001`** — directly, bypassing nginx. Useful for
  debugging the tool itself independent of the nginx routing below.

Run history persists in a named volume (`${COMPOSE_PROJECT_NAME}-perftool-data`)
so it survives container restarts. To stop it: `docker compose stop perftool`
— doesn't touch or restart any other service.

**Port/name collision note**: this project's default `COMPOSE_PROJECT_NAME`,
`HTTP_PORT`/`HTTPS_PORT` (80/443), and perftool's port (5001) are the same
defaults the `geonode` core repo's dev stack uses — the two can't run on the
same host at the same time without changing one of them first.

### How `/performance` is wired up

Unlike the `geonode` core repo (which uses nginx's *prebuilt* image and has
to bind-mount the routing config over a named volume), this project already
builds its own `docker/nginx` image on top of `geonode/nginx` — so
`docker/nginx/performance.conf` is simply `COPY`'d into the image at build
time (`docker/nginx/Dockerfile`), landing in `/etc/nginx/sites-enabled/`
next to the `geonode.conf` that image's own entrypoint generates from a
template at container startup. (Docker populates a named volume from the
image's own content on first creation, so the baked-in file survives being
overlaid by the `nginx-confd` volume mount in `docker-compose.yml`.)

Three nginx gotchas the config file works around, each found by the route
actually breaking on a real deploy rather than guessed up front — documented
in full in `docker/nginx/performance.conf`'s own comments:

1. **Regex locations beat prefix locations, always** — `geonode.conf` has a
   `location ~* \.(?:css|js|...)$` nested under `location /` matching any
   static-asset extension, and nginx checks regex locations before prefix
   locations regardless of specificity. Fixed with the `^~` modifier.
2. **A *variable* `proxy_pass` target disables prefix-stripping** — the
   trick `geonode.conf` uses elsewhere for start-before-upstream-is-up
   resilience (`set $upstream ...; proxy_pass http://$upstream;`) costs
   nginx's automatic "strip the matched location prefix" rewrite — every
   request arrived at perftool as `/` regardless of actual path.
3. **...but a *literal* target refuses to even start if the upstream isn't
   resolvable yet** — the first fix for #2 (a literal
   `proxy_pass http://perftool:5001/;`) resolves that hostname once, at
   config-load time. On a cold `docker compose up` this took down nginx
   entirely (`host not found in upstream "perftool"`) — not a 502 on that
   one route, a hard crash of the whole nginx, confirmed on an actual fresh
   deploy of this project. Fixed by keeping the resilient `$variable` target
   and doing the prefix-strip explicitly via `rewrite ... break;` instead —
   with `set $upstream` placed *before* the `rewrite`, since `break` halts
   every remaining rewrite-module directive in the block including a `set`
   that comes after it (also hit this live: `invalid URL prefix in
   "http://"`, `$upstream` silently never assigned).

**If you already deployed before this fix landed**: rebuilding the nginx
image alone isn't enough — `nginx-confd` is a *named volume*, populated
from the image only on first creation, so an existing deployment's volume
keeps its stale baked-in file even after `docker compose build nginx`. Fix
it directly: `docker run --rm -v <project>-nginxconfd:/etc/nginx -v
$(pwd)/docker/nginx/performance.conf:/tmp/performance.conf:ro alpine cp
/tmp/performance.conf /etc/nginx/sites-enabled/performance.conf`, then
`docker exec nginx4<project> nginx -s reload`. A brand new deployment
doesn't need this — the rebuilt image already has the right content.

Flask itself needs to know it's being served under a path prefix, or every
link/form action/redirect it generates would still point at `/` instead of
`/performance/`. `perf_tool/app.py` uses Werkzeug's `ProxyFix` reading the
`X-Forwarded-Prefix: /performance` header the nginx config sends, which
sets `SCRIPT_NAME` so `url_for()` and redirects come out correctly prefixed.

## Enabling `pg_stat_statements`

Already wired up in `docker-compose.yml`'s `db` service `command:`:
```
postgres -c "max_connections=${POSTGRESQL_MAX_CONNECTIONS}" -c "shared_preload_libraries=pg_stat_statements"
```
`shared_preload_libraries` is a postmaster-context setting (can't be changed
with `ALTER SYSTEM` + reload, needs the flag at startup) — since this
project doesn't otherwise customize `postgresql.conf`, passing it as a
`command:` flag was the smallest change that gets the same result as the
core repo's `conf.d`-file approach, without introducing a new config-file
mechanism this project doesn't already have.

One remaining one-time step, **after the first startup with this in place**:
```bash
docker exec db4${COMPOSE_PROJECT_NAME} psql -U postgres -d ${GEONODE_DATABASE} -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
```
(substitute the real values of `COMPOSE_PROJECT_NAME`/`GEONODE_DATABASE`
from `.env`, or just run the psql command inside a shell in that container
where they're already set as env vars). The plain database role can read it
afterward without superuser — verified this in the core repo with
`SELECT count(*) FROM pg_stat_statements;` as that role.

To turn it back off: remove the `-c "shared_preload_libraries=..."` flag
from the `db` service `command:` and restart `db`. The tool doesn't care
either way — it detects availability at snapshot time and falls back
cleanly to the table-level counters.

## Request-scoped query stats — needs a newer GeoNode base image

The core repo's tool also shows a genuinely request-scoped, zero-noise
metric ("DB queries (this request only)") via a new
`geonode.base.middleware.RequestQueryStatsMiddleware` added straight into
the `geonode` package, gated by an `EXPOSE_DB_QUERY_STATS_HEADER` setting.

**This project can't use it yet as-is**: `Dockerfile` here builds `FROM
geonode/geonode-base:${GEONODE_BASE_IMAGE_VERSION}` — a prebuilt image with
the released `geonode` package already installed — rather than vendoring
GeoNode's source tree the way `geonode` core's own repo does. The
middleware lives in that source tree, not in this project, so there's
nothing to bake in here until a `geonode-base` image built from a GeoNode
version that includes it is published (or this project's `Dockerfile` is
changed to build from that source instead of the prebuilt base image — a
bigger, separate decision about this project's dependency model, not
something to do as a side effect of adding a perf tool).

Until then: the "DB queries (this request only)" card and the `req.
queries`/`req. DB ms` per-iteration columns will show `0` here — the tool
detects this the same way it detects a missing `pg_stat_statements` and
falls back cleanly, nothing else breaks.

## Python-level profiling — same base-image caveat

A second middleware, `geonode.base.middleware.RequestProfilingMiddleware`,
wraps the request in stdlib `cProfile` and returns the slowest functions by
*self* time (tottime, not cumtime — cumtime on a request profile is just
the middleware/dispatch chain retracing itself), filtered to frames whose
file path contains `/geonode/` — a raw top-N by self time is dominated by
psycopg2/Django/DRF internals with no app code behind them to change, and
the one place that noise IS the finding (an unindexed query, a per-row
`reverse()` call) still shows up here attributed to the geonode call site
that triggered it. Returned as an `X-Profile-Top` header, gated by
`EXPOSE_REQUEST_PROFILING`. Same "needs a newer GeoNode base image"
limitation as above — it lives in the same source tree. The result page's
"Slowest functions" tab shows a hint instead of data until that's
available. Adds real per-request overhead
when on; leave it off outside a profiling session.

## Using it

1. **Target & credentials** — base URL defaults to this instance's own
   `SITEURL` (the same env var GeoNode itself uses), and the Host-header
   override defaults on only when that URL's host is `localhost`/`127.0.0.1`
   — otherwise it defaults off. Two real deployment shapes this needs to
   handle:
   - **`SITEURL=http://localhost` (typical local/dev instance)**: from
     *inside* the `perftool` container, "localhost" means that container's
     own loopback, not the host machine running docker — so the default base
     URL won't actually reach anything. Change `base_url` to the internal
     service name (`http://nginx`) and keep the Host header override at
     `localhost`, so nginx still routes it correctly (its plain-HTTP vhost
     only matches `server_name localhost 127.0.0.1`).
   - **`SITEURL` is a real public domain behind TLS**: the default base URL
     (the real domain) usually works fine *if* `perftool` can actually reach
     it — but on infra that doesn't allow "hairpin" traffic (a machine
     inside the private network reaching the same server via its *public*
     domain/IP — common with load balancers/WAFs), it won't, even though the
     domain is perfectly reachable from outside. Symptom: `curl`/`requests`
     both get a connection dropped with no HTTP response at all. Fix: switch
     `base_url` to the internal service name instead (e.g. `https://nginx`),
     set the Host header override to the real domain (so nginx's
     `server_name` still matches), and check **Skip TLS certificate
     verification** — the internal name won't match the cert's hostname even
     though the cert itself is perfectly valid for the real domain.
   Username/password are a real GeoNode account on this instance.
2. **Scenario** — pick a built-in test:
   - **List resources** / **List maps** — times `GET /api/v2/...`.
   - **Upload a CSV dataset** — runs a real upload through the full
     pipeline (sync accept → celery → GeoServer → resource created),
     polling until it finishes. Generates a CSV with the given row count,
     or upload your own file instead.
   - **Create an empty map** / **Create a GeoApp** — times
     `POST /api/v2/maps` / `POST /api/v2/geoapps`. GeoApp's `resource_type`
     isn't a fixed choice field in GeoNode (no API exposes "the list of
     valid types") — leave it blank and the scenario discovers whatever
     types already exist on this instance (via `GET /api/v2/geoapps`) and
     creates one of each, instead of silently assuming one; set it
     explicitly to test just that type.
   - **View / Copy / Edit metadata of an existing resource** — these operate
     on a **real resource already in the instance** rather than a freshly
     synthetic one. Selecting one of these scenarios reveals a "Target
     resource" dropdown — click **Load resources**, which logs in with
     whatever credentials are currently in the form and fetches a real page
     of resources from `GET /api/v2/resources` to populate it.
   - **Custom request** — an escape hatch: method (GET/POST/PATCH/PUT),
     path, and JSON body for anything not covered above.
3. **Repeat the test / iterations** — use the "Run 3x/5x/10x (avg)" buttons
   (or the number field directly, 1-50) to run the scenario back to back
   and get min/avg/median/max, both for wall time and for the DB delta. Use
   more than 1 whenever you're about to trust the number — a single run on
   a shared instance is noise, an average of 3-5 is a measurement.
4. **Label** — free text, e.g. "before fix" / "after fix". Shows up in
   history and makes the compare view legible later.

## Downloading a report

Every result page has a **Download report (.pdf)** button. Averages only —
wall time and DB-statement averages plus a short "how these numbers are
calculated" note, meant to be handed to someone who wasn't in the room when
the test ran. Full per-iteration/per-table/query detail stays on the web
page, not the PDF.

## Reading a result page / comparing runs / extending it

See the `geonode` core repo's `PERF_TOOL.md` and the in-app **How it works**
page (`/performance/how-it-works`) — identical content and identical code
here, just running against this project's stack instead. The only
differences are the two called out above: `pg_stat_statements` is wired up
via a `command:` flag instead of a `conf.d` file, and the request-scoped
query-stats card needs a GeoNode base image with
`RequestQueryStatsMiddleware` in it to show anything but 0.

## What this tool is not

Not a load-testing tool (no concurrent virtual users, one action at a time)
and not a substitute for the Django test suite's `assertNumQueries` —
those catch regressions in CI before merge; this catches "is this actually
faster" against a real running instance, which is a different, complementary
question. It's also not authenticated/hardened for exposure outside the
docker network — it runs Flask's development server deliberately (this is a
single-operator internal tool, not a public service), and it holds
whatever GeoNode credentials you type into it only in memory for the
duration of a request.
