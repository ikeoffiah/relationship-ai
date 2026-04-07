from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.memory.models import Memory, MemoryVector
import uuid

User = get_user_model()

class MemoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
    def test_memory_creation_and_encryption(self):
        mem = Memory.objects.create(
            user=self.user,
            content="A very secret memory"
        )
        self.assertEqual(str(mem), f"Memory {mem.id} for {self.user.id}")
        
        # Verify encryption
        mem.refresh_from_db()
        self.assertTrue(mem.content.startswith("ENC:"))
        self.assertNotEqual(mem.content, "A very secret memory")
        
        # Verify decryption
        self.assertEqual(mem.decrypted_content, "A very secret memory")

class MemoryVectorModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        self.mem = Memory.objects.create(
            user=self.user,
            content="Source memory"
        )
        
    def test_memory_vector_creation(self):
        vector = MemoryVector.objects.create(
            memory=self.mem,
            user_id=self.user.id,
            zone="public",
            embedding=[0.1] * 1536
        )
        self.assertEqual(str(vector), f"Vector for Memory {self.mem.id}")
        self.assertEqual(vector.zone, "public")
        self.assertEqual(len(vector.embedding), 1536)
