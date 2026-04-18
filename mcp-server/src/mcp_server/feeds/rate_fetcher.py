"""
Mortgage rate fetcher — runs once daily via APScheduler.
Source: Freddie Mac PMMS data (public CSV endpoint, no auth required).
Fallback: uses the last known rates unchanged.
"""
import logging
from datetime import date, datetime

import httpx

from ..db.session import AsyncSessionLocal
from ..db.models import MortgageRate

log = logging.getLogger(__name__)

# Freddie Mac PMMS weekly survey data (public)
FREDDIE_MAC_URL = (
    "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xls"
)

# Known rate IDs we manage
RATE_IDS = {
    30: "rate-30f",
    15: "rate-15f",
}


async def _fetch_freddie_mac() -> dict[int, float] | None:
    """
    Attempt to fetch the latest 30yr and 15yr rates from Freddie Mac PMMS.
    Returns {term_years: rate} or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(FREDDIE_MAC_URL)
            resp.raise_for_status()
            # The XLS contains rows of weekly data; last row = latest
            # We parse as raw bytes and use openpyxl if available, else fall back
            import io
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                # Find header row, then last data row
                # Typical columns: date, 30yr, 15yr, ...
                for i, row in enumerate(rows):
                    if row and str(row[0]).strip().lower() in ("date", "week ending"):
                        header = row
                        break
                else:
                    return None
                last = None
                for row in rows[i + 1:]:
                    if row and row[0]:
                        last = row
                if not last:
                    return None
                rates: dict[int, float] = {}
                for j, h in enumerate(header):
                    if h and "30" in str(h):
                        try:
                            rates[30] = float(last[j])
                        except (TypeError, ValueError):
                            pass
                    if h and "15" in str(h):
                        try:
                            rates[15] = float(last[j])
                        except (TypeError, ValueError):
                            pass
                return rates if rates else None
            except ImportError:
                log.warning("rate_fetcher.openpyxl_missing skipping_parse")
                return None
    except Exception as exc:
        log.warning("rate_fetcher.freddie_mac_failed error=%s", exc)
        return None


async def fetch_and_store_rates() -> None:
    """Fetch latest mortgage rates and update the mortgage_rates table."""
    log.info("rate_fetcher.start")
    rates = await _fetch_freddie_mac()

    if not rates:
        log.info("rate_fetcher.no_data using_existing_rates")
        return

    today = date.today()
    async with AsyncSessionLocal() as session:
        for term_years, rate_val in rates.items():
            rate_id = RATE_IDS.get(term_years)
            if not rate_id:
                continue
            from sqlalchemy import select
            result = await session.execute(
                select(MortgageRate).where(MortgageRate.id == rate_id)
            )
            row = result.scalar()
            if row:
                row.rate = round(rate_val, 2)
                row.updated_date = today
                row.updated_at = datetime.utcnow()
            else:
                session.add(MortgageRate(
                    id=rate_id,
                    term_years=term_years,
                    rate=round(rate_val, 2),
                    type="Fixed",
                    updated_date=today,
                    updated_at=datetime.utcnow(),
                ))
        await session.commit()

    log.info("rate_fetcher.complete terms_updated=%d", len(rates))
