import mimetypes
from email.message import EmailMessage
from pathlib import Path

from app.models import Reservation


STANDARD_AUTH_FORM = Path("app/static/forms/special-authorization.pdf")
EmailAttachment = Path | tuple[Path, str]


AUTH_TEMPLATES = {
    "Quail Ridge Lodge": {
        "subject": "Quail Ridge Lodge - Additional Information needed",
        "body": """Hello,

Regarding your upcoming reservation at QUAIL RIDGE LODGE, we need the attached special authorization form returned 3 weeks prior to your reservation. Please include all vendors, caterers, D.J., etc. that will be bringing equipment into the facility. Also, please indicate how many tables and chairs that you will need. The Lodge has 23 round tables that seat 8 (72\"), and 10 rectangular tables (30\"x96\") and 180 chairs. The rectangular tables would be for head tables and buffet. If you have any questions, please let me know.

Typically, this is how the table count is determined:
- 1 round table for cake
- 3 rectangular for buffet (rectangular table size: 30\"x96\")
- 1 rectangular for D.J.
- Head table depends on size of wedding party. 4 persons per long table.
- Round tables for remainder of guests. 8 people per 72\" round table.

Please keep in mind that any vendor or individual that is bringing in large equipment, such as tables, chairs, photo booths or ANY other large equipment, must provide a certificate of liability insurance with a minimum amount of $500,000.00 per person with a $2 million dollar aggregate. Insurance certificates must be made out to St. Charles County Government.

A park ranger will meet you at the facility at the time you list as your check-in time. The earliest you can check-in is 9:00 am. The latest check-out is 11:00 pm.

Please note: We do provide basic cleaning supplies, trash can liners, broom, mop, spray & paper towels. I do recommend you bring your own dish towels and dish soap if you plan to wash dishes.

Please send completed authorization form to reservations@sccmo.org.

Thank you,""",
    },
    "Brommelsiek Meeting Room": {
        "subject": "Brommelsiek Meeting Room - Additional Information needed",
        "body": """Hello,

Regarding your upcoming reservation at BROMMELSIEK MEETING ROOM, we need the attached special authorization form returned 3 weeks prior to your reservation. Please include all vendors, caterers, etc. that will be bringing equipment into the facility. Also, please indicate how many tables and chairs you will need. The meeting room has 8 rectangular tables (30\"x72\") that seat 6, 15 rectangular tables (15\"x72\") and 50 chairs. If you have any questions, please let me know.

Please keep in mind that any vendor or individual that is bringing in large equipment, such as tables, chairs, photo booths or ANY other large equipment, must provide a certificate of liability insurance with a minimum amount of $500,000.00 per person with a $2 million dollar aggregate. Insurance certificates must be made out to St. Charles County Government.

A park ranger will meet you at the facility at the time you list as your check-in time. The earliest you can check-in is 9:00 am. The latest check-out is 10:00 pm.

Please note: We do provide basic cleaning supplies, trash can liners, broom, mop, spray & paper towels. I do recommend you bring your own dish towels and dish soap if you plan to wash dishes.

Please send completed authorization form to reservations@sccmo.org.

Thank you,""",
    },
    "Matson Hill Barn": {
        "subject": "The Barn at Matson Hill - Additional Information needed",
        "body": """Hello,

Regarding your upcoming reservation at THE BARN at Matson Hill Park, we need the attached special authorization form returned 3 weeks prior to your reservation. Please include all vendors, caterers, etc. that will be brought into the facility. Also, please indicate how many tables and chairs you will need. The Barn has 30, 96\" x 40\", rectangle tables and 200 chairs. Tables and chairs must remain inside facility.

Please keep in mind that any vendor or individual that is bringing in large equipment, such as tables, chairs, photo booths or ANY other large equipment, must provide a certificate of liability insurance with a minimum amount of $500,000.00 per person with a $2 million dollar aggregate. Insurance certificates must be made out to St. Charles County Government.

A park ranger will meet you at the facility at the time you list as your check-in time. The earliest you can check-in is 10:00 am. The latest check-out is 10:00 pm.

Please send completed authorization form to reservations@sccmo.org.

Thank you,""",
    },
    "New Melle Landhaus": {
        "subject": "Landhaus at New Melle Lakes - Additional Information needed",
        "body": """Hello,

Regarding your upcoming reservation at THE LANDHAUS, we need the attached special authorization form returned 3 weeks prior to your reservation. Please include all vendors, caterers, etc. that will be bringing equipment into the facility.

Please keep in mind that any vendor or individual that is bringing in large equipment, such as tables, chairs (permitted outside only), photo booths or ANY other large equipment, must provide a certificate of liability insurance with a minimum amount of $500,000.00 per person with a $2 million dollar aggregate. Insurance certificates must be made out to St. Charles County Government.

A park ranger will meet you at the facility at the time you list as your check-in time. The earliest you can check-in is 9:00 am. The latest check-out is 11:00 pm.

Please note: In addition to the cocktail style seating indoors, we provide 5, 18\"x6' rectangular tables and 150 white folding chairs for patio use only. We do provide basic cleaning supplies; trash can liners, broom, mop, spray & paper towels. I do recommend you bring your own dish towels and dish soap if you plan to wash dishes.

Please send completed authorization form to reservations@sccmo.org.

Thank you,""",
    },
    "Heritage Meeting Room": {
        "subject": "Heritage Meeting Room - Additional Information needed",
        "body": """Good morning,

Regarding your upcoming reservation at THE HERITAGE MEETING ROOM, please fill out the attached form to let us know more details about your event. Please let us know how many tables and chairs you will need during your rental. The meeting room has 13, 60\" x 18\" seminar style tables and 32 chairs.

Your rental begins at Noon and ends at 9:00 pm. Please let us know when you will check-in and check-out. A museum staff member will be at the facility at that time of your reservation.

Thank you,""",
    },
}


