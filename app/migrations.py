from pathlib import Path

from sqlalchemy import inspect, text

from app.database import engine


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
MIGRATION_TABLE = "schema_migrations"
BASELINE_TABLES = {
    "facilities",
    "reservations",
    "import_previews",
    "import_logs",
    "reservation_documents",
}


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations() -> None:
    files = migration_files()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        existing_tables = set(inspect(connection).get_table_names())
        applied_versions = {
            row[0]
            for row in connection.execute(
                text(f"SELECT version FROM {MIGRATION_TABLE} ORDER BY version")
            ).all()
        }

        if not applied_versions and BASELINE_TABLES.issubset(existing_tables):
            baseline = files[0].name if files else None
            if baseline:
                connection.execute(
                    text(
                        f"""
                        INSERT INTO {MIGRATION_TABLE} (version)
                        VALUES (:version)
                        ON CONFLICT (version) DO NOTHING
                        """
                    ),
                    {"version": baseline},
                )
                applied_versions.add(baseline)

        for path in files:
            if path.name in applied_versions:
                continue
            with connection.connection.cursor() as cursor:
                cursor.execute(path.read_text())
            connection.execute(
                text(
                    f"""
                    INSERT INTO {MIGRATION_TABLE} (version)
                    VALUES (:version)
                    """
                ),
                {"version": path.name},
            )


if __name__ == "__main__":
    apply_migrations()
    print("Migrations applied.")
