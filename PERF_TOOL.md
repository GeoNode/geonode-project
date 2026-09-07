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

## Python-level profiling

Unlike the request-scoped query-stats middleware above, this one **is**
usable here: `.env`'s `GEONODE_BASE_IMAGE_VERSION=master` already includes
`geonode.base.middleware.RequestProfilingMiddleware` in the base image, so
there's nothing to wait on.

That middleware wraps the request in stdlib `cProfile` and returns the
slowest functions by *self* time (tottime, not cumtime — cumtime on a
request profile is just the middleware/dispatch chain retracing itself),
filtered to frames whose file path contains `/geonode/` — a raw top-N by
self time is dominated by psycopg2/Django/DRF internals with no app code
behind them to change, and the one place that noise IS the finding (an
unindexed query, a per-row `reverse()` call) still shows up here attributed
to the geonode call site that triggered it. Gated by
`EXPOSE_REQUEST_PROFILING`.

**This project uses its own drop-in replacement**,
`geonode_project.profiling_middleware.RequestProfilingMiddleware`
(`src/geonode_project/profiling_middleware.py`), swapped in over the stock
one via a `MIDDLEWARE` list-comprehension in `settings.py` — not a bigger
change, same header contract (`X-Profile-Top`), same filter, same
`EXPOSE_REQUEST_PROFILING` gate. The only difference: the stock middleware
builds its header off `pstats.Stats.print_stats()`'s text table, and
stdlib's own number formatter there (`pstats.f8`) is hardcoded to
`"%8.3f" % x` — 3 decimal places, in *seconds*. Any geonode-code frame
under ~0.0005s self time — the common case on a DB-bound request, since
the actual query execution is a psycopg2 C-extension frame the
`/geonode/` filter excludes, leaving only lightweight Python glue —
prints as a literal `0.000` in that text, with the real value gone before
anyone downstream can read it. The project's version reads
`pstats.Stats().stats` directly (the same profiling run's underlying dict,
full float precision) and reports milliseconds instead of seconds, which
is precise enough to show real, non-zero numbers down to single-digit
microseconds.

Adds real per-request overhead when on (cProfile instruments every
function call) — leave it off outside a profiling session.

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

## Health — /performance/health

A different question from the rest of this tool: not "how fast was this
one action" but "is the stack up, right now". No login, no scenario, safe
to hit anytime — reload it to get a fresh read, nothing on it is saved to
history. Five independent checks (`perf_tool/health.py`), each fails soft
(shows "can't reach it" rather than crashing the page) so one broken check
never takes the others down with it:

- **Docker services** — state (`running`/`exited`/`restarting`/...) and
  healthcheck status of every container in this compose project, via the
  Docker Engine API. Needs `/var/run/docker.sock` mounted into `perftool`
  (already wired up in `docker-compose.yml`) — **note the `:ro` flag only
  protects the socket *file*, not the API reachable through it**; this
  still grants perftool the same host-level power any container with real
  docker access has. Accepted the same way the rest of this tool already
  is (see "What this tool is not" below): single-operator internal tool,
  not exposed outside the docker network.
- **Time to first byte** — a plain `GET /` against this instance, timed to
  the first response byte only (not full body download) — isolates "the
  backend is slow to respond" from "the response is just big". Uses the
  same internal-service-name substitution the manual scenario runner needs
  by hand (see "Using it" above) automatically, since there's no form here
  for a human to fix it on.
- **Celery workers** — `celery inspect ping`/`active`/`reserved` against
  `BROKER_URL`. Doesn't need geonode's own celery app or task modules
  imported, just the broker. The 3 calls run in parallel
  (`ThreadPoolExecutor`), not sequentially — celery's inspect deliberately
  blocks for the *full* timeout on each one to give every worker a chance
  to reply, so 3 sequential calls made this page take 9.3s to load,
  confirmed live; in parallel it's ~1x timeout instead of 3x.
- **Redis queues** — two numbers: `total_queued` (messages waiting for a
  free worker — a plain Redis list per queue name; a backlog that keeps
  growing means workers can't keep up or are down) and `in_flight`
  (celery's own `unacked` hash — messages already handed to a worker and
  being processed, not yet acked done). Queue names aren't hardcoded
  (geonode routes to ~30 of them and that list changes between versions)
  — scanning for list-type keys finds them without keeping a list in sync
  by hand.

  **Both active/reserved (Celery workers) and total_queued/in_flight
  (Redis queues) are snapshots, not a trace** — confirmed live testing
  against a real CSV upload: a real task chain is many short substeps
  (`import_orchestrator` -> `import_resource` -> `publish_resource` ->
  ...), each often done in under a second with idle workers picking them
  up immediately. Polling all four numbers through the actual upload,
  each one independently read 0 on some polls and non-zero on others for
  the *same* run — Redis deletes an empty queue/unacked entry instantly,
  and celery's active/reserved only reflects the exact instant asked.
  Seeing 0 on this page does not mean nothing ran since the last load; it
  means nothing was in that particular state at the instant this load
  happened. A longer job (a bulk load via `run_full_load_test.py`, a
  large upload) is far more likely to be caught mid-run than one small
  CSV — reload a few times during one, or use a bigger one, rather than
  trusting a single load's zeroes.
- **Disk space** — host disk usage via a read-only `/:/hostfs:ro` mount
  into `perftool` (this container's own `/` is a thin, near-empty overlay
  and wouldn't report anything meaningful on its own).

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
