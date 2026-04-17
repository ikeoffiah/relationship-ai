from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.relationships.models import Relationship, RelationshipNote

User = get_user_model()


class RelationshipModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="password123"
        )

    def test_relationship_creation_and_encryption(self):
        rel = Relationship.objects.create(
            user=self.user, name="Brother", description="My older brother"
        )
        self.assertEqual(str(rel), f"Brother ({self.user.id})")

        # Verify encryption (description should be encrypted in DB)
        # We need to refresh from DB to see the raw value
        rel.refresh_from_db()
        self.assertNotEqual(rel.description, "My older brother")
        self.assertTrue(rel.description.startswith("ENC:"))

        # Verify decryption
        self.assertEqual(rel.decrypted_description, "My older brother")


class RelationshipNoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="password123"
        )
        self.rel = Relationship.objects.create(
            user=self.user, name="Wife", description="My loving wife"
        )

    def test_note_creation_and_encryption(self):
        note = RelationshipNote.objects.create(
            relationship=self.rel, content="Our anniversary is coming up"
        )
        self.assertIn(str(self.rel.id), str(note))

        # Verify encryption
        note.refresh_from_db()
        self.assertNotEqual(note.content, "Our anniversary is coming up")
        self.assertTrue(note.content.startswith("ENC:"))

        # Verify decryption
        self.assertEqual(note.decrypted_content, "Our anniversary is coming up")
