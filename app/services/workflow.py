from dataclasses import dataclass
from datetime import date, timedelta

from app.config import DUE_SOON_DAYS
from app.models import Reservation


@dataclass
class ActionInfo:
    next_action: str
    due_date: date | None
    days_until_due: int | None
    status: str


def add_business_days(start_date: date, business_days: int) -> date:
    current = start_date
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def event_end(reservation: Reservation) -> date:
    return reservation.event_end_date or reservation.event_date


def status_for_due_date(
    due_date: date | None,
    today: date,
    due_soon_days: int = DUE_SOON_DAYS,
    overdue_includes_today: bool = False,
) -> tuple[int | None, str]:
    if due_date is None:
        return None, "Pending"

    days_until_due = (due_date - today).days
    if days_until_due < 0 or (overdue_includes_today and days_until_due == 0):
        return days_until_due, "Overdue"
    if days_until_due <= due_soon_days:
        return days_until_due, "Due Soon"
    return days_until_due, "Pending"


def action_info(reservation: Reservation, today: date | None = None) -> ActionInfo:
    today = today or date.today()

    if reservation.cancelled:
        return ActionInfo("No action - canceled", None, None, "Complete")

    if reservation.booking_type == "Phone":
        if reservation.contract_sent_date is None:
            days, status = status_for_due_date(today, today)
            return ActionInfo("Send contract", today, days, status)

        if reservation.contract_received_date is None:
            due_date = reservation.contract_due_date
            days, status = status_for_due_date(due_date, today)
            return ActionInfo("Get signed contract", due_date, days, status)

        if reservation.payment_received_date is None:
            due_date = reservation.contract_due_date
            days, status = status_for_due_date(due_date, today)
            return ActionInfo("Get payment", due_date, days, status)

    auth_send_due_date = reservation.event_date - timedelta(days=45)
    auth_reminder_due_date = reservation.event_date - timedelta(days=30)
    auth_due_date = reservation.auth_due_date or (reservation.event_date - timedelta(days=21))

    if reservation.auth_sent_date is None:
        days, status = status_for_due_date(
            auth_send_due_date,
            today,
            due_soon_days=5,
            overdue_includes_today=True,
        )
        return ActionInfo("Send authorization email", auth_send_due_date, days, status)

    if reservation.auth_sent_date is not None and reservation.auth_received_date is None:
        if reservation.auth_reminder_date is None and today >= auth_reminder_due_date:
            days, status = status_for_due_date(
                auth_reminder_due_date,
                today,
                due_soon_days=5,
                overdue_includes_today=True,
            )
            return ActionInfo("Send authorization reminder", auth_reminder_due_date, days, status)

        days, status = status_for_due_date(
            auth_due_date,
            today,
            due_soon_days=5,
            overdue_includes_today=True,
        )
        return ActionInfo("Receive authorization form", auth_due_date, days, status)

    if reservation.auth_received_date is not None and reservation.approval_sent_date is None:
        days, status = status_for_due_date(today, today)
        return ActionInfo("Send approval email", today, days, status)

    if event_end(reservation) < today and not reservation.refund_completed:
        refund_due = add_business_days(event_end(reservation), 5)
        if reservation.refund_sent_date is None:
            days, status = status_for_due_date(refund_due, today)
            return ActionInfo("Send refund", refund_due, days, status)

        days, status = status_for_due_date(refund_due, today)
        return ActionInfo("Complete refund", refund_due, days, status)

    return ActionInfo("No action needed", None, None, "Complete")
