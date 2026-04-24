# Facility Reservation Tracker

This is a V1 internal web application for a small Parks/Recreation team. The goal is to track reservation workflow deadlines better than the old Access process, not just store reservation records.

V1 uses:

- FastAPI for the Python web app
- PostgreSQL for the database
- Server-rendered HTML templates for the screens
- Docker Compose for an easy local setup

## Project Folder Structure

```text
.
├── app/
│   ├── main.py                 # FastAPI app, pages, forms, and routes
│   ├── config.py               # Reads environment variables
│   ├── database.py             # Database connection and table creation
│   ├── models.py               # Database table definitions
│   ├── seed.py                 # Realistic starter data
│   ├── services/
│   │   ├── workflow.py         # Next action, due date, days until due, and status logic
│   │   ├── imports.py          # RecTrac CSV preview and apply logic
│   │   └── email_drafts.py     # Authorization, reminder, and approval email drafts
│   ├── templates/              # HTML pages
│   └── static/
│       ├── styles.css          # Simple internal-app styling
│       ├── images/             # Parks logo used in the header
│       └── forms/              # Standard authorization PDF attachment
├── sample_imports/
│   ├── baseline_rectrac_export.csv
│   ├── changed_rectrac_export.csv
│   └── rectrac_export_example.csv
├── storage/
│   └── reservation_documents/  # Uploaded reservation documents; ignored except .gitkeep
├── migrations/
│   └── 001_initial_schema.sql  # Plain SQL reference for the starting schema
├── docker-compose.yml          # Runs PostgreSQL and the web app together
├── docker-compose.prod.yml     # Example internal hosting setup for IT
├── IT_HANDOFF.md               # One-page hosting and access-control notes for IT
├── STAFF_WALKTHROUGH.md        # Staff workflow walkthrough using test records
├── RUNBOOK.md                  # Maintenance notes for updates, restart, and troubleshooting
├── Dockerfile                  # Builds the Python web app container
├── requirements.txt            # Python dependencies
├── .dockerignore               # Keeps local-only files out of the Docker image
├── .env.example                # Example local settings
└── .env.production.example     # Example production settings for IT
```

## Database Schema

### facilities

This table stores the facility list.

| Field | Meaning |
| --- | --- |
| Facility | Facility name, such as Brommelsiek Meeting Room |
| Facility name | Same human-readable facility name shown in the app |

### reservations

This table stores the reservation details and the internal workflow tracking fields.

| Field | Meaning |
| --- | --- |
| id | Internal numeric primary key |
| Reservation ID | Numeric RecTrac reservation identifier, used for import matching |
| Facility | Facility name |
| Booking date | Date reservation was booked |
| Event date | Event start date |
| Event end date | Event end date; blank means one-day event |
| Household number | Numeric household identifier |
| Reservee name | Person or group reserving the facility |
| Phone | Contact phone |
| Email | Contact email |
| Canceled | Whether the reservation is canceled |
| Notes | Staff notes entered inside this tracker |
| Contract sent | Phone workflow field |
| Contract due | Phone workflow field |
| Contract received | Phone workflow field |
| Payment received | Phone workflow field |
| Authorization sent | Authorization workflow field |
| Authorization due | Authorization workflow field |
| Authorization received | Authorization workflow field |
| Reminder sent | Authorization workflow field |
| Approval email sent | Approval workflow field |
| Refund sent | Refund workflow field |
| Refund completed | Refund workflow field |
| Last import action | Last import action affecting the reservation |
| created_at / updated_at | Technical timestamps |

The app keeps an internal phone-workflow flag behind the scenes. Staff control it with the `Use phone reservation workflow` toggle on the reservation detail page. Imports do not overwrite that toggle for existing reservations.

### import_previews

This table stores uploaded import previews before staff apply them. This is what makes the process preview-first instead of direct-write.

### import_logs

This table stores a history of applied imports, including filename, timestamp, and counts added/changed/canceled.

### reservation_documents

This table stores documents uploaded on a reservation, such as returned authorization forms, approved authorization forms, signed contracts, payment receipts, insurance certificates, and other supporting files.

