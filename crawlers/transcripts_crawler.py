"""
Earnings call transcript crawler.

Fetches 8-K filings from SEC EDGAR that contain earnings-related keywords,
then pulls the full document text for signal detection. Earnings call transcripts
and earnings press releases contain dense forward-looking language that Haiku
can classify into EARNINGS, GUIDANCE, MARKET_OUTLOOK signals.

Uses the existing EDGAR infrastructure — just targets 8-K filings specifically
and fetches document text rather than just the filing metadata.

Runs on a separate schedule (weekly, after EDGAR metadata crawl) to avoid
overloading the SEC rate limiter.
"""

import hashlib
import logging

import httpx

from config.suppliers import ALL_SUPPLIERS

log = logging.getLogger("hermes.transcripts")

EDGAR_BASE = "https://data.sec.gov/submissions"
HEADERS = {"User-Agent": "Hermes-Agent hermes@icarus-bot.com"}
_EARNINGS_KEYWORDS = {
    "earnings",
    "revenue",
    "guidance",
    "quarterly results",
    "q1",
    "q2",
    "q3",
    "q4",
}
_MAX_TEXT = 3000  # characters to extract from the filing document
_TIMEOUT = 20


def _hash(val: str) -> str:
    return hashlib.md5(val.encode()).hexdigest()


def _is_earnings_related(title: str, description: str) -> bool:
    combined = (title + " " + description).lower()
    return any(kw in combined for kw in _EARNINGS_KEYWORDS)


def _fetch_document_text(url: str) -> str:
    """Fetch first _MAX_TEXT chars of a filing document. Returns '' on failure."""
    try:
        r = httpx.get(url, headers=HEADERS, timeout=_TIMEOUT)
        text = r.text
        # Strip obvious HTML tags for readability
        import re

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:_MAX_TEXT]
    except Exception as e:
        log.debug(f"Document fetch failed {url}: {e}")
        return ""


def _get_earnings_filings(cik: str, supplier_name: str) -> list[dict]:
    try:
        r = httpx.get(f"{EDGAR_BASE}/CIK{cik}.json", headers=HEADERS, timeout=15)
        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        docs = filings.get("primaryDocument", [])
        descriptions = filings.get("primaryDocDescription", [])

        results = []
        for form, date, acc, doc, desc in zip(
            forms, dates, accessions, docs, descriptions, strict=False
        ):
            if form != "8-K":
                continue
            if not _is_earnings_related(doc, desc or ""):
                continue
            acc_clean = acc.replace("-", "")
            cik_int = int(cik)
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{doc}"
            item_id = _hash(f"transcript:{acc}")
            full_text = _fetch_document_text(url)
            results.append(
                {
                    "id": item_id,
                    "supplier": supplier_name,
                    "title": f"{supplier_name} — Earnings 8-K ({date})",
                    "url": url,
                    "summary": full_text or f"SEC 8-K earnings filing dated {date}",
                    "published": date,
                    "source": "transcript",
                    "filing_type": "8-K",
                }
            )
            if len(results) >= 2:
                break
        return results
    except Exception as e:
        log.warning(f"Transcript fetch failed — {supplier_name}: {e}")
        return []


def crawl_transcripts(redis_store) -> list[dict]:
    """
    Fetch earnings-related 8-K filings with full document text for Tier 1+2 suppliers.
    Returns new items ready for signal detection.
    """
    public_suppliers = [s for s in ALL_SUPPLIERS if s.get("ticker") and s["tier"] <= 2]
    new_items = []

    try:
        r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=20)
        ticker_map = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in r.json().values()}
    except Exception as e:
        log.error(f"Could not fetch ticker map: {e}")
        return []

    for supplier in public_suppliers:
        ticker = supplier["ticker"].upper()
        cik = ticker_map.get(ticker)
        if not cik:
            continue
        filings = _get_earnings_filings(cik, supplier["name"])
        for filing in filings:
            if not redis_store.is_seen(filing["id"]):
                redis_store.mark_seen(filing["id"])
                new_items.append(filing)

    log.info(f"Transcripts crawl done — {len(new_items)} new earnings filings")
    return new_items
