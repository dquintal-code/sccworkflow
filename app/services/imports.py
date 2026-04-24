import csv
import io
import re
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Facility, ImportLog, ImportPreview, Reservation


SOURCE_FIELDS = [
    "reservation_id",
    "facility_id",
    "booking_date",
    "event_date",
    "event_end_date",
    "household_number",
    "reservee_name",
    "phone",
    "email",
    "cancelled",
]

PRESERVE_IF_MISSING_OR_BLANK = {
    "booking_date",
}

DATE_SOURCE_FIELDS = {"booking_date", "event_date", "event_end_date"}

FIELD_LABELS = {
    "reservation_id": "Reservation ID",
    "facility_id": "Facility",
    "booking_date": "Booking date",
    "event_date": "Event date",
    "event_end_date": "Event end date",
    "household_number": "Household number",
    "reservee_name": "Reservee name",
    "phone": "Phone",
    "email": "Email",
    "cancelled": "Canceled",
}

HEADER_MAP = {
    "reservationid": "reservation_id",
    "reservation_id": "reservation_id",
    "reservationnumber": "reservation_id",
    "reservation_number": "reservation_id",
    "facilityid": "facility_id",
    "facility_id": "facility_id",
    "facility": "facility_id",
    "facilityname": "facility_id",
    "facilitylocation": "facility_location",
    "facility_location": "facility_location",
    "location:": "location",
    "location": "location",
    "bookingtype": "booking_type",
    "booking_type": "booking_type",
    "bookingdate": "booking_date",
    "booking_date": "booking_date",
    "eventdate": "event_date",
    "event_date": "event_date",
    "begindate": "event_date",
    "begin_date": "event_date",
    "eventenddate": "event_end_date",
    "event_end_date": "event_end_date",
    "enddate": "event_end_date",
    "end_date": "event_end_date",
    "householdnumber": "household_number",
    "household_number": "household_number",
    "reserveename": "reservee_name",
    "reservee_name": "reservee_name",
    "lastname": "last_name",
    "last_name": "last_name",
    "primaryfirstname": "first_name",
    "primary_first_name": "first_name",
    "firstname": "first_name",
    "first_name": "first_name",
    "phone": "phone",
    "email": "email",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

CANONICAL_FACILITIES = {
    "Brommelsiek Meeting Room",
    "Quail Ridge Lodge",
    "New Melle Landhaus",
    "Matson Hill Barn",
    "Heritage Meeting Room",
}


def facility_lookup_key(value: str) -> str:
    compact = value.lower().replace("&", " and ")
    compact = re.sub(r"[^a-z0-9]+", " ", compact)
    compact = compact.replace(" park ", " ")
    return " ".join(compact.split())


FACILITY_ALIASES = {
    facility_lookup_key("brommelsiek"): "Brommelsiek Meeting Room",
    facility_lookup_key("brommelsiek meeting room"): "Brommelsiek Meeting Room",
    facility_lookup_key("brommelsiek park"): "Brommelsiek Meeting Room",
    facility_lookup_key("broemmelsiek"): "Brommelsiek Meeting Room",
    facility_lookup_key("broemmelsiek meeting room"): "Brommelsiek Meeting Room",
    facility_lookup_key("broemmelsiek park"): "Brommelsiek Meeting Room",
    facility_lookup_key("quail ridge"): "Quail Ridge Lodge",
    facility_lookup_key("quail ridge lodge"): "Quail Ridge Lodge",
    facility_lookup_key("quail ridge park"): "Quail Ridge Lodge",
    facility_lookup_key("new melle"): "New Melle Landhaus",
    facility_lookup_key("new melle landhaus"): "New Melle Landhaus",
    facility_lookup_key("new melle lakes"): "New Melle Landhaus",
    facility_lookup_key("landhaus"): "New Melle Landhaus",
    facility_lookup_key("matson hill"): "Matson Hill Barn",
    facility_lookup_key("matson hill barn"): "Matson Hill Barn",
    facility_lookup_key("barn at matson hill"): "Matson Hill Barn",
    facility_lookup_key("the barn at matson hill"): "Matson Hill Barn",
    facility_lookup_key("heritage"): "Heritage Meeting Room",
    facility_lookup_key("heritage meeting room"): "Heritage Meeting Room",
}


def parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "cancelled", "canceled"}


def parse_date(value: str | date | None) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%-m/%-d/%Y", "%-m/%-d/%y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue

    # Some RecTrac exports include a display date such as "Thursday, April 23, 2026".
    try:
        return datetime.strptime(value, "%A, %B %d, %Y").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Could not read date value: {value}") from exc


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_header(header: str) -> str:
    compact = header.strip().replace(" ", "").replace("-", "").lower()
    return HEADER_MAP.get(compact, header.strip())


