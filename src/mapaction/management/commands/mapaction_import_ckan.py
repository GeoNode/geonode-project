"""Load maps from the local CKAN mirror (data/ckan, made by data/scripts/mirror_ckan.py).

  mapaction_import_ckan --mirror data/ckan --emergency 2026-mdg-001            # dry run: quality report only
  mapaction_import_ckan --mirror data/ckan --emergency 2026-mdg-001 --apply
  mapaction_import_ckan --mirror data/ckan --package 2026-mdg-001-ma004-v1 --package 2026-mdg-001-ma004-v2 --apply
"""
import csv
import json
import zlib
import pathlib

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from mapaction import extract, services


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--mirror", required=True, help="the data/ckan directory")
        parser.add_argument("--emergency", action="append", default=[], help="CKAN event code; repeatable")
        parser.add_argument("--package", action="append", default=[], help="CKAN package name; repeatable")
        parser.add_argument("--map-number", action="append", default=[], help="e.g. MA110; repeatable (with --emergency)")
        parser.add_argument("--no-emergency", action="store_true", help="only records with no CKAN emergency")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--shard", help="i/n: only this share of the emergencies (run n processes in parallel)")
        parser.add_argument("--apply", action="store_true", help="really load; default is a dry run")
        parser.add_argument("--report", help="write a CSV quality report here")
        parser.add_argument("--user", help="who is running the load (kept for staff only)")

    def handle(self, **o):
        root = pathlib.Path(o["mirror"])
        catalog = root / "catalog" / "packages.jsonl"
        if not catalog.exists():
            raise CommandError(f"{catalog} not found")
        loaded_by = get_user_model().objects.filter(username=o["user"]).first() if o["user"] else None
        pkgs = []
        for line in catalog.open():
            pkg = json.loads(line)
            groups = {g.get("name") for g in pkg.get("groups") or []}
            if o["package"] and pkg["name"] not in o["package"]:
                continue
            if o["emergency"] and not groups.intersection(o["emergency"]):
                continue
            if o["no_emergency"] and any(g.get("type") == "event" for g in pkg.get("groups") or []):
                continue
            if o["map_number"]:
                mn = next((str(e.get("value", "")).strip().upper() for e in pkg.get("extras") or [] if str(e.get("key", "")).strip() == "mapNumber"), "")
                if mn not in {m.upper() for m in o["map_number"]}:
                    continue
            pkgs.append(pkg)
        if o["shard"]:
            i, n = (int(x) for x in o["shard"].split("/"))
            # Whole emergencies per shard, so every version of a map is loaded by one process, in order
            key = lambda p: next((g["name"] for g in p.get("groups") or [] if g.get("type") == "event"), p["name"])
            pkgs = [p for p in pkgs if zlib.crc32(key(p).encode()) % n == i]
        # Versions in order, so each new one links to the one before
        pkgs.sort(key=lambda p: (p["name"].rsplit("-v", 1)[0], int(p.get("version") or 0) if str(p.get("version") or "0").isdigit() else 0))
        if o["limit"]:
            pkgs = pkgs[: o["limit"]]

        rows, counts = [], {}
        for pkg in pkgs:
            p = extract.from_ckan(pkg, root)
            try:
                mv, action = services.publish(p, loaded_by=loaded_by, dry_run=not o["apply"])
            except Exception as e:  # report and carry on: one bad record must not stop a migration
                mv, action = None, f"error: {e}"
            counts[action.split(":")[0]] = counts.get(action.split(":")[0], 0) + 1
            self.stdout.write(f"{action:<12} {p.source_id:<40} {p.display_title[:70]}")
            for w in p.warnings:
                self.stdout.write(f"{'':12} note: {w}")
            rows.append({"package": p.source_id, "action": action, "record": mv.resource_id if mv else "",
                         "emergency": p.emergency_code, "map_number": p.map_number, "version": p.version,
                         "public": p.is_public, "files": len(p.files), "countries": "; ".join(p.countries),
                         "themes": "; ".join(p.themes), "product_type": p.product_type, "languages": "; ".join(p.languages),
                         "has_extent": bool(p.bbox), "warnings": " | ".join(p.warnings)})
        if o["report"] and rows:
            with open(o["report"], "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
        self.stdout.write(f"\n{len(pkgs)} packages: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                          + ("" if o["apply"] else "  (dry run: nothing written)"))
