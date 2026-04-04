"""Seed the database with CSV data from seeds/ directory.

Usage: uv run python scripts/seed.py
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from peewee import PostgresqlDatabase

from app.database import db
from app.models import Event, Url, User
from playhouse.shortcuts import chunked

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def init_database():
    database = PostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=os.environ.get("DATABASE_PASSWORD", "postgres"),
    )
    db.initialize(database)
    db.connect()
    db.create_tables([User, Url, Event])


def parse_datetime(value):
    return datetime.strptime(value, DATETIME_FMT)


def seed_users():
    with open(SEEDS_DIR / "users.csv") as f:
        reader = csv.DictReader(f)
        rows = [
            {
                "id": int(row["id"]),
                "username": row["username"],
                "email": row["email"],
                "created_at": parse_datetime(row["created_at"]),
            }
            for row in reader
        ]
    # Deduplicate by id (keep last occurrence for each id)
    seen_usernames = {}
    deduped = []
    for row in rows:
        username = row["username"]
        if username in seen_usernames:
            # Keep both rows but make the duplicate username unique
            row["username"] = f"{username}_{row['id']}"
        seen_usernames[username] = True
        deduped.append(row)

    with db.atomic():
        for batch in chunked(deduped, 100):
            User.insert_many(batch).execute()
    print(f"  Imported {len(deduped)} users")


def seed_urls():
    with open(SEEDS_DIR / "urls.csv") as f:
        reader = csv.DictReader(f)
        rows = [
            {
                "id": int(row["id"]),
                "user_id": int(row["user_id"]),
                "short_code": row["short_code"],
                "original_url": row["original_url"],
                "title": row["title"],
                "is_active": row["is_active"] == "True",
                "created_at": parse_datetime(row["created_at"]),
                "updated_at": parse_datetime(row["updated_at"]),
            }
            for row in reader
        ]
    with db.atomic():
        for batch in chunked(rows, 100):
            Url.insert_many(batch).execute()
    print(f"  Imported {len(rows)} urls")


def seed_events():
    with open(SEEDS_DIR / "events.csv") as f:
        reader = csv.DictReader(f)
        rows = [
            {
                "id": int(row["id"]),
                "url_id": int(row["url_id"]),
                "user_id": int(row["user_id"]),
                "event_type": row["event_type"],
                "timestamp": parse_datetime(row["timestamp"]),
                "details": row["details"],  # Already JSON string
            }
            for row in reader
        ]
    with db.atomic():
        for batch in chunked(rows, 100):
            Event.insert_many(batch).execute()
    print(f"  Imported {len(rows)} events")


def main():
    print("Initializing database...")
    init_database()

    # Drop and recreate for clean seed
    print("Dropping existing tables...")
    db.drop_tables([Event, Url, User])
    db.create_tables([User, Url, Event])

    print("Seeding data...")
    seed_users()
    seed_urls()
    seed_events()

    # Reset PostgreSQL sequences after explicit ID inserts
    print("Resetting sequences...")
    for model, table in [(User, "users"), (Url, "urls"), (Event, "events")]:
        db.execute_sql(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"(SELECT COALESCE(MAX(id), 0) FROM {table}))"
        )

    print("Done!")
    db.close()


if __name__ == "__main__":
    main()
