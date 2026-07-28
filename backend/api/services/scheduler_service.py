from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.database import SessionLocal
from api.services.daily_summary_service import (
    DailySummaryService,
    STORE_TIMEZONE,
)


def run_daily_maintenance():
    db = SessionLocal()
    try:
        today = datetime.now(STORE_TIMEZONE).date()
        DailySummaryService.settle_date(
            db,
            today - timedelta(days=1),
        )
        DailySummaryService.cleanup_old_data(db, today)
    finally:
        db.close()


def run_startup_maintenance():
    db = SessionLocal()
    try:
        today = datetime.now(STORE_TIMEZONE).date()
        DailySummaryService.settle_recent_dates(db, today)
        DailySummaryService.cleanup_old_data(db, today)
    finally:
        db.close()


def create_scheduler():
    scheduler = AsyncIOScheduler(timezone=STORE_TIMEZONE)
    scheduler.add_job(
        run_daily_maintenance,
        trigger="cron",
        hour=0,
        minute=0,
        id="daily-sales-maintenance",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
        max_instances=1,
    )
    return scheduler
