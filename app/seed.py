from datetime import date

from app.database import SessionLocal
from app.migrations import apply_migrations
from app.models import Facility, Reservation


FACILITIES = [
    {"facility_id": "Brommelsiek Meeting Room", "facility_name": "Brommelsiek Meeting Room"},
    {"facility_id": "Quail Ridge Lodge", "facility_name": "Quail Ridge Lodge"},
    {"facility_id": "New Melle Landhaus", "facility_name": "New Melle Landhaus"},
    {"facility_id": "Matson Hill Barn", "facility_name": "Matson Hill Barn"},
    {"facility_id": "Heritage Meeting Room", "facility_name": "Heritage Meeting Room"},
]


LEGACY_RESERVATION_IDS = {
    "R-2026-0412": "600412",
    "R-2026-0408": "600408",
    "R-2026-0334": "600334",
    "R-2026-0328": "600328",
    "R-2026-0402": "600402",
    "R-2026-0277": "600277",
    "R-2026-0188": "600188",
    "R-2026-0220": "600220",
    "R-2026-0430": "600430",
    "R-2026-0301": "600301",
    "R-2026-0441": "600441",
}

LEGACY_FACILITIES = {
    "LP-PAV-LAKE": "Brommelsiek Meeting Room",
    "CRC-BANQ-HALL": "Quail Ridge Lodge",
    "SP-FIELD-01": "New Melle Landhaus",
    "GCC-MEET-ROOM": "Heritage Meeting Room",
}

ACCIDENTAL_FACILITIES = {
    "Broemmelsiek": "Brommelsiek Meeting Room",
    "Brommelsiek": "Brommelsiek Meeting Room",
    "Broemmelsiek Meeting Room": "Brommelsiek Meeting Room",
    "Broemmelsiek Park": "Brommelsiek Meeting Room",
    "Brommelsiek Park": "Brommelsiek Meeting Room",
}


SOURCE_SEED_FIELDS = {
    "reservation_id",
    "facility_id",
    "booking_type",
    "booking_date",
    "event_date",
    "event_end_date",
    "household_number",
    "reservee_name",
    "phone",
    "email",
    "cancelled",
    "last_sync_action",
}


RESERVATIONS = [
    {
        "reservation_id": "600412",
        "facility_id": "Brommelsiek Meeting Room",
        "booking_type": "Online",
        "booking_date": date(2026, 4, 12),
        "event_date": date(2026, 5, 3),
        "event_end_date": None,
        "household_number": "10482",
        "reservee_name": "Jenna Morales",
        "phone": "555-0147",
        "email": "jenna.morales@example.com",
        "cancelled": False,
        "notes": "New one-day online reservation. Authorization has not been started.",
        "auth_due_date": date(2026, 4, 19),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600408",
        "facility_id": "Brommelsiek Meeting Room",
        "booking_type": "Online",
        "booking_date": date(2026, 4, 8),
        "event_date": date(2026, 5, 3),
        "event_end_date": None,
        "household_number": "10391",
        "reservee_name": "Maya Chen",
        "phone": "555-0128",
        "email": "maya.chen@example.com",
        "cancelled": False,
        "notes": "Overlaps with another pavilion reservation so the calendar shows multiple entries.",
        "auth_sent_date": date(2026, 4, 10),
        "auth_due_date": date(2026, 4, 16),
        "auth_received_date": date(2026, 4, 16),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600334",
        "facility_id": "Quail Ridge Lodge",
        "booking_type": "Phone",
        "booking_date": date(2026, 3, 29),
        "event_date": date(2026, 4, 30),
        "event_end_date": None,
        "household_number": "9764",
        "reservee_name": "Robert Anders",
        "phone": "555-0194",
        "email": "robert.anders@example.com",
        "cancelled": False,
        "notes": "Contract sent but not returned yet.",
        "contract_sent_date": date(2026, 4, 13),
        "contract_due_date": date(2026, 4, 20),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600328",
        "facility_id": "Quail Ridge Lodge",
        "booking_type": "Phone",
        "booking_date": date(2026, 3, 28),
        "event_date": date(2026, 4, 26),
        "event_end_date": None,
        "household_number": "10018",
        "reservee_name": "Danielle Brooks",
        "phone": "555-0162",
        "email": "danielle.brooks@example.com",
        "cancelled": False,
        "notes": "Signed contract received. Payment is overdue.",
        "contract_sent_date": date(2026, 4, 8),
        "contract_due_date": date(2026, 4, 15),
        "contract_received_date": date(2026, 4, 11),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600402",
        "facility_id": "New Melle Landhaus",
        "booking_type": "Online",
        "booking_date": date(2026, 4, 2),
        "event_date": date(2026, 5, 1),
        "event_end_date": date(2026, 5, 3),
        "household_number": "11820",
        "reservee_name": "Pine Ridge Youth Soccer",
        "phone": "555-0188",
        "email": "scheduler@pineridgesoccer.example.com",
        "cancelled": False,
        "notes": "Multi-day reservation. Authorization was sent but has not been returned.",
        "auth_sent_date": date(2026, 4, 10),
        "auth_due_date": date(2026, 4, 15),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600277",
        "facility_id": "Heritage Meeting Room",
        "booking_type": "Online",
        "booking_date": date(2026, 3, 20),
        "event_date": date(2026, 4, 22),
        "event_end_date": None,
        "household_number": "9044",
        "reservee_name": "Northside Garden Club",
        "phone": "555-0119",
        "email": "northsidegarden@example.com",
        "cancelled": False,
        "notes": "Authorization received. Approval email still needs to be sent.",
        "auth_sent_date": date(2026, 4, 1),
        "auth_due_date": date(2026, 4, 8),
        "auth_received_date": date(2026, 4, 7),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600188",
        "facility_id": "Brommelsiek Meeting Room",
        "booking_type": "Phone",
        "booking_date": date(2026, 2, 28),
        "event_date": date(2026, 4, 10),
        "event_end_date": None,
        "household_number": "8702",
        "reservee_name": "Thomas Riley",
        "phone": "555-0173",
        "email": "thomas.riley@example.com",
        "cancelled": False,
        "notes": "Completed event awaiting refund processing.",
        "contract_sent_date": date(2026, 3, 4),
        "contract_due_date": date(2026, 3, 11),
        "contract_received_date": date(2026, 3, 8),
        "payment_received_date": date(2026, 3, 8),
        "auth_sent_date": date(2026, 3, 19),
        "auth_due_date": date(2026, 3, 27),
        "auth_received_date": date(2026, 3, 26),
        "approval_sent_date": date(2026, 3, 28),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600220",
        "facility_id": "Heritage Meeting Room",
        "booking_type": "Online",
        "booking_date": date(2026, 3, 3),
        "event_date": date(2026, 5, 8),
        "event_end_date": None,
        "household_number": "9351",
        "reservee_name": "Elena Watkins",
        "phone": "555-0136",
        "email": "elena.watkins@example.com",
        "cancelled": True,
        "notes": "Canceled reservation included to test canceled search toggle.",
        "last_sync_action": "Seeded as canceled from baseline sample",
    },
    {
        "reservation_id": "600430",
        "facility_id": "New Melle Landhaus",
        "booking_type": "Online",
        "booking_date": date(2026, 4, 14),
        "event_date": date(2026, 5, 10),
        "event_end_date": None,
        "household_number": "12105",
        "reservee_name": "Alicia Patel",
        "phone": "555-0106",
        "email": "alicia.patel@example.com",
        "cancelled": False,
        "notes": "Second sample import marks this reservation canceled.",
        "auth_due_date": date(2026, 4, 26),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600301",
        "facility_id": "Quail Ridge Lodge",
        "booking_type": "Phone",
        "booking_date": date(2026, 3, 24),
        "event_date": date(2026, 5, 17),
        "event_end_date": date(2026, 5, 18),
        "household_number": "9618",
        "reservee_name": "Eastview Neighborhood Association",
        "phone": "555-0181",
        "email": "eastview.na@example.com",
        "cancelled": False,
        "notes": "Multi-day phone reservation with contract and payment already complete.",
        "contract_sent_date": date(2026, 3, 25),
        "contract_due_date": date(2026, 4, 1),
        "contract_received_date": date(2026, 3, 30),
        "payment_received_date": date(2026, 3, 30),
        "auth_due_date": date(2026, 5, 3),
        "last_sync_action": "Seeded from baseline sample",
    },
    {
        "reservation_id": "600441",
        "facility_id": "Heritage Meeting Room",
        "booking_type": "Online",
        "booking_date": date(2026, 4, 15),
        "event_date": date(2026, 6, 5),
        "event_end_date": None,
        "household_number": "12344",
        "reservee_name": "Samantha Ortiz",
        "phone": "555-0155",
        "email": "samantha.ortiz@example.com",
        "cancelled": False,
        "notes": "Future online booking outside the authorization lookahead window.",
        "auth_due_date": date(2026, 5, 22),
        "last_sync_action": "Seeded from baseline sample",
    },
]


