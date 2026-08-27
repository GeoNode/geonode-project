## Design goals that shaped every choice below

- **Trustworthy with zero privilege.** Everything must work against the
  same DB role/HTTP surface GeoNode itself uses — no superuser, no
  `ALTER SYSTEM`, no docker log scraping, no code changes required on the
  target instance to get *a* number. Extra precision (`pg_stat_statements`,
  the two middlewares below) is additive and detected at runtime, never a
  hard requirement.
- **Relative over absolute.** Every metric here is inherently noisy at
  n=1 on a shared instance. The tool leans on iteration (min/avg/median/max)
  and before/after comparison rather than presenting one number as ground
  truth.
- **Stack ported wholesale, not reinvented.** This copy is functionally
  identical to the `geonode` core repo's own `perf_tool/` — same
  Flask app, same middlewares, same metric set. Only the deployment
  wiring differs (see `../PERF_TOOL.md`'s nginx section). Keep changes to
  the two in sync unless there's a project-specific reason not to.

## Architecture

Flask app (`app.py`), server-rendered templates, SQLite for run history
(`storage.py`). Three concerns kept in separate modules:

- `geonode_client.py` — thin `requests`-based HTTP client for the target
  GeoNode instance: login/CSRF, one-redirect-only handling, header capture
  for the two middleware-emitted headers.
- `db_stats.py` — Postgres-side before/after snapshot + diff
  (`pg_stat_database`, `pg_stat_user_tables`, optionally
  `pg_stat_statements`).
- `scenarios.py` — the actual GeoNode actions being timed (list resources,
  upload CSV, create map/geoapp, view/copy/edit metadata, custom request).

`_run_once()` in `app.py` is where every metric for one iteration comes
together: reset the client's per-request counters, snapshot Postgres,
run the scenario, snapshot Postgres again, diff, and pull whatever the
client accumulated from response headers during the call(s).

## Metrics, and why each one exists

Four independent signals, deliberately not collapsed into one "score" —
they catch different regressions and have different noise floors.

### 1. Wall time

Measured in the tool itself (`time.time()` around the scenario call),
not derived from any header. For scenarios that trigger the async import
pipeline (CSV upload), the clock includes polling
`/api/v2/resource-service/execution-status/<id>` to a terminal state —
stopping at the initial `201 Accepted` would hide the celery/GeoServer
work that's usually where the actual regression lives.

**Why wall time at all, given the more precise numbers below exist**: it's
the number a user/stakeholder actually experiences. A DB-query-count
improvement that doesn't move wall time isn't done yet (could be GeoServer,
network, or something outside Postgres entirely).

### 2. Postgres-wide counters (`pg_stat_database` / `pg_stat_user_tables`)

The baseline metric — always available, zero setup, zero privilege. Two
views, snapshotted immediately before and immediately after the action on
the *same connection* with `autocommit = True`:

- `pg_stat_database`: `xact_commit`, `xact_rollback`, `tup_returned`,
  `tup_fetched`, `tup_inserted`, `tup_updated`, `tup_deleted` — whole
  database. `xact_commit` delta is the headline number (roughly:
  "how many transactions did this action cause").
- `pg_stat_user_tables`, filtered to `TRACKED_TABLES` in `db_stats.py`
  (`base_resourcebase`, `layers_dataset`, `guardian_userobjectpermission`,
  etc.) — `seq_scan`/`idx_scan`/`n_tup_ins`/`n_tup_upd`/`n_tup_del` per
  table. `seq_scan` deltas on a table that should be hitting an index are
  usually the actual finding.

**Why `conn.autocommit = True` specifically**: PG15+'s
`stats_fetch_consistency` defaults to `cache` — within one transaction,
repeated reads of a `pg_stat_*` view return the *same* cached snapshot.
Taking before/after snapshots on the same non-autocommit connection would
silently diff to zero every time (each read within the implicit
transaction hits the same cache). Autocommit forces a fresh read each time.

**Why `TRACKED_TABLES` is a fixed allowlist, not `SELECT * FROM
pg_stat_user_tables`**: it's the list of tables that actually moved during
the manual investigation this tool grew out of (upload pipeline, map/geoapp
creation, permission writes). Diffing every table in the schema would bury
the signal in tables no scenario here touches. Extend the list when
chasing something new, not by default.

**The honest limitation, stated plainly in the UI and the PDF report**:
these are whole-database counters, not scoped to one HTTP request. Any
concurrent activity on the same Postgres instance (another user, a celery
beat tick, a concurrent test run) leaks into the delta. This is why the
tool reports min/avg/median/max over N iterations rather than a single
number, and why it's positioned as *relative* (before-fix vs after-fix)
rather than an absolute truth. Run against a quiet instance when precision
actually matters.

### 3. `pg_stat_statements` (optional, auto-detected)

If the extension is installed **and** the role running the tool can read
it, `db_stats.snapshot()` also captures `queryid`/`query`/`calls`/
`total_exec_time` from `pg_stat_statements`, diffs by `queryid`, and
surfaces the top 30 by call-count delta. This is the only metric here that
shows *actual SQL text* — genuinely diagnostic when a scenario runs an
N+1 query pattern, since the repeated query's text and per-call count show
up directly instead of being inferred from `seq_scan` counts.

Detected at snapshot time (`pg_stat_statements_available()` — checks the
extension is installed and a `SELECT 1 FROM pg_stat_statements` doesn't
error); the tool falls back to the table-level counters alone, silently,
if it's missing. Setup is a `shared_preload_libraries` flag on the `db`
service (postmaster-context, needs a restart — see `../PERF_TOOL.md`) plus
a one-time `CREATE EXTENSION`.

Same whole-database caveat as above applies — the query rows are filtered
to the target database (`JOIN pg_database ... WHERE d.datname = %s`) and
the tool's own `pg_stat_statements` lookup query is excluded, but another
concurrent client's queries on the same DB still show up.

### 4. Request-scoped query stats (`X-DB-Query-Count`/`X-DB-Query-Time-Ms`)

The zero-noise counterpart to #2/#3 — genuinely scoped to exactly the one
HTTP request that produced it, immune to concurrent-activity noise by
construction. Requires the target GeoNode to have
`RequestQueryStatsMiddleware` enabled (see below); shows as `0`/`0` in the
UI otherwise, same graceful-degradation pattern as `pg_stat_statements`.

`GeoNodeClient` accumulates this across every HTTP call made since the
last `reset_query_stats()` (a scenario often makes several requests —
login is excluded, the scenario body isn't), so the per-iteration number
in `_run_once()` reflects the whole scenario, not just its last call.

### 5. Per-request profiling top functions (`X-Profile-Top`)

The most targeted signal: which *GeoNode* functions actually burned CPU
time during one request, self-time only. Requires
`RequestProfilingMiddleware` enabled; empty string otherwise. Unlike
query-stats, this isn't summed across a scenario's multiple requests —
`GeoNodeClient.profile_top()` only keeps the last response's header,
since concatenating separate cProfile runs isn't meaningful. Good for
"which HTTP call in this scenario is the slow one" once wall time and
query count have already pointed at a scenario worth digging into.

## The two GeoNode-side middlewares

Both live in `geonode/base/middleware.py` in the `geonode` core repo (not
in this project — see the base-image caveat below). Both are opt-in via
settings, off by default, and both degrade the tool gracefully to "0"/
empty rather than erroring when absent — the tool never assumes they're
present.

### `RequestQueryStatsMiddleware`

Wraps the request in `connection.execute_wrapper()`, timing every SQL
statement Django/psycopg2 executes for that request, and sets two response
headers: `X-DB-Query-Count`, `X-DB-Query-Time-Ms`.

**Why `execute_wrapper()` and not `connection.queries`**: `connection.queries`
only populates when `DEBUG=True` (or `force_debug_cursor`), which nobody
wants flipped on for a perf-comparison run against something
production-like. `execute_wrapper()` is a hook that runs unconditionally,
so this works with `DEBUG=False`.

**Why this exists at all given #2/#3 above**: it's the one number in the
whole tool immune to "something else was hitting the DB at the same time"
noise, by construction rather than by averaging it away. Trade-off: it's
opt-in and reveals internal query volume to anyone who can see response
headers, so it's gated behind a setting rather than always-on.

Enable:
```
EXPOSE_DB_QUERY_STATS_HEADER=True
```
(env var, read via `ast.literal_eval` in `geonode/settings.py`). Only ever
turn this on for an instance you're actively perf-testing.

### `RequestProfilingMiddleware`

Wraps the request in stdlib `cProfile`, then uses `pstats` to extract the
top N (15) functions by **self time** (`tottime`, not `cumtime`) whose
file path contains `/geonode/`, joined with `|` into `X-Profile-Top`
(header values can't carry newlines).

**Why `tottime` and not `cumtime`**: `cumtime` on a request profile is
dominated by the outer middleware/dispatch chain — every wrapper down to
the view shows almost the same cumulative number, which just retraces the
call stack rather than pointing at where time is actually spent.
`tottime` isolates time spent *in that function itself*.

**Why filtered to `/geonode/` paths**: an unfiltered top-N by self time is
dominated by psycopg2/Django/DRF internals — real time, but no app code
behind it to change. The one place that noise *is* the finding (an
unindexed query showing up as time spent in the DB driver, a per-row
`reverse()` call) still surfaces here, just attributed to the geonode call
site that triggered it rather than the library frame that happened to
burn the cycles. `strip_dirs()` is deliberately not called before the
filter — the regex needs the full path to match against, not just the
bare filename; the path gets trimmed down to `geonode/...` afterward,
once filtering no longer needs it.

Real per-request overhead — cProfile instruments every function call.
Gated separately from query-stats since it's the more expensive of the
two.

Enable:
```
EXPOSE_REQUEST_PROFILING=True
```
Never leave this on outside an active profiling session; never in
production.

### Why both middlewares are opt-in via env var, not always-on

Same reasoning as the `pg_stat_statements` detection: precise but
sensitive/expensive, so it's a deliberate choice per-instance rather than
a default. The tool treats "middleware present" and "middleware absent"
as two equally valid states — `_run_once()`/`_aggregate()` in `app.py`
use `.get(..., default)` throughout specifically so old saved runs
(before a field existed) and instances without the middleware on don't
break rendering.

### Base-image limitation for this project specifically

This project's `Dockerfile` builds `FROM
geonode/geonode-base:${GEONODE_BASE_IMAGE_VERSION}` — a prebuilt image
with the released `geonode` package already installed — rather than
vendoring GeoNode's source tree the way the `geonode` core repo does. Both
middlewares live in that source tree (`geonode/base/middleware.py`), so
there's currently nothing to enable here: the "DB queries (this request
only)" card and the profiling tab will show `0`/empty until a
`geonode-base` image built from a GeoNode version containing them is
published, or this project switches to building from source (a bigger,
separate decision, not a side effect of this tool). The tool detects this
the same way it detects a missing `pg_stat_statements` and degrades
cleanly — nothing else breaks.

## Client-side quirks worth knowing before touching `geonode_client.py`

Not metrics, but affect whether the metrics above get produced at all —
a failed request obviously can't carry the response headers being
measured:

- Requests always send an explicit `Host: localhost` header regardless of
  the URL's own hostname — this sandbox's nginx `server_name` only matches
  `localhost`/`127.0.0.1`; a bare service-name Host falls through to
  `default_server` and the connection drops.
- Cookies are stripped of the `Secure` flag right after being set
  (`_unsecure_cookies()`). GeoNode marks session/CSRF cookies `Secure`
  (correct for a TLS-terminating production nginx); this tool talks plain
  HTTP inside the compose network, so `requests` would otherwise silently
  refuse to send them back — anonymous GETs looked fine, anything
  requiring auth 401'd with no obvious cause.
- Exactly one redirect is followed manually, preserving method and body
  (`_request()`), instead of relying on `requests`' default redirect
  handling — which downgrades PUT/POST to GET on a 302, breaking
  i18n-prefix redirects like `PUT /api/v2/resources/<pk>/copy`.

## Metrics deliberately not included

- **No load/concurrency testing** (virtual users, RPS). One action at a
  time by design — this tool answers "is this action faster than before",
  not "how does this endpoint behave under load". A different tool for a
  different question.
- **No replacement for `assertNumQueries`.** That's a CI-time regression
  gate on a known query count; this is a runtime measurement against a
  real instance, useful for "did the fix actually help" in a way a static
  assertion in a test can't answer.
