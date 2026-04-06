import os
import django
import sys
from pathlib import Path
import uuid

# Add the project root to the sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.models import User  # noqa: E402
from apps.memory.models import Memory  # noqa: E402
from django.db import connection  # noqa: E402


def run_verification():
    print("--- Starting Final Encryption Verification (HKDF + UUID) ---")

    # 1. Create a Test User
    email = "test_uuid_user@example.com"
    username = "testuuiduser"
    if User.objects.filter(email=email).exists():
        User.objects.filter(email=email).delete()

    user = User.objects.create_user(
        username=username, email=email, password="testpassword123"
    )
    print(f"User created: {user.email} (ID: {user.id})")

    # Verify ID is a UUID
    if isinstance(user.id, uuid.UUID):
        print("Success: User ID is a UUID.")
    else:
        print(f"Error: User ID is {type(user.id)}, expected UUID.")
        return

    # 2. Create Encrypted Data
    original_content = (
        "This is a very sensitive relationship memory for the final spec."
    )
    memory = Memory.objects.create(user=user, content=original_content)
    print(f"Memory created ID: {memory.id}")

    # 3. Check Raw Data in Database (Should be encrypted)
    with connection.cursor() as cursor:
        # Use the spec table name: user_memories
        cursor.execute("SELECT content FROM user_memories WHERE id = %s", [memory.id])
        raw_db_content = cursor.fetchone()[0]

    print(f"Raw database content: {raw_db_content}")

    if raw_db_content == original_content:
        print("Error: Database content is NOT encrypted!")
    else:
        print("Success: Database content is encrypted ciphertext.")

    # 4. Verify Automatic Decryption Property
    decrypted = memory.decrypted_content
    print(f"Decrypted content (via property): {decrypted}")

    if decrypted == original_content:
        print("Success: Decrypted property matches original content!")
    else:
        print(f"Error: Decryption failed! Got: {decrypted}")

    print("--- Verification Complete ---")


if __name__ == "__main__":
    run_verification()
