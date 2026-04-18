"""
KPI ingestor — two modes:
  A) HTTP push via POST /ingest/kpis (called by external pipeline)
  B) File watch via APScheduler (polls KPI_IMPORT_PATH every 15 min)
"""
import hashlib
import json
import logging
import os
from datetime import date, datetime

from ..db.session import AsyncSessionLocal
from ..db.models import KPISnapshot

log = logging.getLogger(__name__)

KPI_IMPORT_PATH = os.getenv("KPI_IMPORT_PATH", "")

_last_file_mtime: float = 0.0


def _snapshot_id(market: str, as_of_date: date) -> str:
    key = f"{market}-{as_of_date.isoformat()}"
    return "kpi-" + hashlib.sha1(key.encode()).hexdigest()[:12]


async def ingest_kpis(market: str, kpis: dict, as_of_date: date) -> None:
    """Write a KPI snapshot to the database (idempotent by market + date)."""
    snap_id = _snapshot_id(market, as_of_date)
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        existing = await session.execute(
            select(KPISnapshot).where(KPISnapshot.id == snap_id)
        )
        if existing.scalar() is not None:
            log.info("kpi_ingestor.skip_duplicate market=%s as_of=%s", market, as_of_date)
            return
        session.add(KPISnapshot(
            id=snap_id,
            market=market,
            kpis=kpis,
            as_of_date=as_of_date,
            ingested_at=datetime.utcnow(),
        ))
        await session.commit()
    log.info("kpi_ingestor.stored market=%s as_of=%s", market, as_of_date)


async def poll_kpi_file() -> None:
    """Check KPI_IMPORT_PATH for new data and ingest if the file has changed."""
    global _last_file_mtime

    if not KPI_IMPORT_PATH or not os.path.exists(KPI_IMPORT_PATH):
        return

    mtime = os.path.getmtime(KPI_IMPORT_PATH)
    if mtime <= _last_file_mtime:
        return

    try:
        with open(KPI_IMPORT_PATH, "r") as f:
            payload = json.load(f)

        market = payload.get("market", "National")
        kpis = payload.get("kpis", {})
        as_of_str = payload.get("as_of_date", date.today().isoformat())
        as_of = date.fromisoformat(as_of_str)

        await ingest_kpis(market, kpis, as_of)
        _last_file_mtime = mtime
        log.info("kpi_ingestor.file_imported path=%s market=%s", KPI_IMPORT_PATH, market)
    except Exception as exc:
        log.error("kpi_ingestor.file_error path=%s error=%s", KPI_IMPORT_PATH, exc)
