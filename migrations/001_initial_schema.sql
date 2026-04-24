CREATE TABLE IF NOT EXISTS facilities (
    facility_id VARCHAR(30) PRIMARY KEY,
    facility_name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    reservation_id VARCHAR(40) NOT NULL UNIQUE,
    facility_id VARCHAR(30) NOT NULL REFERENCES facilities(facility_id),
    booking_type VARCHAR(20) NOT NULL,
    booking_date DATE,
    event_date DATE NOT NULL,
    event_end_date DATE,
    household_number VARCHAR(40),
    reservee_name VARCHAR(120) NOT NULL,
    phone VARCHAR(40),
    email VARCHAR(160),
    cancelled BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    contract_sent_date DATE,
    contract_due_date DATE,
    contract_received_date DATE,
    payment_received_date DATE,
    auth_sent_date DATE,
    auth_due_date DATE,
    auth_received_date DATE,
    auth_reminder_date DATE,
    approval_sent_date DATE,
    refund_sent_date DATE,
    refund_completed BOOLEAN NOT NULL DEFAULT false,
    last_sync_action VARCHAR(160),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_reservations_reservation_id ON reservations(reservation_id);
CREATE INDEX IF NOT EXISTS ix_reservations_facility_id ON reservations(facility_id);
CREATE INDEX IF NOT EXISTS ix_reservations_event_date ON reservations(event_date);
CREATE INDEX IF NOT EXISTS ix_reservations_household_number ON reservations(household_number);
CREATE INDEX IF NOT EXISTS ix_reservations_reservee_name ON reservations(reservee_name);
CREATE INDEX IF NOT EXISTS ix_reservations_phone ON reservations(phone);
CREATE INDEX IF NOT EXISTS ix_reservations_email ON reservations(email);

CREATE TABLE IF NOT EXISTS import_previews (
    id SERIAL PRIMARY KEY,
    token VARCHAR(80) NOT NULL UNIQUE,
    filename VARCHAR(255) NOT NULL,
    source_rows JSONB NOT NULL,
    preview JSONB NOT NULL,
    added_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    canceled_count INTEGER NOT NULL DEFAULT 0,
    applied BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_import_previews_token ON import_previews(token);

CREATE TABLE IF NOT EXISTS import_logs (
    id SERIAL PRIMARY KEY,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    filename VARCHAR(255) NOT NULL,
    added_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    canceled_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS reservation_documents (
    id SERIAL PRIMARY KEY,
    reservation_id VARCHAR(40) NOT NULL REFERENCES reservations(reservation_id) ON DELETE CASCADE,
    document_type VARCHAR(80) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(120),
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_reservation_documents_reservation_id ON reservation_documents(reservation_id);
