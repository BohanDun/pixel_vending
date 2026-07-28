from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, text

from api.models import DailySummary, Transaction, TransactionStatus


STORE_TIMEZONE = ZoneInfo("Pacific/Auckland")
TRANSACTION_RETENTION_DAYS = 7
SUMMARY_RETENTION_DAYS = 30


class DailySummaryService:
    @staticmethod
    def utc_bounds_for_local_date(summary_date: date):
        start_local = datetime.combine(
            summary_date,
            time.min,
            tzinfo=STORE_TIMEZONE,
        )
        end_local = start_local + timedelta(days=1)
        return (
            start_local.astimezone(timezone.utc).replace(tzinfo=None),
            end_local.astimezone(timezone.utc).replace(tzinfo=None),
        )

    @staticmethod
    def settle_date(db, summary_date: date) -> int:
        start_utc, end_utc = DailySummaryService.utc_bounds_for_local_date(
            summary_date
        )
        user_ids = [
            row.user_id
            for row in (
                db.query(Transaction.user_id)
                .filter(
                    Transaction.created_at >= start_utc,
                    Transaction.created_at < end_utc,
                )
                .distinct()
                .all()
            )
        ]

        summaries_created_or_updated = 0
        for user_id in user_ids:
            successful_transactions, total_revenue, units_sold = (
                db.query(
                    func.count(Transaction.id),
                    func.coalesce(func.sum(Transaction.total_price), 0),
                    func.coalesce(func.sum(Transaction.quantity), 0),
                )
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= start_utc,
                    Transaction.created_at < end_utc,
                    Transaction.status == TransactionStatus.SUCCESS,
                )
                .one()
            )
            total_transactions = (
                db.query(func.count(Transaction.id))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= start_utc,
                    Transaction.created_at < end_utc,
                )
                .scalar()
            )
            top_product = (
                db.query(
                    Transaction.product_id,
                    func.sum(Transaction.quantity).label("units"),
                )
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= start_utc,
                    Transaction.created_at < end_utc,
                    Transaction.status == TransactionStatus.SUCCESS,
                    Transaction.product_id.is_not(None),
                )
                .group_by(Transaction.product_id)
                .order_by(
                    func.sum(Transaction.quantity).desc(),
                    Transaction.product_id.asc(),
                )
                .first()
            )

            summary = (
                db.query(DailySummary)
                .filter(
                    DailySummary.user_id == user_id,
                    DailySummary.summary_date == summary_date,
                )
                .first()
            )
            if summary is None:
                summary = DailySummary(
                    user_id=user_id,
                    summary_date=summary_date,
                )
                db.add(summary)

            summary.total_revenue = Decimal(total_revenue)
            summary.successful_transactions = int(successful_transactions)
            summary.failed_transactions = (
                int(total_transactions) - int(successful_transactions)
            )
            summary.units_sold = int(units_sold)
            summary.top_product_id = (
                top_product.product_id if top_product is not None else None
            )
            summaries_created_or_updated += 1

        db.commit()
        return summaries_created_or_updated

    @staticmethod
    def settle_recent_dates(
        db,
        today: date,
        lookback_days: int = SUMMARY_RETENTION_DAYS,
    ) -> int:
        settled = 0
        for days_ago in range(1, lookback_days + 1):
            settled += DailySummaryService.settle_date(
                db,
                today - timedelta(days=days_ago),
            )
        return settled

    @staticmethod
    def cleanup_old_data(db, today: date):
        transaction_cutoff_date = today - timedelta(
            days=TRANSACTION_RETENTION_DAYS
        )
        transaction_cutoff_utc, _ = (
            DailySummaryService.utc_bounds_for_local_date(
                transaction_cutoff_date
            )
        )
        summary_cutoff_date = today - timedelta(
            days=SUMMARY_RETENTION_DAYS
        )

        deleted_transactions = (
            db.query(Transaction)
            .filter(Transaction.created_at < transaction_cutoff_utc)
            .delete(synchronize_session=False)
        )
        deleted_summaries = (
            db.query(DailySummary)
            .filter(DailySummary.summary_date < summary_cutoff_date)
            .delete(synchronize_session=False)
        )
        db.commit()
        db.execute(text("PRAGMA optimize"))
        return {
            "deleted_transactions": deleted_transactions,
            "deleted_summaries": deleted_summaries,
        }
