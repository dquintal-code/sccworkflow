# Staff Walkthrough Notes

This walkthrough was completed with starter/test records only. No live Parks reservation data is needed for this check.

## Dashboard

Items checked:

- The dashboard opens from the Home link.
- The top summary counts are visible for overdue actions, due-soon actions, and upcoming events.
- The Needs Attention table links directly to reservation detail pages.
- Upcoming Events shows near-term reservations.
- Problem Records calls out missing contact or household information.
- Recent Import shows the latest applied import summary when import history exists.

Result:

- The dashboard works as a daily starting point.
- It does not duplicate the full action queue because it only shows the highest-priority items and recent activity.

## Reservation Search

Items checked:

- Search page opens from the Search link.
- Keyword search supports reservation ID, reservee name, household number, phone, and email.
- Facility filtering is available.
- Reservation date filtering finds reservations active on that date, including multi-day reservations where the selected date is between the start and end dates.
- Canceled reservations are hidden unless Include canceled is selected.
- Results link to the reservation detail page.
- A New reservation button is available for manual entry.

Result:

- This is still the main working screen for finding records quickly.
- The one-date reservation filter matches the requested behavior.

## Reservation Detail

Items checked:

- Staff can edit reservation ID, facility, household number, booking date, event date, event end date, reservee name, phone, email, canceled status, notes, and workflow fields.
- Reservation ID and household number are numeric-only.
- The phone workflow is controlled by a sliding toggle.
- Phone workflow fields are hidden unless the toggle is enabled.
- Contract due date defaults to 5 business days after contract sent when it is left blank.
- One-click workflow buttons are available for common updates:
  - Contract sent today
  - Contract received today
  - Payment received today
  - Authorization received today
  - Refund completed today
- Delete reservation requires a browser confirmation.

Result:

- The page supports both imported reservations and manually created records.
- The one-click workflow buttons reduce manual date typing.

## Documents And Emails

Items checked:

- Documents and email tools are separated into a top tab instead of being buried in the main form.
- Staff can upload returned authorization forms, approved authorization forms, signed contracts, payment receipts, insurance certificates, and other supporting files.
- Authorization, reminder, and approval email draft buttons generate `.eml` files.
- Email draft download does not automatically mark the email as sent.
- Separate Mark sent today buttons update the matching workflow date after staff send the message from Outlook.

Result:

- The email process stays simple for IT because it does not need Outlook automation or Microsoft 365 permissions.
- Staff still control the final email before sending.

## Facility Calendar

Items checked:

- Calendar opens from Event Calendar.
- Calendar is month view only.
- Calendar shows one facility at a time.
- Canceled reservations are hidden by default.
- Multi-day reservations appear on each day from event date through event end date.
- Multiple reservations on the same day appear together in the day square.
- Calendar entries link to the reservation detail page.

Result:

- The calendar matches the requested facility-by-facility workflow and does not collapse overlapping reservations.

## Action Queue

Items checked:

- Action Queue opens from the top navigation.
- Canceled reservations do not appear.
- Rows show reservation ID, facility, reservee name, event date, phone workflow type, next action, due date, days until due, and status.
- Overdue and due-soon status colors are visible.
- Authorization deadlines follow the current V1 rules:
  - first authorization email due 45 days before the event
  - due-soon warning starts 5 days before that deadline
  - reminder email due 30 days before the event if the authorization form has not been received
  - authorization form due 21 days before the event

Result:

- This is the strongest workflow-tracking view in the app.
- It gives staff a practical list of what needs attention next.

## Import / Sync

Items checked:

- Import page accepts CSV uploads.
- Uploads go to preview first.
- Preview shows counts for new, changed, and canceled reservations.
- Preview shows which CSV fields are included and can update existing reservations.
- Changed records show before/after field values.
- Applying an import requires confirmation.
- Internal workflow fields are not overwritten by RecTrac imports.
- Missing CSV columns are ignored instead of blanking existing fields.
- Facility names are normalized to the five approved facility names and unknown facilities are rejected.

Result:

- The import flow protects existing workflow notes and dates.
- Staff can review what will happen before applying changes.

## Current Usability Notes

- The app is ready for a small internal V1 review using non-sensitive test data.
- Before production use, IT still needs to decide the internal URL, access restriction method, backup method, and whether HTTPS is required on the internal server.
- Real RecTrac exports should be tested only in an approved environment that is allowed to contain Parks reservation data.
