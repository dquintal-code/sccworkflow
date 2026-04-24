import calendar
import io
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import APP_NAME, APP_TIMEZONE, MAX_DOCUMENT_UPLOAD_MB, MAX_IMPORT_UPLOAD_MB
from app.database import SessionLocal, get_db
from app.migrations import apply_migrations
from app.models import Facility, ImportLog, ImportPreview, Reservation, ReservationDocument
from app.seed import ensure_facilities
from app.services.email_drafts import (
    STANDARD_AUTH_FORM,
    approval_body,
    approval_subject,
    authorization_template,
    build_eml,
    reminder_body,
    reminder_subject,
)
from app.services.imports import apply_import_preview, build_import_preview, read_csv_upload
from app.services.workflow import action_info, add_business_days, event_end


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    db = SessionLocal()
    try:
        ensure_facilities(db)
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

DOCUMENT_STORAGE = Path("storage/reservation_documents")
DOCUMENT_STORAGE.mkdir(parents=True, exist_ok=True)
CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"
MAX_DOCUMENT_UPLOAD_BYTES = MAX_DOCUMENT_UPLOAD_MB * 1024 * 1024
MAX_IMPORT_UPLOAD_BYTES = MAX_IMPORT_UPLOAD_MB * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".tif", ".tiff"}
ALLOWED_IMPORT_EXTENSIONS = {".csv"}
LOCAL_TIMEZONE = ZoneInfo(APP_TIMEZONE)


def render(request: Request, template: str, context: dict) -> HTMLResponse:
    context.setdefault("app_name", APP_NAME)
    return templates.TemplateResponse(request, template, context)


def render_error(request: Request, status_code: int, message: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "app_name": APP_NAME,
            "status_code": status_code,
            "message": message,
        },
        status_code=status_code,
    )


def csrf_input(request: Request) -> Markup:
    token = getattr(request.state, "csrf_token", None) or request.cookies.get(CSRF_COOKIE_NAME, "")
    return Markup(f'<input type="hidden" name="{CSRF_FORM_FIELD}" value="{token}">')


def format_local_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %I:%M %p %Z")


def reservation_sort_url(
    q: str,
    facility_id: str,
    reservation_date: str,
    include_canceled: bool,
    field: str,
    sort: str,
    direction: str,
) -> str:
    next_direction = "desc" if sort == field and direction == "asc" else "asc"
    params = {
        "q": q or "",
        "facility_id": facility_id or "",
        "reservation_date": reservation_date or "",
        "include_canceled": "true" if include_canceled else "false",
        "sort": field,
        "direction": next_direction,
    }
    return f"/reservations?{urlencode(params)}"


templates.env.globals["csrf_input"] = csrf_input
templates.env.globals["reservation_sort_url"] = reservation_sort_url
templates.env.filters["format_local_datetime"] = format_local_datetime


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_urlsafe(32)
    request.state.csrf_token = csrf_token

    response = await call_next(request)
    if request.cookies.get(CSRF_COOKIE_NAME) != csrf_token:
        response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=True, samesite="lax")
    return response


def validate_csrf(request: Request, csrf_token: str | None = Form(None)) -> None:
    expected_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not expected_token or csrf_token != expected_token:
        raise HTTPException(status_code=403, detail="The request could not be verified. Reload the page and try again.")


