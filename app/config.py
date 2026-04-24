import os

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://parks:parks@localhost:5432/facility_tracker",
)
APP_NAME = os.getenv("APP_NAME", "Facility Reservation Tracker")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Chicago")
DUE_SOON_DAYS = int(os.getenv("DUE_SOON_DAYS", "3"))
MAX_DOCUMENT_UPLOAD_MB = int(os.getenv("MAX_DOCUMENT_UPLOAD_MB", "10"))
MAX_IMPORT_UPLOAD_MB = int(os.getenv("MAX_IMPORT_UPLOAD_MB", "5"))
