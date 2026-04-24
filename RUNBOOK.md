# Runbook: Facility Reservation Tracker

This runbook is the quick maintenance reference for the app. The goal is to make it easy to start, stop, update, and troubleshoot the system without having to relearn the whole project.

## Purpose

This app is an internal reservation workflow tracker for the Parks/Recreation team. It runs as:

- one FastAPI web container
- one PostgreSQL database container
- one persistent document storage volume

The production deployment is based on `docker-compose.prod.yml`.

Schema changes are managed through the SQL files in `migrations/`.

## Main Files

- `docker-compose.prod.yml`: production container setup
- `.env.production`: production environment settings
- `README.md`: project overview and setup notes
- `IT_HANDOFF.md`: hosting/access notes for IT
- `app/main.py`: main application routes and page actions
- `app/models.py`: database table definitions
- `storage/reservation_documents/`: uploaded files when using local storage

## Standard Production Commands

All production commands below assume the current working directory is the project folder.

Start or rebuild the application:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Stop the application:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

Restart only the web container:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart web
```

Check running containers:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

View web logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs web
```

View database logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs db
```

Run migrations manually:

```bash
python -m app.migrations
```

## Update Process

Use this process for application updates:

1. Pull or copy the latest project code onto the server.
2. Review any changes to `.env.production` if there are new settings.
3. Rebuild and restart the containers:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

4. Open the app in a browser and confirm the main screens load:
   - dashboard
   - search
   - calendar
   - action queue
   - import page

## Data Location

There are two important data areas in production:

- PostgreSQL data in the `postgres_data` Docker volume
- uploaded documents in the `reservation_documents` Docker volume

The application code itself is separate from those volumes. Rebuilding the web container should not remove reservation data or uploaded files as long as those volumes are preserved.

## Backups

At minimum, backups should include:

- the PostgreSQL database volume
- the uploaded document volume
- the `.env.production` file, stored securely
- the source code repository

If a restore is ever needed, both the database and the uploaded document volume need to be restored together so reservation records still match the file list in the app.

## Basic Health Check

To confirm the system is up after a restart or update, check:

1. containers are running
2. the dashboard loads
3. the reservation search page loads
4. the action queue loads
5. the import page loads
6. document downloads still work for an existing test record

## Common Problems

### The app page does not load

Check:

- `docker compose --env-file .env.production -f docker-compose.prod.yml ps`
- `docker compose --env-file .env.production -f docker-compose.prod.yml logs web`

Most likely causes:

- web container did not start
- bad environment variable
- database is not available yet

### The web container starts but pages error out

Check:

- `DATABASE_URL` in `.env.production`
- database container status
- web logs

### Uploaded documents are missing

Check:

- the `reservation_documents` volume still exists
- the container is mounting that volume correctly
- the files were included in backup/restore work

### Reservation data is missing

Check:

- the `postgres_data` volume still exists
- the database container is healthy
- the correct `.env.production` file is being used

## What V1 Does Not Include

These items are not included in V1:

- built-in user accounts
- Outlook automation
- editable email template administration
- public access

That means access control needs to happen outside the app, and email sending still depends on staff opening the generated `.eml` files in Outlook.

## Handoff Notes

If this project changes hands later, start with these files:

- `README.md`
- `IT_HANDOFF.md`
- this runbook
- `app/main.py`
- `app/models.py`
- `app/services/workflow.py`
- `app/services/imports.py`

That is enough to understand how the app runs, where the data lives, and how the core workflow logic works.
