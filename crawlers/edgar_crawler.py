import httpx
import hashlib
from datetime import datetime, timezone
from config.suppliers import ALL_SUPPLIERS

EDGAR_BASE = "https://data.sec.gov/submissions"
HEADERS = {"User-Agent": "Hermes-Agent hermes@icarus-bot.com"}

# Only fetch these high-signal filing types
FILING_TYPES = {"8-K", "10-Q", "10-K", "SC 13G", "DEF 14A"}


def _hash(val: str) -> str:
    return hashlib.md5(val.encode()).hexdigest()


def _get_cik(ticker: str) -> str | None:
    try:
        r = httpx.get(
            "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt=2020-01-01&forms=10-K".format(ticker),
            headers=HEADERS,
            timeout=10,
        )
        # Use the company tickers JSON endpoint instead
        tickers_r = httpx.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS,
            timeout=15,
        )
        data = tickers_r.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
    except Exception:
        pass
    return None


def _get_recent_filings(cik: str, supplier_name: str) -> list[dict]:
    try:
        r = httpx.get(f"{EDGAR_BASE}/CIK{cik}.json", headers=HEADERS, timeout=15)
        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        descriptions = filings.get("primaryDocument", [])

        results = []
        for form, date, acc, doc in zip(forms, dates, accessions, descriptions):
            if form not in FILING_TYPES:
                continue
            acc_clean = acc.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}"
            item_id = _hash(acc)
            results.append({
                "id": item_id,
                "supplier": supplier_name,
                "title": f"{supplier_name} — {form} filing ({date})",
                "url": url,
                "summary": f"SEC {form} filing dated {date}",
                "published": date,
                "source": "edgar",
                "filing_type": form,
            })
            if len(results) >= 3:
                break
        return results
    except Exception as e:
        print(f"[EDGAR] Failed {supplier_name}: {e}")
        return []


def crawl_edgar(redis_store) -> list[dict]:
    public_suppliers = [s for s in ALL_SUPPLIERS if s.get("ticker") and s["tier"] <= 2]
    new_items = []

    # Cache CIK map to avoid re-fetching
    try:
        r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=20)
        ticker_map = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in r.json().values()}
    except Exception as e:
        print(f"[EDGAR] Could not fetch ticker map: {e}")
        return []

    for supplier in public_suppliers:
        ticker = supplier["ticker"].upper()
        cik = ticker_map.get(ticker)
        if not cik:
            continue

        filings = _get_recent_filings(cik, supplier["name"])
        for filing in filings:
            if not redis_store.is_seen(filing["id"]):
                redis_store.mark_seen(filing["id"])
                new_items.append(filing)

    print(f"[EDGAR] Found {len(new_items)} new filings")
    return new_items
