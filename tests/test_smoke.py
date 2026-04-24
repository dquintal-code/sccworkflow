import os
import re
import uuid
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://parks:parks@localhost:5432/facility_tracker")

from fastapi.testclient import TestClient

from app.main import app, DOCUMENT_STORAGE, format_local_datetime
from app.database import SessionLocal
from app.migrations import apply_migrations
from app.models import ImportPreview, Reservation


def csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def cleanup_reservation(reservation_id: str) -> None:
    with SessionLocal() as db:
        reservation = db.query(Reservation).filter_by(reservation_id=reservation_id).first()
        if reservation is None:
            return
        for document in reservation.documents:
            stored_path = DOCUMENT_STORAGE / document.stored_filename
            if stored_path.exists():
                stored_path.unlink()
        db.delete(reservation)
        db.commit()


def cleanup_import_preview(token: str) -> None:
    with SessionLocal() as db:
        preview = db.query(ImportPreview).filter_by(token=token).first()
        if preview is not None:
            db.delete(preview)
            db.commit()


def test_apply_migrations_is_idempotent():
    apply_migrations()
    apply_migrations()


def test_main_pages_load():
    with TestClient(app) as client:
        for path in ["/", "/reservations", "/reservations/new", "/calendar", "/actions", "/import"]:
            response = client.get(path)
            assert response.status_code == 200


def test_csrf_protected_reservation_create():
    reservation_id = str(990000000 + (uuid.uuid4().int % 1000000))
    cleanup_reservation(reservation_id)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/reservations/new",
                data={
                    "reservation_id": reservation_id,
                    "facility_id": "Heritage Meeting Room",
                    "event_date": "2026-08-01",
                    "reservee_name": "Smoke Test Create",
                },
                follow_redirects=False,
            )
            assert response.status_code == 403

            form_page = client.get("/reservations/new")
            token = csrf_token(form_page.text)
            response = client.post(
                "/reservations/new",
                data={
                    "csrf_token": token,
                    "reservation_id": reservation_id,
                    "facility_id": "Heritage Meeting Room",
                    "event_date": "2026-08-01",
                    "reservee_name": "Smoke Test Create",
                    "household_number": "555401",
                    "phone": "555-0123",
                    "email": "smoke-create@example.com",
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
    finally:
        cleanup_reservation(reservation_id)


def test_document_upload_rejects_invalid_extension():
    reservation_id = str(991000000 + (uuid.uuid4().int % 1000000))
    cleanup_reservation(reservation_id)
    try:
        with SessionLocal() as db:
            db.add(
                Reservation(
                    reservation_id=reservation_id,
                    facility_id="Heritage Meeting Room",
                    booking_type="Online",
                    event_date=date(2026, 8, 2),
                    reservee_name="Smoke Test Upload",
                    cancelled=False,
                )
            )
            db.commit()

        with TestClient(app) as client:
            detail = client.get(f"/reservations/{reservation_id}")
            token = csrf_token(detail.text)
            response = client.post(
                f"/reservations/{reservation_id}/documents",
                data={
                    "csrf_token": token,
                    "document_type": "Other",
                },
                files={"upload": ("bad.exe", b"not allowed", "application/octet-stream")},
            )
            assert response.status_code == 400
            assert "must use one of these file types" in response.text
    finally:
        cleanup_reservation(reservation_id)


def test_import_preview_rejects_invalid_file_type():
    with TestClient(app) as client:
        page = client.get("/import")
        token = csrf_token(page.text)
        response = client.post(
            "/import/preview",
            data={"csrf_token": token},
            files={"upload": ("not-a-csv.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "Import file must use one of these file types" in response.text


def test_import_preview_rejects_duplicate_reservation_ids():
    csv_bytes = b"""ReservationID,Facility,BookingDate,EventDate,EventEndDate,HouseholdNumber,ReserveeName,Phone,Email,Cancelled
991234567,Heritage Meeting Room,2026-06-01,2026-08-05,,555401,Test One,555-0111,test-one@example.com,false
991234567,Heritage Meeting Room,2026-06-02,2026-08-06,,555402,Test Two,555-0222,test-two@example.com,false
"""
    with TestClient(app) as client:
        page = client.get("/import")
        token = csrf_token(page.text)
        response = client.post(
            "/import/preview",
            data={"csrf_token": token},
            files={"upload": ("duplicate.csv", csv_bytes, "text/csv")},
        )
        assert response.status_code == 400
        assert "duplicate Reservation ID values" in response.text


def test_valid_import_preview_redirects():
    with TestClient(app) as client:
        page = client.get("/import")
        token = csrf_token(page.text)
        sample_path = Path("sample_imports/baseline_rectrac_export.csv")
        with sample_path.open("rb") as handle:
            response = client.post(
                "/import/preview",
                data={"csrf_token": token},
                files={"upload": (sample_path.name, handle, "text/csv")},
                follow_redirects=False,
            )
        assert response.status_code == 303
        location = response.headers["location"]
        preview_token = location.rsplit("/", 1)[-1]
        cleanup_import_preview(preview_token)


def test_reservation_sort_links_preserve_special_character_filters():
    with TestClient(app) as client:
        response = client.get("/reservations?q=A%26B")
        assert response.status_code == 200
        assert "/reservations?q=A%26B&amp;facility_id=&amp;reservation_date=&amp;include_canceled=false&amp;sort=reservation_id&amp;direction=asc" in response.text


def test_format_local_datetime_converts_utc_to_local_timezone():
    value = datetime(2026, 1, 15, 18, 30, tzinfo=timezone.utc)
    assert format_local_datetime(value) == "2026-01-15 12:30 PM CST"
