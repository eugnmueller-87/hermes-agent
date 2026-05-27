"""
notifications/zeus_notifier.py

Fires a POST to the ZEUS webhook whenever Hermes detects a
HIGH-urgency significant signal. Zeus wakes up, runs the pipeline,
goes back to sleep. Zero polling needed on the Zeus side.

Env vars (set in Railway):
  ZEUS_WEBHOOK_URL  — e.g. http://187.124.14.81:8080/run
  ZEUS_API_KEY      — the X-API-Key Zeus expects
"""

import logging
import os
import threading

import httpx

log = logging.getLogger("hermes.zeus_notifier")

ZEUS_WEBHOOK_URL = os.environ.get("ZEUS_WEBHOOK_URL", "")
ZEUS_API_KEY     = os.environ.get("ZEUS_API_KEY", "")


def _post(signals: list[dict]) -> None:
    if not ZEUS_WEBHOOK_URL:
        return
    try:
        headers = {"Content-Type": "application/json"}
        if ZEUS_API_KEY:
            headers["X-API-Key"] = ZEUS_API_KEY
        with httpx.Client(timeout=10) as client:
            resp = client.post(ZEUS_WEBHOOK_URL, headers=headers)
        log.info(
            "Zeus notified — %d significant signal(s) triggered wake-up. Status: %s",
            len(signals), resp.status_code,
        )
    except Exception as exc:
        log.warning("Zeus notification failed (non-fatal): %s", exc)


def notify_zeus_if_significant(enriched: list[dict]) -> None:
    """
    Call this after detect_signals() + store_items().
    Fires async so it never blocks the Hermes crawl cycle.
    Only triggers on HIGH urgency + is_significant=True signals.
    """
    hot = [
        i for i in enriched
        if i.get("is_significant") and i.get("urgency") == "HIGH"
    ]
    if not hot:
        return

    log.info(
        "%d HIGH-urgency significant signal(s) — waking Zeus: %s",
        len(hot),
        [i.get("supplier", "?") for i in hot],
    )
    threading.Thread(target=_post, args=(hot,), daemon=True).start()
