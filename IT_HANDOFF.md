# IT Handoff: Facility Reservation Tracker

This is a small internal web application for the Parks/Recreation reservation workflow. The goal is to give the Recreation Specialist team one place to search reservations, track deadlines, upload related documents, and review RecTrac imports before applying changes.

## What IT Needs To Host

The application is packaged as Docker containers:

- one Python/FastAPI web container
- one PostgreSQL database container
- one persistent document upload volume

Staff should not need anything installed on their computers other than a normal web browser and Outlook for opening downloaded `.eml` email drafts.

## Recommended Simple Access Control

V1 does not include a user account system. Access control should be handled at the network or server layer.

Recommended setup:

- host the app only on the internal network or VPN
- restrict the app URL to the small Parks Department staff group that needs it
- do not expose the PostgreSQL database directly to staff computers
- put HTTPS in front of the app if that matches the internal hosting standard

This keeps the application simple and avoids a separate password system for only a few internal users.

## Production Startup

Copy the production environment example:

```bash
cp .env.production.example .env.production
```

Edit `.env.production`:

- set a real `POSTGRES_PASSWORD`
- make sure the password in `DATABASE_URL` matches
- adjust `APP_PORT` if IT does not want to use port `8000`

Start the production-style stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Then open the app using the internal server name and selected port.

## Persistent Data

The production Docker Compose file creates two persistent volumes:

- `postgres_data`: stores the PostgreSQL database
- `reservation_documents`: stores uploaded reservation documents

Both need to be included in normal server backups.

## Data Notes

The production startup does not load starter/test reservation records. It only makes sure the five approved facility names exist:

- Brommelsiek Meeting Room
- Quail Ridge Lodge
- New Melle Landhaus
- Matson Hill Barn
- Heritage Meeting Room

After that, reservation records are expected to come from RecTrac imports or manual entry.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| POSTGRES_DB | Database name used by the included PostgreSQL container |
| POSTGRES_USER | Database username |
| POSTGRES_PASSWORD | Database password |
| DATABASE_URL | Full database connection string used by the web app |
| APP_NAME | Browser title and application name |
| DUE_SOON_DAYS | Number of days used for due-soon workflow status |
| APP_PORT | Host port exposed by Docker |

## Backups And Maintenance

IT should back up:

- the PostgreSQL database volume
- the reservation document upload volume
- the `.env.production` file, stored securely

Basic maintenance:

- apply normal server operating system updates
- rebuild the containers when application updates are provided
- monitor disk space for the database and document uploads

## What Is Not Included In V1

These items are intentionally not included in V1:

- public access
- self-service renter accounts
- built-in username/password management
- direct Outlook automation
- Microsoft 365 app registration
- editable email template administration

Email drafts are downloaded as `.eml` files so staff can open them in Outlook, review them, add signatures or CCs, and send them manually.