| Field | Meaning |
| --- | --- |
| Reservation ID | The reservation the document belongs to |
| Document type | Staff-selected document category |
| Original filename | The filename staff uploaded |
| Stored filename | Internal filename used to avoid duplicate file conflicts |
| Content type | File type reported by the browser |
| Uploaded at | Upload timestamp |

## V1 Notes

- Versioned SQL migrations are applied automatically on startup. The schema files live in `migrations/` so changes are explicit and reviewable.
- RecTrac imports only update source reservation fields: reservation ID, facility, booking date, event dates, household, reservee name, phone, email, and canceled status.
- For existing reservations, the importer only updates fields from columns that are actually present in the uploaded CSV. Missing columns are ignored instead of treated as blank values.
- RecTrac facility names are normalized to the five approved facility names. For example, `Broemmelsiek` and `Brommelsiek` both import as `Brommelsiek Meeting Room`.
- Imports reject unknown facility names instead of creating new facilities. That prevents accidental extra calendar/search locations.
- Imports do not overwrite internal workflow fields like contract dates, payment date, authorization dates, approval date, refund fields, or notes.
- For V1, a reservation shows in the canceled preview section when the uploaded CSV has `Canceled` set to true and the existing reservation is not already canceled.
- The requested facility names are used: Brommelsiek Meeting Room, Quail Ridge Lodge, New Melle Landhaus, Matson Hill Barn, and Heritage Meeting Room.
- Reservation IDs and household numbers are stored as numbers-only text values because RecTrac IDs may be identifiers rather than values that should be added or calculated.
- The calendar is intentionally one facility at a time and month-only.
- Email buttons generate `.eml` draft files. Opening one should create an email with the renter address, subject, body, and attachment already filled in. V1 intentionally uses `.eml` generation instead of Outlook automation.
- This keeps the app container-only for IT. There is no required PC-side helper, Outlook add-in, browser extension, or Microsoft 365 app registration in V1.
- Downloading an email draft does not mark the email as sent. Staff use the one-click `Mark sent today` buttons after they actually send the email from Outlook.
- Common workflow dates have one-click buttons on the reservation detail page so staff can mark contract sent, contract received, payment received, authorization received, and refund completed without typing today's date.
- Form and import errors show as normal app pages with a short explanation and links back to the dashboard or search page.
- The standard authorization form is stored at `app/static/forms/special-authorization.pdf`.
- Uploaded reservation documents are stored on disk in `storage/reservation_documents/` and tracked in the database.

## Run Locally With Docker

This is the recommended local setup because it starts the database and web app together.

1. Start Docker Desktop.
2. In this folder, run:

```bash
docker compose up --build
```

3. Open the app in a browser:

```text
http://localhost:8000
```

The web container runs the seed script on startup. That script is safe to run repeatedly because it only inserts starter reservations that do not already exist.

To stop the app:

```bash
docker compose down
```

To reset the database completely:

```bash
docker compose down -v
docker compose up --build
```

## Run Locally Without Docker

Use this path only when PostgreSQL and Python are already installed on the machine.

1. Create a PostgreSQL database named `facility_tracker` with user `parks` and password `parks`, or adjust `.env`.
2. Copy the example environment file:

```bash
cp .env.example .env
```

3. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Create tables and load starter data:

```bash
python -m app.seed
```

6. Start the web app:

```bash
uvicorn app.main:app --reload
```

7. Open:

```text
http://localhost:8000
```

## How To Test The V1 Screens

### Dashboard

Open `http://localhost:8000/`. The dashboard shows:

- overdue action count
- due soon action count
- upcoming event count
- the highest-priority open workflow actions
- upcoming authorization email deadlines
- events in the next 14 days
- records missing basic contact/household information
- most recent applied import and a short list of affected records

### Reservation Search

Open `http://localhost:8000/reservations`.

Try searching for:

- `600328`
- `Jenna`
- `11820`
- `555-0119`
- `northsidegarden@example.com`

Use the facility filter and the include canceled checkbox to confirm canceled records are hidden by default.

Use `New reservation` on the search page to create a reservation manually. The manual form validates numeric reservation ID and household number, supports the phone workflow toggle, and opens the new reservation detail page after saving.

### Reservation Detail

