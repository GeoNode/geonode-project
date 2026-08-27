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

Standard new-style Django middleware (`__init__(self, get_response)` /
`__call__(self, request)`), registered near the end of `MIDDLEWARE` so it
wraps as much of the request/response cycle as possible.

Mechanism, step by step:

1. On `__call__`, if `settings.EXPOSE_DB_QUERY_STATS_HEADER` is falsy, it's
   a pure passthrough (`return self.get_response(request)`) — zero overhead
   when off, not even the wrapper registration.
2. Otherwise it opens `connection.execute_wrapper(wrapper)` as a context
   manager around `self.get_response(request)` — i.e. around the *entire*
   rest of the middleware chain, the view, and every DB call any of that
   code makes (ORM queries, raw SQL, signal handlers that hit the DB,
   anything on Django's default connection). `execute_wrapper` is Django's
   own hook for exactly this: it's called around every `cursor.execute()`/
   `executemany()` on that connection.
3. The `wrapper(execute, sql, params, many, context)` closure times each
   call with `time.monotonic()` (immune to system clock adjustments,
   unlike `time.time()`) and appends the duration to a `queries` list
   local to that one request — a fresh list per call to `__call__`, so
   there's no cross-request leakage or shared state to worry about.
4. After `get_response` returns, it sets
   `response["X-DB-Query-Count"] = len(queries)` and
   `response["X-DB-Query-Time-Ms"] = round(sum(queries) * 1000, 2)` on the
   way back out.

**Why `execute_wrapper()` and not `connection.queries`**: `connection.queries`
only populates when `DEBUG=True` (or `force_debug_cursor`), which nobody
wants flipped on for a perf-comparison run against something
production-like — `DEBUG=True` also changes error pages, template
behavior, and (mildly) performance itself, contaminating the very thing
being measured. `execute_wrapper()` is a hook that runs unconditionally
regardless of `DEBUG`, so counting works on a `DEBUG=False` instance,
which is what you actually want to be measuring.

**Why this middleware is needed at all, given the Postgres-side metrics
(#2/#3) already exist**: those are whole-database counters — anything else
concurrently hitting the same Postgres instance (another user, a celery
beat tick) leaks into the delta, which is why the tool has to fall back to
reporting min/avg/median/max and calling it noise-tolerant rather than
exact. This middleware sidesteps that problem entirely rather than
averaging around it: the count/timing is attributed to *this specific
request's connection usage* during *this specific call to `get_response`*,
so nothing another client does can appear in it. It's the only metric in
the tool that's exact at n=1.

Trade-off for that precision: it's opt-in specifically because exposing
query counts/timings in a response header is information disclosure about
internal implementation to anyone who can see response headers (not
secrets, but still not something to leave on for the general public) —
hence gated behind a setting rather than always-on.

Enable:
```
EXPOSE_DB_QUERY_STATS_HEADER=True
```
(env var, read via `ast.literal_eval` in `geonode/settings.py`, same
pattern GeoNode already uses for other boolean settings). Only ever turn
this on for an instance you're actively perf-testing — restart the
GeoNode process after setting it, same as any other Django setting change.
On the perf_tool side, `GeoNodeClient._record_query_stats()` reads both
headers off every response and `query_stats()` sums them since the last
`reset_query_stats()` call — nothing to configure there, it's automatic
once the header is present.

### `RequestProfilingMiddleware`

Same shape as the middleware above (`__init__`/`__call__`, passthrough
when its setting is off), but instruments the whole request with stdlib
`cProfile` instead of just the DB layer.

Mechanism, step by step:

1. If `settings.EXPOSE_REQUEST_PROFILING` is falsy: passthrough, no
   profiler object even created.
2. Otherwise: `profiler = cProfile.Profile()`, `profiler.enable()`,
   `self.get_response(request)` inside a `try`, `profiler.disable()` in
   `finally` — the `finally` matters, an exception raised inside the view
   still needs the profiler turned back off, or every later request on
   that worker process would be recorded into the same still-running
   profile.
3. `cProfile` (a C-implemented deterministic profiler, not a statistical
   sampler) records every function call/return during that window with
   real counts and timings — everything the view does, every ORM call,
   every template render, every signal handler, down through the standard
   library.
4. The recorded data is fed into `pstats.Stats(profiler, stream=buf)` and
   sorted with `.sort_stats("tottime")`.
5. `stats.print_stats(r"/geonode/", self.TOP_N)` — `pstats`' own regex
   filter argument, applied *before* truncating to the top 15, so the
   top-15 cut is taken from the already-`/geonode/`-filtered set, not from
   the global top 15 with non-matching rows dropped afterward (which would
   often return fewer than 15, or none, on a request dominated by
   framework/driver time).
6. `print_stats` writes its usual human-readable table into the `buf`
   `StringIO`; the first 5 lines (call-count summary, sort-order line,
   column headers) are sliced off, each remaining line is
   whitespace-trimmed, and the leading absolute path on each is trimmed
   down to start at `geonode/` with a regex substitution — cosmetic only,
   done after filtering so it doesn't interfere with the `/geonode/` match.
7. The resulting lines are joined with `" | "` into one
   `X-Profile-Top` header — headers are single-line, so this is the only
   way to carry a multi-row table out of a request/response cycle without
   inventing a side channel (a file, a cache key) for something this
   throwaway.

**Why `tottime` and not `cumtime`**: `cumtime` (cumulative time, including
everything a function calls) on a request profile is dominated by the
outer middleware/dispatch chain — Django's `BaseHandler`, URL resolution,
DRF's `dispatch()` — every wrapper down to the actual view shows almost
the same cumulative number, because they're all on the same call stack
down to the leaf. That just retraces the call graph, it doesn't say where
CPU time is actually spent. `tottime` (self time, excluding sub-calls)
isolates time spent *inside that function's own code*, which is what you'd
actually go edit.

**Why filtered to `/geonode/` paths**: an unfiltered top-15 by self time on
a typical DRF request is dominated by psycopg2 (`cursor.execute`),
Django's ORM internals, and DRF serializer machinery — real time, all
correctly measured, but no application code behind any of those frames to
change. The one place that noise *is* the actual finding — an unindexed
query burning time in the DB driver, a per-row `.reverse()`/property
access in a serializer — still surfaces in this list, just attributed to
whichever geonode call site *triggered* that work, since that's the frame
in the call stack that's inside `/geonode/`. `strip_dirs()` is
deliberately never called on the `pstats.Stats` object — that would
shorten every path to a bare filename before filtering, and the `/geonode/`
regex needs the full path to match against (multiple apps can have a
`views.py`, `models.py`, etc.); the path is trimmed to start at
`geonode/...` only afterward, once filtering no longer needs the prefix.

**Why this middleware is needed at all**: wall time (#1) says *whether*
a scenario got slower; `pg_stat_*`/query-count say whether it's DB-bound.
Neither says *which Python function* to open next. This is the one signal
in the tool that names actual call sites — the profiling equivalent of
`RequestQueryStatsMiddleware`'s "attributed to exactly this request", but
for CPU time instead of query count, and with a call-site name attached
instead of just a number.

Real, non-negligible per-request overhead — cProfile instruments every
single function call/return in the request, which is why it's gated by a
*separate* setting from query-stats rather than folded into the same one:
you may want query counts on a broader perf-testing instance without
paying cProfile's cost on every request.

Enable:
```
EXPOSE_REQUEST_PROFILING=True
```
Never leave this on outside an active profiling session; never in
production — restart the GeoNode process after setting it. On the
perf_tool side, `GeoNodeClient._record_query_stats()` also captures
`X-Profile-Top` (same method handles both headers) into
`self._profile_top`, overwritten on every request rather than accumulated
— unlike query-stats, concatenating separate cProfile runs from multiple
requests in one scenario wouldn't be meaningful, so only the last
request's profile is kept.

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