def normalize_facility(value: str | None) -> str | None:
    value = normalize_text(value)
    if not value:
        return None
    if value in CANONICAL_FACILITIES:
        return value
    mapped = FACILITY_ALIASES.get(facility_lookup_key(value))
    if mapped:
        return mapped
    raise ValueError(
        f"Unknown facility in import: {value}. Expected one of: {', '.join(sorted(CANONICAL_FACILITIES))}."
    )


def raw_rows_from_csv(contents: bytes) -> list[dict[str, str]]:
    text = contents.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise ValueError("The uploaded file does not appear to have a header row.") from exc

    if not headers:
        raise ValueError("The uploaded file does not appear to have a header row.")

    rows: list[dict[str, str]] = []
    for values in reader:
        if not any((value or "").strip() for value in values):
            continue

        row: dict[str, str] = {}
        for index, header in enumerate(headers):
            value = values[index] if index < len(values) else ""
            header = header.strip()

            # RecTrac can export blank headers for display date, phone, and email.
            if not header:
                if index == 9:
                    row["phone"] = value
                elif index == 10:
                    row["email"] = value
                continue

            row[header] = value
        rows.append(row)

    return rows


def normalize_row(row: dict[str, str]) -> dict:
    normalized: dict = {}
    source_fields: set[str] = set()
    for raw_key, raw_value in row.items():
        key = normalize_header(raw_key)
        if key == "first_name":
            normalized["first_name"] = raw_value
            continue
        if key == "last_name":
            normalized["last_name"] = raw_value
            continue
        if key == "facility_location":
            normalized["facility_location"] = raw_value
            continue
        if key == "location":
            normalized["location"] = raw_value
            continue
        if key == "booking_type":
            normalized["booking_type"] = raw_value
            continue
        if key not in SOURCE_FIELDS:
            continue
        normalized[key] = raw_value
        source_fields.add(key)

    if not normalized.get("reservee_name"):
        first_name = normalize_text(normalized.get("first_name"))
        last_name = normalize_text(normalized.get("last_name"))
        normalized["reservee_name"] = " ".join(part for part in [first_name, last_name] if part)
        if normalized["reservee_name"]:
            source_fields.add("reservee_name")

    if not normalized.get("facility_id"):
        normalized["facility_id"] = normalized.get("facility_location") or normalized.get("location")
        if normalized["facility_id"]:
            source_fields.add("facility_id")

    if not normalized.get("booking_type"):
        normalized["booking_type"] = "Online"

    required_fields = ("reservation_id", "facility_id", "event_date", "reservee_name")
    missing = [field for field in required_fields if not normalized.get(field)]
    if missing:
        labels = ", ".join(FIELD_LABELS[field] for field in missing)
        raise ValueError(f"Import row is missing required field(s): {labels}")

    reservation_id = normalize_text(normalized.get("reservation_id"))
    household_number = normalize_text(normalized.get("household_number"))
    if reservation_id and not reservation_id.isdigit():
        raise ValueError("Reservation ID must contain numbers only.")
    if household_number and not household_number.isdigit():
        raise ValueError("Household number must contain numbers only.")

    return {
        "reservation_id": reservation_id,
        "facility_id": normalize_facility(normalized.get("facility_id")),
        "booking_type": normalize_text(normalized.get("booking_type")),
        "booking_date": parse_date(normalized.get("booking_date")),
        "event_date": parse_date(normalized.get("event_date")),
        "event_end_date": parse_date(normalized.get("event_end_date")),
        "household_number": household_number,
        "reservee_name": normalize_text(normalized.get("reservee_name")),
        "phone": normalize_text(normalized.get("phone")),
        "email": normalize_text(normalized.get("email")),
        "cancelled": parse_bool(normalized.get("cancelled")),
        "_source_fields": sorted(source_fields),
    }


def read_csv_upload(contents: bytes) -> list[dict]:
    rows = raw_rows_from_csv(contents)
    if not rows:
        raise ValueError("The uploaded file did not contain any reservation rows.")
    normalized_rows = [normalize_row(row) for row in rows]
    validate_unique_reservation_ids(normalized_rows)
    return normalized_rows


