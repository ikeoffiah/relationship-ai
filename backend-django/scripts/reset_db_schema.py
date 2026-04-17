import os
import django
import sys
from pathlib import Path

# Add the project root to the sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402


def reset_schema():
    with connection.cursor() as cursor:
        print("Dropping schema public CASCADE...")
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        print("Creating schema public...")
        cursor.execute("CREATE SCHEMA public;")
        print("Granting permissions...")
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")

        print("Enabling pgvector extension...")
        # Note: In Supabase, you might need to enable it in the extensions schema or just public.
        # The spec says CREATE EXTENSION IF NOT EXISTS vector;
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        print("Database schema reset and pgvector enabled successfully.")


if __name__ == "__main__":
    reset_schema()
