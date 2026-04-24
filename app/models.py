from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Facility(Base):
    __tablename__ = "facilities"

    facility_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    facility_name: Mapped[str] = mapped_column(String(120), nullable=False)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="facility")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reservation_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.facility_id"), nullable=False, index=True)
    booking_type: Mapped[str] = mapped_column(String(20), nullable=False)
    booking_date: Mapped[date | None] = mapped_column(Date)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_end_date: Mapped[date | None] = mapped_column(Date)
    household_number: Mapped[str | None] = mapped_column(String(40), index=True)
    reservee_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    email: Mapped[str | None] = mapped_column(String(160), index=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    contract_sent_date: Mapped[date | None] = mapped_column(Date)
    contract_due_date: Mapped[date | None] = mapped_column(Date)
    contract_received_date: Mapped[date | None] = mapped_column(Date)
    payment_received_date: Mapped[date | None] = mapped_column(Date)

    auth_sent_date: Mapped[date | None] = mapped_column(Date)
    auth_due_date: Mapped[date | None] = mapped_column(Date)
    auth_received_date: Mapped[date | None] = mapped_column(Date)
    auth_reminder_date: Mapped[date | None] = mapped_column(Date)
    approval_sent_date: Mapped[date | None] = mapped_column(Date)
    refund_sent_date: Mapped[date | None] = mapped_column(Date)
    refund_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_sync_action: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    facility: Mapped[Facility] = relationship(back_populates="reservations")
    documents: Mapped[list["ReservationDocument"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationDocument(Base):
    __tablename__ = "reservation_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.reservation_id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    reservation: Mapped[Reservation] = relationship(back_populates="documents")


class ImportPreview(Base):
    __tablename__ = "import_previews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_rows: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    preview: Mapped[dict] = mapped_column(JSON, nullable=False)
    added_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    changed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    canceled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    added_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    changed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    canceled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
