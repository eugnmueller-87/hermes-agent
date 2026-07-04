#!/usr/bin/env python3
"""export_brain.py — dump Hermes' supplier intelligence for the AI Brain to ingest.

Hermes owns the supplier library; the Brain is a downstream reader. This script is the
hand-off: it writes ONE self-contained JSON snapshot (catalog + per-supplier profiles +
recent live signals) that the Brain's `sync-hermes-suppliers` skill distills into
`wiki/suppliers/`. No Redis credentials ever leave Hermes — the Brain reads the file only.

Run:  python export_brain.py [--out PATH] [--signals-per-supplier N] [--catalog-only]

Degrades gracefully: if Redis (Upstash) is unreachable or unconfigured, it still emits
the static catalog from config/suppliers.py so the Brain always gets *something* true.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Force UTF-8 stdout on Windows so supplier names with accents don't crash the pipe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9_]", "_", name.lower())


def load_catalog() -> dict:
    """The static watchlist — always available, no network needed."""
    try:
        from config.suppliers import SUPPLIERS
    except Exception as e:
        print(f"WARN: could not import config.suppliers ({e})", file=sys.stderr)
        return {}
    catalog = {}
    for category, companies in SUPPLIERS.items():
        for s in companies:
            slug = _slug(s["name"])
            catalog[slug] = {
                "slug": slug,
                "name": s["name"],
                "category": category,
                "tier": s.get("tier", 0),
                "ticker": s.get("ticker"),
                "rss": s.get("rss"),
            }
    return catalog


def load_live(catalog: dict, signals_per_supplier: int) -> tuple[dict, list, dict]:
    """Read persistent profiles + recent signals from Redis. Returns (profiles, signals, meta).
    Never raises — on any failure returns empty live data so the catalog still ships."""
    profiles, signals = {}, []
    meta = {"redis": "unavailable", "total_items": 0, "significant_items": 0}
    try:
        from storage.redis_store import RedisStore

        store = RedisStore()
        meta["redis"] = "connected"
        meta["total_items"] = store.count_items()

        # Persistent per-supplier profiles are the spine of the library.
        for slug in store.list_profile_slugs():
            p = store.get_profile(slug)
            if p:
                profiles[slug] = p

        # Recent significant signals — the live intelligence layer (timeline material).
        sig = store.get_significant_items(limit=200)
        meta["significant_items"] = len(sig)
        for it in sig:
            signals.append(
                {
                    "supplier": it.get("supplier", ""),
                    "category": it.get("category", ""),
                    "title": it.get("title", ""),
                    "url": it.get("url") or it.get("link", ""),
                    "source": it.get("source", ""),
                    "published": it.get("published", ""),
                    "signal_type": it.get("signal_type", ""),
                    "urgency": it.get("urgency", ""),
                    "significance_reason": it.get("significance_reason", ""),
                    "procurement_angle": it.get("procurement_angle", ""),
                    "_from": "item",
                }
            )

        # Fallback: signal ITEMS have a 7-day TTL, but each PROFILE keeps its last ~10
        # recent_signals permanently (no TTL). When Hermes hasn't crawled recently the
        # items are gone but the profile-embedded summaries survive — use those so the
        # Brain still gets the latest known intelligence per supplier.
        seen_titles = {(s["supplier"], s["title"]) for s in signals}
        for slug, p in profiles.items():
            for rs in p.get("recent_signals", []):
                key = (p.get("name", ""), rs.get("title", ""))
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                signals.append(
                    {
                        "supplier": p.get("name", ""),
                        "category": p.get("category", ""),
                        "title": rs.get("title", ""),
                        "url": rs.get("url", ""),
                        "source": rs.get("source", ""),
                        "published": rs.get("published", ""),
                        "signal_type": rs.get("signal_type", ""),
                        "urgency": rs.get("urgency", ""),
                        "significance_reason": "",
                        "procurement_angle": "",
                        "_from": "profile",
                    }
                )
        meta["signals_from_profiles"] = sum(1 for s in signals if s.get("_from") == "profile")
    except KeyError as e:
        print(f"WARN: Redis env not set ({e}) — catalog-only export.", file=sys.stderr)
    except Exception as e:
        print(f"WARN: Redis read failed ({e}) — catalog-only export.", file=sys.stderr)
    return profiles, signals, meta


def build_snapshot(signals_per_supplier: int, catalog_only: bool) -> dict:
    catalog = load_catalog()
    if catalog_only:
        profiles, signals, meta = {}, [], {"redis": "skipped (catalog-only)"}
    else:
        profiles, signals, meta = load_live(catalog, signals_per_supplier)

    # Timestamp is passed in by the caller-free clock here; the Brain re-stamps on ingest.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "source": "hermes-agent",
        "exported_at": now,
        "meta": meta,
        "catalog": list(catalog.values()),
        "profiles": profiles,
        "signals": signals,
        "counts": {
            "catalog": len(catalog),
            "profiles": len(profiles),
            "signals": len(signals),
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Export Hermes supplier intelligence for the AI Brain.")
    ap.add_argument("--out", default="", help="Write JSON here instead of stdout.")
    ap.add_argument("--signals-per-supplier", type=int, default=10)
    ap.add_argument("--catalog-only", action="store_true", help="Skip Redis; emit static catalog only.")
    args = ap.parse_args()

    snap = build_snapshot(args.signals_per_supplier, args.catalog_only)
    out = json.dumps(snap, indent=2, ensure_ascii=False)
    if args.out:
        # Create the target directory if the Brain hasn't made raw/hermes/ yet.
        parent = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(parent, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        c = snap["counts"]
        print(
            f"OK: wrote {args.out} — {c['catalog']} catalog, {c['profiles']} profiles, "
            f"{c['signals']} signals (redis: {snap['meta'].get('redis')})",
            file=sys.stderr,
        )
    else:
        print(out)


if __name__ == "__main__":
    main()