def validate_unique_reservation_ids(rows: list[dict]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        reservation_id = row["reservation_id"]
        if reservation_id in seen and reservation_id not in duplicates:
            duplicates.append(reservation_id)
        seen.add(reservation_id)

    if duplicates:
        joined_ids = ", ".join(sorted(duplicates))
        raise ValueError(f"Import file contains duplicate Reservation ID values: {joined_ids}")


def serialize_source_value(value) -> str | bool | None:
    if isinstance(value, date):
        return value.isoformat()
    return value


def existing_source_snapshot(reservation: Reservation) -> dict:
    return {field: serialize_source_value(getattr(reservation, field)) for field in SOURCE_FIELDS}


def source_fields_for_row(row: dict) -> set[str]:
    if "_source_fields" in row:
        return set(row["_source_fields"])

    # Older import previews did not store source-column metadata. Preserve booking
    # dates when those older rows have no booking date value, because RecTrac
    # exports may omit that column entirely.
    return {
        field
        for field in SOURCE_FIELDS
        if field in row and not (field in PRESERVE_IF_MISSING_OR_BLANK and row.get(field) is None)
    }


def build_import_preview(db: Session, rows: list[dict], filename: str) -> ImportPreview:
    validate_unique_reservation_ids(rows)
    existing = {
        reservation.reservation_id: reservation
        for reservation in db.scalars(select(Reservation)).all()
    }

    new_records: list[dict] = []
    changed_records: list[dict] = []
    canceled_records: list[dict] = []
    included_fields = sorted(
        {
            field
            for row in rows
            for field in source_fields_for_row(row)
            if field in SOURCE_FIELDS
        },
        key=SOURCE_FIELDS.index,
    )

    for row in rows:
        reservation_id = row["reservation_id"]
        source_fields = source_fields_for_row(row)
        current = existing.get(reservation_id)
        if current is None:
            new_records.append(row)
            continue

        changes = []
        before = existing_source_snapshot(current)
        for field in SOURCE_FIELDS:
            if field not in source_fields:
                continue
            old_value = before[field]
            new_value = row.get(field)
            if old_value != new_value:
                changes.append(
                    {
                        "field": field,
                        "label": FIELD_LABELS[field],
                        "old": old_value,
                        "new": new_value,
                    }
                )

        if changes:
            changed_records.append(
                {
                    "reservation_id": reservation_id,
                    "reservee_name": current.reservee_name,
                    "facility_id": current.facility_id,
                    "changes": changes,
                }
            )

        if "cancelled" in source_fields and row.get("cancelled") and not current.cancelled:
            canceled_records.append(
                {
                    "reservation_id": reservation_id,
                    "reservee_name": current.reservee_name,
                    "facility_id": current.facility_id,
                    "event_date": current.event_date.isoformat(),
                }
            )

    preview = {
        "included_fields": [
            {
                "field": field,
                "label": FIELD_LABELS[field],
                "can_update_existing": field != "reservation_id",
            }
            for field in included_fields
        ],
        "new_records": new_records,
        "changed_records": changed_records,
        "canceled_records": canceled_records,
    }

    import_preview = ImportPreview(
        token=str(uuid.uuid4()),
        filename=filename,
        source_rows=rows,
        preview=preview,
        added_count=len(new_records),
        changed_count=len(changed_records),
        canceled_count=len(canceled_records),
    )
    db.add(import_preview)
    db.commit()
    db.refresh(import_preview)
    return import_preview


def _date_or_none(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def apply_import_preview(db: Session, preview: ImportPreview) -> ImportLog:
    if preview.applied:
        raise ValueError("This import preview has already been applied.")
    validate_unique_reservation_ids(preview.source_rows)

    existing = {
        reservation.reservation_id: reservation
        for reservation in db.scalars(select(Reservation)).all()
    }

    added = 0
    changed = 0
    canceled = 0

    for row in preview.source_rows:
        source_fields = source_fields_for_row(row)
        facility = db.get(Facility, row["facility_id"])
        if facility is None:
            raise ValueError(f"Import references an unknown facility: {row['facility_id']}")

        current = existing.get(row["reservation_id"])
        if current is None:
            db.add(
                Reservation(
                    reservation_id=row["reservation_id"],
                    facility_id=row["facility_id"],
                    booking_type=row["booking_type"],
                    booking_date=_date_or_none(row["booking_date"]),
                    event_date=_date_or_none(row["event_date"]),
                    event_end_date=_date_or_none(row["event_end_date"]),
                    household_number=row["household_number"],
                    reservee_name=row["reservee_name"],
                    phone=row["phone"],
                    email=row["email"],
                    cancelled=row["cancelled"],
                    last_sync_action=f"Added from import {preview.filename}",
                )
            )
            added += 1
            continue

        before = existing_source_snapshot(current)
        changed_this_row = False
        for field in SOURCE_FIELDS:
            if field not in source_fields:
                continue
            new_value = row.get(field)
            if before[field] == new_value:
                continue

            if field in DATE_SOURCE_FIELDS:
                setattr(current, field, _date_or_none(new_value))
            else:
                setattr(current, field, new_value)
            changed_this_row = True

        if changed_this_row:
            changed += 1
            current.last_sync_action = f"Updated from import {preview.filename}"
            if "cancelled" in source_fields and row.get("cancelled") and not before["cancelled"]:
                canceled += 1
                current.last_sync_action = f"Marked canceled from import {preview.filename}"

    preview.applied = True
    log = ImportLog(
        filename=preview.filename,
        added_count=added,
        changed_count=changed,
        canceled_count=canceled,
        summary=preview.preview,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