def event_date_text(reservation: Reservation) -> str:
    return reservation.event_date.strftime("%m/%d/%Y")


def reminder_subject(reservation: Reservation) -> str:
    return f"Authorization Form Required - {reservation.facility.facility_name}, {event_date_text(reservation)}"


def reminder_body(reservation: Reservation) -> str:
    facility_name = reservation.facility.facility_name
    return f"""Hello,

This is a reminder that we are still waiting on your authorization form for your reservation at {facility_name} on {event_date_text(reservation)}. As mentioned previously, we need the completed form in order to schedule staff and prepare the facility for your reservation.

Since the date is approaching, we kindly ask that you submit the form at your earliest convenience so we can make the necessary arrangements.

Please feel free to reach out by phone or email if you have any questions.

Thank you,"""


def approval_subject(reservation: Reservation) -> str:
    return f"Approved Authorization - {event_date_text(reservation)}"


def approval_body(reservation: Reservation, check_in_time: str) -> str:
    facility_name = reservation.facility.facility_name
    return f"""Good morning,

Attached is your approved special authorization form for your reservation at {facility_name} on {event_date_text(reservation)}.

A Park Ranger will meet you at the {facility_name} at {check_in_time} for check-in.

Leave facility as you found it.

Your cleaning responsibilities prior to check-out:
1. Pick up trash and cigarettes on grounds around building and parking lots
2. Tables and chairs wiped clean
3. Decorations removed and disposed of properly
4. All indoor areas clean of debris, stickiness, restroom spills
5. All outdoor areas reserved cleaned of trash, debris, cigarette butts (includes flowerbeds/turf/wooded)
6. All kitchen appliances cleaned & wipe down, food removed
7. All trash bagged, tied, and placed in dumpster outside (Landhaus is only required to tie bags and place them in garage).
8. All items not belonging to Parks Department removed
9. Rental key is located and returned to Ranger

Thank you,"""


def authorization_template(reservation: Reservation) -> tuple[str, str]:
    template = AUTH_TEMPLATES.get(reservation.facility.facility_name)
    if template is None:
        subject = f"{reservation.facility.facility_name} - Additional Information needed"
        body = reminder_body(reservation)
        return subject, body
    return template["subject"], template["body"]


def build_eml(
    reservation: Reservation,
    subject: str,
    body: str,
    attachments: list[EmailAttachment] | None = None,
) -> bytes:
    if not reservation.email:
        raise ValueError("Reservation does not have an email address.")

    message = EmailMessage()
    message["To"] = reservation.email
    message["Subject"] = subject
    message.set_content(body)

    for attachment in attachments or []:
        if isinstance(attachment, tuple):
            attachment_path, display_name = attachment
        else:
            attachment_path = attachment
            display_name = attachment.name

        if not attachment_path.exists():
            raise ValueError(f"Attachment file is missing: {display_name}")
        content_type, _ = mimetypes.guess_type(display_name)
        maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
        message.add_attachment(
            attachment_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=display_name,
        )

    return message.as_bytes()
