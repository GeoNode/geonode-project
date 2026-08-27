"""
perf_tool — a small, self-contained webapp for measuring GeoNode performance
the same trustworthy way it was done by hand during the investigation this
tool grew out of: time an HTTP action end to end, and diff Postgres's own
pg_stat_database / pg_stat_user_tables counters around it instead of guessing.

Deliberately not fancy: Flask, server-rendered HTML, SQLite for run history.
See PERF_TOOL.md for how to use it.
"""
import json
import math
import os
import re
import statistics
import time
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request, url_for
from fpdf import FPDF
from werkzeug.middleware.proxy_fix import ProxyFix

import db_stats
import storage
from geonode_client import GeoNodeClient, LoginError
from scenarios import SCENARIOS, lookup_resources

app = Flask(__name__)
# Trust nginx's X-Forwarded-* headers (needed when this sits behind
# nginx at a path like /performance/, not just on its own port).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


@app.template_filter("datetime")
def _format_datetime(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


# Default the base URL to this instance's own configured SITEURL — the same
# env var GeoNode itself uses — rather than assuming an internal service
# name that may or may not exist/resolve/match the TLS cert on any given
# deployment. GEONODE_BASE_URL still wins if explicitly set (e.g. to force
# an internal name on purpose).
DEFAULT_BASE_URL = os.environ.get("GEONODE_BASE_URL") or os.environ.get("SITEURL", "http://nginx").rstrip("/")

# The Host-header-override quirk (see geonode_client.py) is specific to this
# sandbox's nginx, which only matches server_name "localhost"/"127.0.0.1" —
# so only default it to "localhost" when the base URL actually points there.
# Any other target (a real domain via SITEURL, a different internal name)
# defaults to no override, since a real deployment's nginx generally doesn't
# need one and a wrong guess here just reproduces the original bug.
_default_base_host = urlparse(DEFAULT_BASE_URL).hostname or ""
DEFAULT_HOST_HEADER = os.environ.get(
    "GEONODE_HOST_HEADER", "localhost" if _default_base_host in ("localhost", "127.0.0.1") else ""
)


def _run_once(client, conn, scenario_key, params):
    scenario_fn = SCENARIOS[scenario_key]["fn"]
    client.reset_query_stats()
    before = db_stats.snapshot(conn)
    t0 = time.time()
    try:
        result = scenario_fn(client, params)
    except Exception as e:
        # Full traceback server-side only — the response/report only ever
        # gets the generic type/message, never a raw exception dump.
        app.logger.exception("scenario '%s' raised (params=%s)", scenario_key, params)
        result = {"ok": False, "http_status": None, "detail": f"{type(e).__name__}: {e}"}
    wall_time = time.time() - t0
    after = db_stats.snapshot(conn)
    delta = db_stats.diff(before, after)
    return {
        "wall_time": round(wall_time, 3),
        "ok": result.get("ok", False),
        "http_status": result.get("http_status"),
        "detail": result.get("detail", ""),
        "db": delta,
        # request-scoped, zero-noise — see geonode.base.middleware.
        # RequestQueryStatsMiddleware. {"count": 0, "time_ms": 0} when the
        # target instance doesn't have EXPOSE_DB_QUERY_STATS_HEADER on.
        "request_db": client.query_stats(),
        # cProfile's slowest functions for this iteration's last HTTP call —
        # see geonode.base.middleware.RequestProfilingMiddleware. Empty
        # string when the target instance doesn't have
        # EXPOSE_REQUEST_PROFILING on.
        "profile_top": client.profile_top(),
    }


def _stats(values, ndigits=3):
    """min/avg/median/stdev/max for one metric across iterations. stdev is
    0 when there's only one value (statistics.stdev needs >=2 and a single
    run can't say anything about run-to-run noise anyway) — callers should
    treat a 0 stdev from a single-iteration run as "unknown", not "no
    noise". None (not an empty dict) when there are no values at all, so
    templates can tell "no data" apart from "all zeros"."""
    if not values:
        return None
    return {
        "min": round(min(values), ndigits),
        "avg": round(statistics.mean(values), ndigits),
        "median": round(statistics.median(values), ndigits),
        "stdev": round(statistics.stdev(values), ndigits) if len(values) > 1 else 0.0,
        "max": round(max(values), ndigits),
        "count": len(values),
    }


def _aggregate(iterations):
    times = [it["wall_time"] for it in iterations]
    ok_times = [it["wall_time"] for it in iterations if it["ok"]]
    commits = [it["db"]["db"].get("xact_commit", 0) for it in iterations]
    # .get() with a default: runs saved before this field existed won't have it
    req_counts = [it.get("request_db", {}).get("count", 0) for it in iterations]
    req_times = [it.get("request_db", {}).get("time_ms", 0) for it in iterations]
    return {
        "count": len(iterations),
        "ok_count": sum(1 for it in iterations if it["ok"]),
        # every iteration, successes and failures alike — a fast-failing
        # 4xx pulls this down just as much as a slow success pulls it up.
        # Check ok_count/count before trusting this in isolation.
        "wall_time": _stats(times, 3),
        # same metric, successful iterations only — None when nothing
        # succeeded. This is usually the number you actually want.
        "wall_time_ok": _stats(ok_times, 3),
        "xact_commit": _stats(commits, 1),
        "request_query_count": _stats(req_counts, 1),
        "request_query_time_ms": _stats(req_times, 2),
    }


def _aggregate_stat_statements(iterations, top_n=30):
    """Sum pg_stat_statements calls/time across every iteration, keyed by
    query text (queryid isn't preserved past db_stats.diff()). Replaces
    showing only the last iteration's snapshot — a query that ran on every
    iteration but wasn't the very last one used to disappear entirely."""
    totals = {}
    for it in iterations:
        for row in it["db"].get("stat_statements") or []:
            bucket = totals.setdefault(row["query"], {"query": row["query"], "calls": 0, "total_time_ms": 0.0})
            bucket["calls"] += row["calls"]
            bucket["total_time_ms"] += row["total_time_ms"]
    if not totals:
        return None
    rows = sorted(totals.values(), key=lambda r: r["calls"], reverse=True)[:top_n]
    for row in rows:
        row["total_time_ms"] = round(row["total_time_ms"], 2)
    return rows


# One line of pstats.print_stats() output, post-processing already applied
# by RequestProfilingMiddleware (leading path trimmed to "geonode/..."):
#   ncalls  tottime  percall  cumtime  percall  geonode/mod.py:12(func)
# ncalls can read "3/1" for recursive calls — only the primary (left) count
# is summed here, matching what a plain call-count would mean to a reader.
_PSTATS_LINE_RE = re.compile(
    r"^(?P<ncalls>\d+(?:/\d+)?)\s+(?P<tottime>[\d.]+)\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+(?P<func>.+)$"
)


def _aggregate_profile_top(iterations, top_n=15):
    """Sum cProfile self-time (tottime) per function across every iteration
    that has an X-Profile-Top header, instead of showing only the last
    iteration's profile — a function that's consistently hot across the
    run but wasn't the slowest specifically on the final iteration used to
    never surface."""
    totals = {}
    for it in iterations:
        profile_top = it.get("profile_top") or ""
        for line in profile_top.split(" | "):
            m = _PSTATS_LINE_RE.match(line.strip())
            if not m:
                continue
            func = m.group("func")
            bucket = totals.setdefault(func, {"func": func, "ncalls": 0, "tottime": 0.0})
            bucket["ncalls"] += int(m.group("ncalls").split("/")[0])
            bucket["tottime"] += float(m.group("tottime"))
    if not totals:
        return None
    rows = sorted(totals.values(), key=lambda r: r["tottime"], reverse=True)[:top_n]
    for row in rows:
        row["tottime"] = round(row["tottime"], 4)
    return rows


def _within_noise(agg_a, agg_b, metric):
    """None: can't judge (either run has <2 iterations, so its stdev is
    unknown rather than genuinely zero). True: the two averages differ by
    less than the combined stdev of both runs — plausibly just run-to-run
    noise, not a real change. False: the difference exceeds that band."""
    a, b = agg_a.get(metric), agg_b.get(metric)
    if not a or not b or a["count"] < 2 or b["count"] < 2:
        return None
    combined_stdev = math.sqrt(a["stdev"] ** 2 + b["stdev"] ** 2)
    return abs(b["avg"] - a["avg"]) <= combined_stdev


@app.route("/api/lookup/resources", methods=["POST"])
def api_lookup_resources():
    """Real resources already in the target instance, for the picker in the
    UI — so scenarios like "copy" or "view metadata" exercise something real
    instead of only ever creating fresh synthetic ones."""
    data = request.get_json(force=True)
    base_url = data.get("base_url") or DEFAULT_BASE_URL
    host_header = data.get("host_header", DEFAULT_HOST_HEADER)
    verify_tls = not data.get("skip_tls_verify")
    client = GeoNodeClient(base_url, host_header=host_header, verify_tls=verify_tls)
    try:
        client.login(data["username"], data["password"])
        resources = lookup_resources(client, limit=int(data.get("limit", 50)))
    except LoginError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 502
    return jsonify({"resources": resources})


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.route("/")
def index():
    return render_template(
        "index.html",
        scenarios=SCENARIOS,
        default_base_url=DEFAULT_BASE_URL,
        default_host_header=DEFAULT_HOST_HEADER,
    )


@app.route("/run", methods=["POST"])
def run():
    scenario_key = request.form["scenario"]
    if scenario_key not in SCENARIOS:
        return f"Unknown scenario: {scenario_key}", 400

    base_url = request.form.get("base_url") or DEFAULT_BASE_URL
    host_header = request.form.get("host_header", DEFAULT_HOST_HEADER)
    verify_tls = not request.form.get("skip_tls_verify")
    username = request.form["username"]
    password = request.form["password"]
    iterations_n = max(1, min(int(request.form.get("iterations", 1)), 50))
    warmup_n = max(0, min(int(request.form.get("warmup_iterations", 0) or 0), 20))
    label = request.form.get("label", "")

    params = {}
    for key, value in request.form.items():
        if key.startswith("param_") and value != "":
            params[key[len("param_") :]] = value
    if params.get("body"):
        try:
            params["body"] = json.loads(params["body"])
        except json.JSONDecodeError as e:
            return f"Invalid JSON in body field: {e}", 400

    uploaded_file = request.files.get("file")
    tmp_upload_path = None
    if uploaded_file and uploaded_file.filename:
        tmp_upload_path = f"/tmp/perftool_upload_{int(time.time())}_{uploaded_file.filename}"
        uploaded_file.save(tmp_upload_path)
        params["uploaded_file_path"] = tmp_upload_path

    client = GeoNodeClient(base_url, host_header=host_header, verify_tls=verify_tls)
    try:
        client.login(username, password)
    except LoginError as e:
        return render_template("error.html", message=str(e)), 400

    conn = db_stats.get_connection()
    try:
        # Discarded on purpose: cold Django/GeoServer/DB-plan caches on the
        # very first hit otherwise skew iteration 1 (and therefore the
        # min/avg) in a way that has nothing to do with the code being
        # measured. Not counted, not saved — same scenario/params, run and
        # thrown away before the timed iterations start.
        for _ in range(warmup_n):
            _run_once(client, conn, scenario_key, params)
        iterations = [_run_once(client, conn, scenario_key, params) for _ in range(iterations_n)]
    finally:
        conn.close()
        if tmp_upload_path and os.path.exists(tmp_upload_path):
            os.unlink(tmp_upload_path)

    saved_params = {k: v for k, v in params.items() if k != "uploaded_file_path"}
    if warmup_n:
        # kept only as a visible note on the run, not fed into any metric
        saved_params["_warmup_iterations_discarded"] = warmup_n
    run_id = storage.save_run(scenario_key, saved_params, iterations, label=label)
    return redirect(url_for("show_run", run_id=run_id))


def _table_totals(iterations):
    """Sum per-table deltas across every iteration of a run."""
    totals = {}
    for it in iterations:
        for table, delta in it["db"]["tables"].items():
            bucket = totals.setdefault(table, {"seq_scan": 0, "idx_scan": 0, "n_tup_ins": 0, "n_tup_upd": 0, "n_tup_del": 0})
            for key, value in delta.items():
                bucket[key] += value
    return dict(sorted(totals.items(), key=lambda kv: sum(kv[1].values()), reverse=True))


def _run_context(run_id):
    run_data = storage.get_run(run_id)
    if not run_data:
        return None
    aggregate = _aggregate(run_data["iterations"])
    return {
        "run": run_data,
        "aggregate": aggregate,
        "table_totals": _table_totals(run_data["iterations"]),
        # summed across every iteration, not just the last one — see
        # _aggregate_stat_statements/_aggregate_profile_top docstrings.
        "stat_statements": _aggregate_stat_statements(run_data["iterations"]),
        "profile_top": _aggregate_profile_top(run_data["iterations"]),
        "scenario_label": SCENARIOS.get(run_data["scenario"], {}).get("label", run_data["scenario"]),
    }


@app.route("/run/<int:run_id>")
def show_run(run_id):
    ctx = _run_context(run_id)
    if not ctx:
        return "Run not found", 404
    return render_template("result.html", **ctx)


def _build_report_text(ctx):
    run = ctx["run"]
    agg = ctx["aggregate"]
    lines = []
    w = lines.append
    w(f"perf_tool report — run #{run['id']}")
    w("=" * 60)
    w(f"Scenario:   {ctx['scenario_label']}")
    w(f"Label:      {run['label'] or '(none)'}")
    w(f"When:       {_format_datetime(run['created_at'])}")
    w(f"Params:     {run['params']}")
    w(f"Iterations: {len(run['iterations'])}")
    w("")
    w("HOW THESE NUMBERS ARE CALCULATED")
    w("-" * 60)
    w(
        "Wall time: measured in the tool itself, wrapped directly around the\n"
        "HTTP call(s) that make up the scenario (for an upload, this includes\n"
        "polling /api/v2/resource-service/execution-status/<id> until the\n"
        "async pipeline reports finished/failed — the clock doesn't stop at\n"
        "the initial 201 Accepted)."
    )
    w("")
    w(
        "DB statements (xact_commit delta): a snapshot of Postgres's own\n"
        "pg_stat_database.xact_commit counter is taken immediately before and\n"
        "immediately after the action, on the same connection with autocommit\n"
        "on (so each snapshot is fresh, not reused from a cached transaction\n"
        "view). The delta is the number of transactions Postgres committed\n"
        "while the action ran. This is a whole-database counter, not scoped to\n"
        "this one request — if anything else was hitting this Postgres\n"
        "instance at the same time (another user, a celery beat tick), it's\n"
        "included in the delta too. That's why this report shows min/avg/\n"
        "median/max across iterations rather than a single number: one\n"
        "iteration can be noise, several iterations are a measurement."
    )
    w("")
    w(
        f"This report shows averages only. The full per-iteration detail,\n"
        f"per-table read/write breakdown, and (if pg_stat_statements is\n"
        f"available) exact top-query text live on the web page for this run:\n"
        f"/run/{run['id']}"
    )
    w("")
    w("AVERAGE RESULTS")
    w("-" * 60)
    w(
        f"Average wall time:       {agg['wall_time']['avg']} s   (stdev {agg['wall_time']['stdev']} s, "
        f"over {agg['count']} run(s), {agg['ok_count']} successful)"
    )
    if agg["wall_time_ok"] and agg["ok_count"] < agg["count"]:
        w(f"  ...successful-only:    {agg['wall_time_ok']['avg']} s   (over {agg['ok_count']} run(s))")
    w(
        f"Average xact_commit Δ:   {agg['xact_commit']['avg']}   (stdev {agg['xact_commit']['stdev']}, "
        f"over {agg['count']} run(s))  [whole-database]"
    )
    if agg["request_query_count"]["max"] > 0:
        w(
            f"Average DB queries:      {agg['request_query_count']['avg']}   "
            f"({agg['request_query_time_ms']['avg']} ms)   [this request only, no noise]"
        )
    w("")
    w(
        f"For context — min {agg['wall_time']['min']}s / median {agg['wall_time']['median']}s / "
        f"max {agg['wall_time']['max']}s wall time,"
    )
    w(
        f"min {agg['xact_commit']['min']} / median {agg['xact_commit']['median']} / "
        f"max {agg['xact_commit']['max']} xact_commit delta."
    )
    w(f"Success rate: {agg['ok_count']} / {agg['count']}")
    return "\n".join(lines) + "\n"


def _build_report_pdf(ctx):
    """Same report content as _build_report_text, laid out as a PDF.
    Monospace throughout (it's a data report, not a document) with section
    headers bolded — no need for more design than that."""
    text = _build_report_text(ctx)
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    for line in text.split("\n"):
        # core PDF fonts (Courier included) are latin-1 only — the report
        # text uses a few unicode punctuation marks (em dashes), swap them
        # for plain-ASCII equivalents rather than bundling a unicode font
        # just for this
        line = line.replace("—", "-").encode("latin-1", "replace").decode("latin-1")
        # raw SQL text from pg_stat_statements can run to hundreds of chars
        # (wide column lists) — full text belongs in the DB, not a page-per-
        # query PDF, so cap what's shown here
        if len(line) > 220:
            line = line[:220] + " ..."
        is_rule = set(line) <= {"=", "-"} and len(line) > 10
        is_header = line.isupper() and line.strip() and not is_rule
        if is_rule:
            continue
        pdf.set_font("Courier", "B" if is_header else "", 14 if line.startswith("perf_tool report") else 9)
        pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


@app.route("/run/<int:run_id>/report")
def download_report(run_id):
    ctx = _run_context(run_id)
    if not ctx:
        return "Run not found", 404
    pdf_bytes = _build_report_pdf(ctx)
    return app.response_class(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=perftool_run_{run_id}_report.pdf"},
    )


@app.route("/history")
def history():
    runs = storage.list_runs()
    for r in runs:
        r["aggregate"] = _aggregate(r["iterations"])
        r["scenario_label"] = SCENARIOS.get(r["scenario"], {}).get("label", r["scenario"])
    return render_template("history.html", runs=runs)


@app.route("/history/delete-all", methods=["POST"])
def delete_all_history():
    storage.delete_all_runs()
    return redirect(url_for("history"))


@app.route("/compare")
def compare():
    a_id = request.args.get("a", type=int)
    b_id = request.args.get("b", type=int)
    if not a_id or not b_id:
        return redirect(url_for("history"))
    run_a = storage.get_run(a_id)
    run_b = storage.get_run(b_id)
    if not run_a or not run_b:
        return "Run not found", 404
    agg_a = _aggregate(run_a["iterations"])
    agg_b = _aggregate(run_b["iterations"])
    return render_template(
        "compare.html",
        run_a=run_a,
        run_b=run_b,
        agg_a=agg_a,
        agg_b=agg_b,
        wall_time_within_noise=_within_noise(agg_a, agg_b, "wall_time"),
        xact_commit_within_noise=_within_noise(agg_a, agg_b, "xact_commit"),
        totals_a=_table_totals(run_a["iterations"]),
        totals_b=_table_totals(run_b["iterations"]),
        scenario_label_a=SCENARIOS.get(run_a["scenario"], {}).get("label", run_a["scenario"]),
        scenario_label_b=SCENARIOS.get(run_b["scenario"], {}).get("label", run_b["scenario"]),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