def ensure_facilities(db) -> None:
    for facility_data in FACILITIES:
        facility = db.get(Facility, facility_data["facility_id"])
        if facility is None:
            db.add(Facility(**facility_data))
        else:
            facility.facility_name = facility_data["facility_name"]


def seed() -> None:
    apply_migrations()
    db = SessionLocal()
    try:
        ensure_facilities(db)

        db.flush()

        for old_id, new_id in LEGACY_RESERVATION_IDS.items():
            existing = db.query(Reservation).filter_by(reservation_id=old_id).first()
            if existing is not None:
                duplicate = db.query(Reservation).filter_by(reservation_id=new_id).first()
                if duplicate is None:
                    existing.reservation_id = new_id

        db.flush()

        for reservation in db.query(Reservation).all():
            if reservation.facility_id in LEGACY_FACILITIES:
                reservation.facility_id = LEGACY_FACILITIES[reservation.facility_id]
            if reservation.facility_id in ACCIDENTAL_FACILITIES:
                reservation.facility_id = ACCIDENTAL_FACILITIES[reservation.facility_id]
            if reservation.household_number:
                reservation.household_number = "".join(ch for ch in reservation.household_number if ch.isdigit())

        db.flush()

        for reservation_data in RESERVATIONS:
            existing = db.query(Reservation).filter_by(reservation_id=reservation_data["reservation_id"]).first()
            if existing is None:
                db.add(Reservation(**reservation_data))
            else:
                for field, value in reservation_data.items():
                    if field == "notes" and existing.notes:
                        continue
                    if field in SOURCE_SEED_FIELDS:
                        setattr(existing, field, value)
                    elif getattr(existing, field) is None:
                        setattr(existing, field, value)

        for legacy_facility_id in LEGACY_FACILITIES:
            legacy_facility = db.get(Facility, legacy_facility_id)
            if legacy_facility is not None and not legacy_facility.reservations:
                db.delete(legacy_facility)

        for accidental_facility_id in ACCIDENTAL_FACILITIES:
            accidental_facility = db.get(Facility, accidental_facility_id)
            if accidental_facility is not None and not accidental_facility.reservations:
                db.delete(accidental_facility)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed data is ready.")