Open a reservation from search, calendar, or action queue. From there, staff can edit reservation information, facility, contact information, canceled status, workflow dates, and notes.

For phone reservations, if contract sent is entered and contract due is left blank, the app defaults the due date to 5 business days later.

The reservation page also includes a Documents & Emails section. From there staff can:

- generate the first authorization email with the standard authorization PDF attached
- generate the reminder email with the standard authorization PDF attached
- upload returned or approved authorization documents
- generate the approval email after entering the check-in time and selecting the approved form to attach
- download or delete uploaded documents

The detail page also has one-click workflow buttons so staff do not have to type common dates manually:

- Contract sent today
- Contract received today
- Payment received today
- Authorization received today
- Refund completed today

### Facility Calendar

Open `http://localhost:8000/calendar`.

Use `Brommelsiek Meeting Room` for May 2026. The May 3 day square has two reservations, which confirms the calendar lists multiple same-day entries. Multi-day reservations appear on every day from event date through event end date.

### Action Queue

Open `http://localhost:8000/actions`.

The action queue uses these V1 authorization rules:

- first authorization email due 45 days before the event
- warning starts 5 days before the 45-day deadline
- deadline day and overdue are shown as overdue
- reminder email due 30 days before the event if the authorization form has not been received
- authorization form due 21 days before the event

The seed data includes examples for:

- contract sent but not returned
- payment overdue
- authorization sent but not received
- authorization reminder needed
- approval email needed
- completed event awaiting refund

### Import Preview And Apply

Open `http://localhost:8000/import`.

First upload:

```text
sample_imports/baseline_rectrac_export.csv
```

Because the database starts with matching seed data, this should preview no major changes.

Then upload:

```text
sample_imports/changed_rectrac_export.csv
```

This file intentionally causes:

- one new reservation
- one changed event date
- one changed event end date
- one changed contact phone
- one cancellation

Review the preview page. It shows new records, changed records with before/after values, and canceled records. Use the Apply button only after review.

The preview page also shows the CSV fields included in the import. Existing reservations are only updated for those included fields.

The app also supports the actual RecTrac-style export shape shown in `sample_imports/rectrac_export_example.csv`, including `Reservation Number`, `Facility Location`, `Begin Date`, `End Date`, `Household Number`, `Last Name`, `Primary First Name`, and blank phone/email headers.

## Environment Variables

The app reads these values:

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | PostgreSQL connection string |
| APP_NAME | Text shown in the page header and browser title |
| DUE_SOON_DAYS | Number of days that count as due soon for the general workflow checks |

See `.env.example` for a simple local example.

## Internal Hosting

For internal deployment, IT can run the same Docker image and connect it to a managed or internal PostgreSQL database. They would set `DATABASE_URL` to the production database, keep the app behind the organization’s network or VPN, and add normal internal controls such as backups, HTTPS, authentication, and persistent storage for `storage/reservation_documents/`. V1 intentionally does not include public SaaS features, Outlook automation, or email template management.

### Simple Internal Docker Hosting

The production example keeps the app container-only and does not install anything on staff PCs.

1. Copy the production environment example:

```bash
cp .env.production.example .env.production
```

2. Edit `.env.production` and change `POSTGRES_PASSWORD` and `DATABASE_URL` so the password matches in both places.

3. Start the production-style stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

4. Open the app at the internal server name and port IT chooses.

The production compose file uses two persistent Docker volumes:

- `postgres_data` for the PostgreSQL database
- `reservation_documents` for uploaded reservation documents

The production compose file starts the app without loading starter/test reservation data. On startup, the app still makes sure the five approved facility names exist so staff can create and import reservations.

IT should back up both. If IT uses an external PostgreSQL server instead of the included database container, they can point `DATABASE_URL` at that database and keep persistent storage for uploaded documents.

### Access Control

The app does not manage usernames or passwords. Access control should happen at the internal network, firewall, VPN, IIS, reverse proxy, or web gateway layer.

Recommended simple setup:

- host only on the internal network or VPN
- restrict the URL to a small Parks Department security group
- keep PostgreSQL inaccessible except to the app and server admins

### Backups

Back up these two things:

- PostgreSQL database data
- uploaded files in `storage/reservation_documents/` or the `reservation_documents` Docker volume