def validate_file_extension(filename: str, allowed_extensions: set[str], label: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(status_code=400, detail=f"{label} must use one of these file types: {allowed}.")
    return suffix


def read_limited_upload(upload: UploadFile, max_bytes: int, label: str) -> bytes:
    buffer = io.BytesIO()
    total_bytes = 0
    while chunk := upload.file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"{label} is too large. Limit is {max_bytes // (1024 * 1024)} MB.",
            )
        buffer.write(chunk)
    return buffer.getvalue()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    return render_error(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> HTMLResponse:
    return render_error(request, 400, "The page received missing or invalid information. Please go back and check the form.")


def parse_date_value(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def form_date(form, name: str) -> date | None:
    return parse_date_value(form.get(name))


def required_text(form, name: str, label: str) -> str:
    value = (form.get(name) or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{label} is required.")
    return value


def numeric_text(form, name: str, label: str, required: bool = False) -> str | None:
    value = (form.get(name) or "").strip()
    if not value:
        if required:
            raise HTTPException(status_code=400, detail=f"{label} is required.")
        return None
    if not value.isdigit():
        raise HTTPException(status_code=400, detail=f"{label} must contain numbers only.")
    return value


def reservation_form_values(form, db: Session, existing: Reservation | None = None) -> dict:
    reservation_id = numeric_text(form, "reservation_id", "Reservation ID", required=True)
    duplicate_query = select(Reservation).where(Reservation.reservation_id == reservation_id)
    if existing is not None:
        duplicate_query = duplicate_query.where(Reservation.id != existing.id)
    duplicate = db.scalars(duplicate_query).first()
    if duplicate is not None:
        raise HTTPException(status_code=400, detail="That reservation ID is already used.")
    if existing is not None and reservation_id != existing.reservation_id and existing.documents:
        raise HTTPException(
            status_code=400,
            detail="Reservation ID cannot be changed after documents have been uploaded.",
        )

    facility_id = required_text(form, "facility_id", "Facility")
    if db.get(Facility, facility_id) is None:
        raise HTTPException(status_code=400, detail="Selected facility was not found.")

    event_date = form_date(form, "event_date")
    if event_date is None:
        raise HTTPException(status_code=400, detail="Event date is required.")
    event_end_date = form_date(form, "event_end_date")
    if event_end_date and event_end_date < event_date:
        raise HTTPException(status_code=400, detail="Event end date cannot be before event date.")

    booking_type = "Phone" if form.get("use_phone_workflow") == "on" else "Online"
    contract_sent_date = form_date(form, "contract_sent_date")
    contract_due_date = form_date(form, "contract_due_date")
    if booking_type == "Phone" and contract_sent_date and contract_due_date is None:
        contract_due_date = add_business_days(contract_sent_date, 5)

    return {
        "reservation_id": reservation_id,
        "facility_id": facility_id,
        "booking_type": booking_type,
        "booking_date": form_date(form, "booking_date"),
        "event_date": event_date,
        "event_end_date": event_end_date,
        "household_number": numeric_text(form, "household_number", "Household number"),
        "reservee_name": required_text(form, "reservee_name", "Reservee name"),
        "phone": (form.get("phone") or "").strip() or None,
        "email": (form.get("email") or "").strip() or None,
        "cancelled": form.get("cancelled") == "on",
        "notes": (form.get("notes") or "").strip() or None,
        "contract_sent_date": contract_sent_date,
        "contract_due_date": contract_due_date,
        "contract_received_date": form_date(form, "contract_received_date"),
        "payment_received_date": form_date(form, "payment_received_date"),
        "auth_sent_date": form_date(form, "auth_sent_date"),
        "auth_due_date": form_date(form, "auth_due_date"),
        "auth_received_date": form_date(form, "auth_received_date"),
        "auth_reminder_date": form_date(form, "auth_reminder_date"),
        "approval_sent_date": form_date(form, "approval_sent_date"),
        "refund_sent_date": form_date(form, "refund_sent_date"),
        "refund_completed": form.get("refund_completed") == "on",
    }


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def problem_flags(reservation: Reservation) -> list[str]:
    flags: list[str] = []
    if not reservation.email:
        flags.append("Missing email")
    if not reservation.phone:
        flags.append("Missing phone")
    if not reservation.household_number:
        flags.append("Missing household number")
    if reservation.event_end_date and reservation.event_end_date < reservation.event_date:
        flags.append("Event end date before event date")
    return flags


def action_row_sort_key(row: dict) -> tuple:
    status_order = {"Overdue": 0, "Due Soon": 1, "Pending": 2, "Complete": 3}
    return (
        status_order.get(row["action"].status, 9),
        row["action"].due_date or date.max,
        row["reservation"].event_date,
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    reservations = db.scalars(
        select(Reservation).options(joinedload(Reservation.facility)).where(Reservation.cancelled.is_(False))
    ).all()

    actions = [action_info(reservation, today) for reservation in reservations]
    overdue_count = sum(1 for action in actions if action.status == "Overdue")
    due_soon_count = sum(1 for action in actions if action.status == "Due Soon")
    upcoming_count = sum(
        1 for reservation in reservations if today <= reservation.event_date <= today + timedelta(days=30)
    )
    recent_import = db.scalars(select(ImportLog).order_by(ImportLog.imported_at.desc())).first()
    recent_import_changes = []
    if recent_import:
        summary = recent_import.summary or {}
        for section, label in [
            ("new_records", "Added"),
            ("changed_records", "Changed"),
            ("canceled_records", "Canceled"),
        ]:
            for row in summary.get(section, [])[:5]:
                recent_import_changes.append(
                    {
                        "label": label,
                        "reservation_id": row.get("reservation_id"),
                        "reservee_name": row.get("reservee_name", ""),
                        "facility_id": row.get("facility_id", ""),
                    }
                )
        recent_import_changes = recent_import_changes[:8]

    action_rows = []
    authorization_rows = []
    for reservation, action in zip(reservations, actions):
        if action.status != "Complete":
            row = {"reservation": reservation, "action": action}
            action_rows.append(row)
            if action.next_action == "Send authorization email":
                authorization_rows.append(row)

    action_rows.sort(key=action_row_sort_key)
    authorization_rows.sort(key=action_row_sort_key)

    upcoming_events = sorted(
        [
            reservation
            for reservation in reservations
            if today <= reservation.event_date <= today + timedelta(days=14)
        ],
        key=lambda reservation: (reservation.event_date, reservation.facility.facility_name, reservation.reservee_name),
    )[:10]

    problem_records = []
    for reservation in sorted(reservations, key=lambda item: (item.event_date, item.reservation_id)):
        flags = problem_flags(reservation)
        if flags:
            problem_records.append({"reservation": reservation, "flags": flags})
        if len(problem_records) >= 8:
            break

    return render(
        request,
        "dashboard.html",
        {
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count,
            "upcoming_count": upcoming_count,
            "action_rows": action_rows[:10],
            "authorization_rows": authorization_rows[:8],
            "upcoming_events": upcoming_events,
            "problem_records": problem_records,
            "recent_import": recent_import,
            "recent_import_changes": recent_import_changes,
        },
    )


@app.get("/reservations", response_class=HTMLResponse)
def reservation_search(
    request: Request,
    q: str = "",
    facility_id: str = "",
    reservation_date: str = "",
    include_canceled: bool = False,
    sort: str = "event_date",
    direction: str = "asc",
    db: Session = Depends(get_db),
):
    facilities = db.scalars(select(Facility).order_by(Facility.facility_name)).all()
    query = select(Reservation).options(joinedload(Reservation.facility)).join(Facility)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Reservation.reservation_id.ilike(pattern),
                Reservation.reservee_name.ilike(pattern),
                Reservation.household_number.ilike(pattern),
                Reservation.email.ilike(pattern),
                Reservation.phone.ilike(pattern),
            )
        )

    if facility_id:
        query = query.where(Reservation.facility_id == facility_id)

    reserved_on = parse_date_value(reservation_date)
    if reserved_on:
        query = query.where(Reservation.event_date <= reserved_on).where(
            func.coalesce(Reservation.event_end_date, Reservation.event_date) >= reserved_on
        )

    if not include_canceled:
        query = query.where(Reservation.cancelled.is_(False))

    sort_columns = {
        "reservation_id": Reservation.reservation_id,
        "facility": Facility.facility_name,
        "reservee_name": Reservation.reservee_name,
        "event_date": Reservation.event_date,
        "cancelled": Reservation.cancelled,
    }
    sort_column = sort_columns.get(sort, Reservation.event_date)
    order_by = desc(sort_column) if direction == "desc" else asc(sort_column)
    results = db.scalars(query.order_by(order_by, Reservation.reservation_id)).all()

    return render(
        request,
        "reservations_search.html",
        {
            "facilities": facilities,
            "results": results,
            "q": q,
            "facility_id": facility_id,
            "reservation_date": reservation_date,
            "include_canceled": include_canceled,
            "sort": sort,
            "direction": direction,
        },
    )


@app.get("/reservations/new", response_class=HTMLResponse)
def new_reservation(request: Request, db: Session = Depends(get_db)):
    facilities = db.scalars(select(Facility).order_by(Facility.facility_name)).all()
    return render(request, "reservation_new.html", {"facilities": facilities})


@app.post("/reservations/new", dependencies=[Depends(validate_csrf)])
async def create_reservation(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    reservation_data = reservation_form_values(form, db)
    reservation = Reservation(**reservation_data, last_sync_action="Manually created")
    db.add(reservation)
    db.commit()
    return RedirectResponse(url=f"/reservations/{reservation.reservation_id}?created=1", status_code=303)


@app.get("/reservations/{reservation_id}", response_class=HTMLResponse)
def reservation_detail(request: Request, reservation_id: str, db: Session = Depends(get_db)):
    reservation = db.execute(
        select(Reservation)
        .options(joinedload(Reservation.facility), joinedload(Reservation.documents))
        .where(Reservation.reservation_id == reservation_id)
    ).unique().scalars().first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    facilities = db.scalars(select(Facility).order_by(Facility.facility_name)).all()

    return render(
        request,
        "reservation_detail.html",
        {
            "reservation": reservation,
            "facilities": facilities,
            "action": action_info(reservation),
            "approved_documents": [
                document
                for document in sorted(reservation.documents, key=lambda item: item.uploaded_at, reverse=True)
                if document.document_type == "Approved authorization form"
            ],
        },
    )


@app.post("/reservations/{reservation_id}/documents", dependencies=[Depends(validate_csrf)])
async def upload_reservation_document(
    reservation_id: str,
    document_type: str = Form(...),
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    reservation = db.scalars(select(Reservation).where(Reservation.reservation_id == reservation_id)).first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Please choose a file to upload.")
    safe_suffix = validate_file_extension(upload.filename, ALLOWED_DOCUMENT_EXTENSIONS, "Document upload")
    file_bytes = read_limited_upload(upload, MAX_DOCUMENT_UPLOAD_BYTES, "Document upload")

    stored_filename = f"{reservation_id}-{uuid.uuid4().hex}{safe_suffix}"
    stored_path = DOCUMENT_STORAGE / stored_filename
    with stored_path.open("wb") as output:
        output.write(file_bytes)

    document = ReservationDocument(
        reservation_id=reservation.reservation_id,
        document_type=document_type,
        original_filename=upload.filename,
        stored_filename=stored_filename,
        content_type=upload.content_type,
    )
    db.add(document)
    db.commit()
    return RedirectResponse(url=f"/reservations/{reservation_id}?uploaded=1#documents-emails", status_code=303)


@app.get("/reservations/{reservation_id}/documents/{document_id}")
def download_reservation_document(reservation_id: str, document_id: int, db: Session = Depends(get_db)):
    document = db.get(ReservationDocument, document_id)
    if document is None or document.reservation_id != reservation_id:
        raise HTTPException(status_code=404, detail="Document not found")

    stored_path = DOCUMENT_STORAGE / document.stored_filename
    if not stored_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")

    return FileResponse(
        stored_path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.original_filename,
    )


def email_download_response(content: bytes, filename: str) -> Response:
    return Response(
        content,
        media_type="message/rfc822",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def reservation_for_email(db: Session, reservation_id: str) -> Reservation:
    reservation = db.execute(
        select(Reservation)
        .options(joinedload(Reservation.facility), joinedload(Reservation.documents))
        .where(Reservation.reservation_id == reservation_id)
    ).unique().scalars().first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if not reservation.email:
        raise HTTPException(status_code=400, detail="Reservation does not have an email address.")
    return reservation


def reservation_for_status_update(db: Session, reservation_id: str) -> Reservation:
    reservation = db.scalars(select(Reservation).where(Reservation.reservation_id == reservation_id)).first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


def reservation_redirect(reservation_id: str, marker: str, anchor: str = "details-panel") -> RedirectResponse:
    return RedirectResponse(url=f"/reservations/{reservation_id}?marked={marker}#{anchor}", status_code=303)


@app.post("/reservations/{reservation_id}/emails/authorization", dependencies=[Depends(validate_csrf)])
def generate_authorization_email(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_email(db, reservation_id)
    subject, body = authorization_template(reservation)
    try:
        content = build_eml(reservation, subject, body, [STANDARD_AUTH_FORM])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return email_download_response(content, f"{reservation_id}-authorization.eml")


@app.post("/reservations/{reservation_id}/emails/reminder", dependencies=[Depends(validate_csrf)])
def generate_reminder_email(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_email(db, reservation_id)
    try:
        content = build_eml(reservation, reminder_subject(reservation), reminder_body(reservation), [STANDARD_AUTH_FORM])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return email_download_response(content, f"{reservation_id}-authorization-reminder.eml")


@app.post("/reservations/{reservation_id}/emails/approval", dependencies=[Depends(validate_csrf)])
def generate_approval_email(
    reservation_id: str,
    check_in_time: str = Form(...),
    document_id: int = Form(...),
    db: Session = Depends(get_db),
):
    reservation = reservation_for_email(db, reservation_id)
    check_in_time = check_in_time.strip()
    if not check_in_time:
        raise HTTPException(status_code=400, detail="Check-in time is required.")

    document = db.get(ReservationDocument, document_id)
    if document is None or document.reservation_id != reservation_id:
        raise HTTPException(status_code=400, detail="Selected approved form was not found.")
    if document.document_type != "Approved authorization form":
        raise HTTPException(status_code=400, detail="Only an approved authorization form can be attached to this email.")

    attachment_path = DOCUMENT_STORAGE / document.stored_filename
    try:
        content = build_eml(
            reservation,
            approval_subject(reservation),
            approval_body(reservation, check_in_time),
            [(attachment_path, document.original_filename)],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return email_download_response(content, f"{reservation_id}-approval.eml")


@app.post("/reservations/{reservation_id}/emails/authorization/mark-sent", dependencies=[Depends(validate_csrf)])
def mark_authorization_email_sent(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.auth_sent_date = date.today()
    reservation.auth_due_date = reservation.event_date - timedelta(days=21)
    db.commit()
    return reservation_redirect(reservation_id, "authorization", "documents-emails")


@app.post("/reservations/{reservation_id}/emails/reminder/mark-sent", dependencies=[Depends(validate_csrf)])
def mark_reminder_email_sent(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.auth_reminder_date = date.today()
    db.commit()
    return reservation_redirect(reservation_id, "reminder", "documents-emails")


@app.post("/reservations/{reservation_id}/emails/approval/mark-sent", dependencies=[Depends(validate_csrf)])
def mark_approval_email_sent(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.approval_sent_date = date.today()
    db.commit()
    return reservation_redirect(reservation_id, "approval", "documents-emails")


@app.post("/reservations/{reservation_id}/workflow/contract-sent-today", dependencies=[Depends(validate_csrf)])
def mark_contract_sent_today(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.booking_type = "Phone"
    reservation.contract_sent_date = date.today()
    if reservation.contract_due_date is None:
        reservation.contract_due_date = add_business_days(reservation.contract_sent_date, 5)
    db.commit()
    return reservation_redirect(reservation_id, "contract_sent")


@app.post("/reservations/{reservation_id}/workflow/contract-received-today", dependencies=[Depends(validate_csrf)])
def mark_contract_received_today(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.booking_type = "Phone"
    reservation.contract_received_date = date.today()
    db.commit()
    return reservation_redirect(reservation_id, "contract_received")


@app.post("/reservations/{reservation_id}/workflow/payment-received-today", dependencies=[Depends(validate_csrf)])
def mark_payment_received_today(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.booking_type = "Phone"
    reservation.payment_received_date = date.today()
    db.commit()
    return reservation_redirect(reservation_id, "payment_received")


@app.post("/reservations/{reservation_id}/workflow/authorization-received-today", dependencies=[Depends(validate_csrf)])
def mark_authorization_received_today(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    reservation.auth_received_date = date.today()
    db.commit()
    return reservation_redirect(reservation_id, "authorization_received")


@app.post("/reservations/{reservation_id}/workflow/refund-completed-today", dependencies=[Depends(validate_csrf)])
def mark_refund_completed_today(reservation_id: str, db: Session = Depends(get_db)):
    reservation = reservation_for_status_update(db, reservation_id)
    if reservation.refund_sent_date is None:
        reservation.refund_sent_date = date.today()
    reservation.refund_completed = True
    db.commit()
    return reservation_redirect(reservation_id, "refund_completed")


@app.post("/reservations/{reservation_id}/documents/{document_id}/delete", dependencies=[Depends(validate_csrf)])
def delete_reservation_document(reservation_id: str, document_id: int, db: Session = Depends(get_db)):
    document = db.get(ReservationDocument, document_id)
    if document is None or document.reservation_id != reservation_id:
        raise HTTPException(status_code=404, detail="Document not found")

    stored_path = DOCUMENT_STORAGE / document.stored_filename
    if stored_path.exists():
        stored_path.unlink()
    db.delete(document)
    db.commit()
    return RedirectResponse(url=f"/reservations/{reservation_id}?doc_deleted=1#documents-emails", status_code=303)


@app.post("/reservations/{reservation_id}", dependencies=[Depends(validate_csrf)])
async def update_reservation(request: Request, reservation_id: str, db: Session = Depends(get_db)):
    reservation = db.execute(
        select(Reservation)
        .options(joinedload(Reservation.documents))
        .where(Reservation.reservation_id == reservation_id)
    ).unique().scalars().first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    form = await request.form()
    reservation_data = reservation_form_values(form, db, existing=reservation)
    for field, value in reservation_data.items():
        setattr(reservation, field, value)

    db.commit()
    return RedirectResponse(url=f"/reservations/{reservation.reservation_id}?saved=1", status_code=303)


@app.post("/reservations/{reservation_id}/delete", dependencies=[Depends(validate_csrf)])
def delete_reservation(reservation_id: str, db: Session = Depends(get_db)):
    reservation = db.execute(
        select(Reservation)
        .options(joinedload(Reservation.documents))
        .where(Reservation.reservation_id == reservation_id)
    ).unique().scalars().first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    for document in reservation.documents:
        stored_path = DOCUMENT_STORAGE / document.stored_filename
        if stored_path.exists():
            stored_path.unlink()

    db.delete(reservation)
    db.commit()
    return RedirectResponse(url=f"/reservations?deleted={reservation_id}", status_code=303)


@app.get("/calendar", response_class=HTMLResponse)
def facility_calendar(
    request: Request,
    facility_id: str = "",
    year: int | None = None,
    month: int | None = None,
    include_canceled: bool = False,
    db: Session = Depends(get_db),
):
    facilities = db.scalars(select(Facility).order_by(Facility.facility_name)).all()
    if not facilities:
        return render(request, "calendar.html", {"facilities": [], "calendar_weeks": []})

    today = date.today()
    year = year or today.year
    month = month or today.month
    facility_id = facility_id or facilities[0].facility_id

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    query = (
        select(Reservation)
        .options(joinedload(Reservation.facility))
        .where(Reservation.facility_id == facility_id)
        .where(Reservation.event_date <= last_day)
        .where(func.coalesce(Reservation.event_end_date, Reservation.event_date) >= first_day)
    )
    if not include_canceled:
        query = query.where(Reservation.cancelled.is_(False))

    reservations = db.scalars(query.order_by(Reservation.event_date, Reservation.reservee_name)).all()

    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_cells = []
        for day in week:
            day_reservations = [
                reservation
                for reservation in reservations
                if reservation.event_date <= day <= event_end(reservation)
            ]
            week_cells.append(
                {
                    "date": day,
                    "in_month": day.month == month,
                    "reservations": day_reservations,
                }
            )
        weeks.append(week_cells)

    prev_year, prev_month = previous_month(year, month)
    next_year, next_month_value = next_month(year, month)

    return render(
        request,
        "calendar.html",
        {
            "facilities": facilities,
            "facility_id": facility_id,
            "year": year,
            "month": month,
            "month_name": first_day.strftime("%B %Y"),
            "calendar_weeks": weeks,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month_value,
            "include_canceled": include_canceled,
        },
    )


@app.get("/actions", response_class=HTMLResponse)
def action_queue(request: Request, db: Session = Depends(get_db)):
    reservations = db.scalars(
        select(Reservation)
        .options(joinedload(Reservation.facility))
        .where(Reservation.cancelled.is_(False))
        .order_by(Reservation.event_date, Reservation.reservation_id)
    ).all()

    rows = []
    for reservation in reservations:
        action = action_info(reservation)
        if action.status == "Complete":
            continue
        rows.append({"reservation": reservation, "action": action})

    rows.sort(key=action_row_sort_key)

    return render(request, "action_queue.html", {"rows": rows})


@app.get("/import", response_class=HTMLResponse)
def import_upload(request: Request, db: Session = Depends(get_db)):
    recent_imports = db.scalars(select(ImportLog).order_by(ImportLog.imported_at.desc()).limit(10)).all()
    return render(request, "import_upload.html", {"recent_imports": recent_imports})


@app.post("/import/preview", dependencies=[Depends(validate_csrf)])
async def import_preview(
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Please choose a CSV file to import.")
    validate_file_extension(upload.filename, ALLOWED_IMPORT_EXTENSIONS, "Import file")
    try:
        upload_bytes = await upload.read()
        if len(upload_bytes) > MAX_IMPORT_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Import file is too large. Limit is {MAX_IMPORT_UPLOAD_MB} MB.",
            )
        rows = read_csv_upload(upload_bytes)
        preview = build_import_preview(db, rows, upload.filename or "uploaded.csv")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=f"/import/preview/{preview.token}", status_code=303)


@app.get("/import/preview/{token}", response_class=HTMLResponse)
def import_preview_page(request: Request, token: str, db: Session = Depends(get_db)):
    preview = db.scalars(select(ImportPreview).where(ImportPreview.token == token)).first()
    if preview is None:
        raise HTTPException(status_code=404, detail="Import preview not found")
    return render(request, "import_preview.html", {"preview": preview})


@app.post("/import/apply/{token}", dependencies=[Depends(validate_csrf)])
def import_apply(token: str, confirm: str = Form(""), db: Session = Depends(get_db)):
    preview = db.scalars(select(ImportPreview).where(ImportPreview.token == token)).first()
    if preview is None:
        raise HTTPException(status_code=404, detail="Import preview not found")
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Import was not confirmed.")

    try:
        log = apply_import_preview(db, preview)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=f"/import?applied={log.id}", status_code=303)
