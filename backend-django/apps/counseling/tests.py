import json
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.counseling.models import Session
from apps.counseling.tasks import (
    extract_memories_task,
    generate_session_summary_task,
    process_post_session_async,
)
from apps.memory.models import Memory, MemoryVector
from apps.relationships.models import Relationship

User = get_user_model()


class CounselingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="modeluser", email="model@example.com", password="password"
        )
        self.relationship = Relationship.objects.create(
            user=self.user, name="Model Relationship"
        )

    def test_session_str(self):
        session = Session.objects.create(
            user=self.user,
            relationship=self.relationship,
            status=Session.Status.ACTIVE,
        )
        self.assertEqual(str(session), f"Session {session.id} (active)")

    def test_session_encryption_on_save(self):
        transcript = "Top secret message"
        summary = "Clinical summary"
        session = Session.objects.create(
            user=self.user,
            relationship=self.relationship,
            transcript=transcript,
            summary=summary,
        )
        # Verify encryption
        self.assertTrue(session.transcript.startswith("ENC:"))
        self.assertTrue(session.summary.startswith("ENC:"))
        self.assertEqual(session.decrypted_transcript, transcript)
        self.assertEqual(session.decrypted_summary, summary)


class EndSessionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="viewuser", email="view@example.com", password="password"
        )
        self.client.force_authenticate(user=self.user)
        self.relationship = Relationship.objects.create(
            user=self.user, name="View Relationship"
        )
        self.url = "/api/counseling/sessions/end/"

    @patch("apps.counseling.views.process_post_session_async.delay")
    def test_end_session_success(self, mock_task):
        data = {
            "relationship_id": str(self.relationship.id),
            "transcript": "Full session transcript content",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Session.objects.count(), 1)
        session = Session.objects.first()
        self.assertEqual(session.status, Session.Status.COMPLETED)
        mock_task.assert_called_once_with(session.id)

    def test_end_session_missing_data(self):
        response = self.client.post(self.url, {"transcript": "missing id"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_session_invalid_relationship(self):
        data = {
            "relationship_id": str(uuid.uuid4()),
            "transcript": "invalid relationship",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.counseling.views.Relationship.objects.get")
    def test_end_session_internal_error(self, mock_get):
        mock_get.side_effect = Exception("System crash")
        data = {
            "relationship_id": str(self.relationship.id),
            "transcript": "trigger error",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class CounselingTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="taskuser", email="task@example.com", password="password"
        )
        self.relationship = Relationship.objects.create(
            user=self.user, name="Task Relationship"
        )
        self.session = Session.objects.create(
            user=self.user,
            relationship=self.relationship,
            transcript="I feel happy today.",
            status=Session.Status.COMPLETED,
        )

    @patch("apps.counseling.tasks.generate_session_summary_task.delay")
    @patch("apps.counseling.tasks.extract_memories_task.delay")
    def test_process_post_session_async(self, mock_extract, mock_summary):
        process_post_session_async(self.session.id)
        mock_summary.assert_called_once_with(self.session.id)
        mock_extract.assert_called_once_with(self.session.id)

    @patch("apps.counseling.tasks.logger")
    def test_process_post_session_not_found(self, mock_logger):
        process_post_session_async(uuid.uuid4())
        mock_logger.error.assert_called()

    @patch("openai.OpenAI")
    def test_generate_session_summary_task(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Short summary"
        mock_client.chat.completions.create.return_value = mock_response

        generate_session_summary_task(self.session.id)

        self.session.refresh_from_db()
        self.assertEqual(self.session.decrypted_summary, "Short summary")

    @patch("openai.OpenAI")
    def test_extract_memories_task_new_memory(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock chat completion response (insights)
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps(
            {
                "insights": [
                    {"content": "New insight", "category": "theme", "confidence": 0.9}
                ]
            }
        )
        mock_client.chat.completions.create.return_value = mock_chat_response

        # Mock embedding response
        mock_emb_response = MagicMock()
        mock_emb_response.data = [MagicMock()]
        mock_emb_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_emb_response

        extract_memories_task(self.session.id)

        self.assertEqual(Memory.objects.count(), 1)
        self.assertEqual(MemoryVector.objects.count(), 1)
        memory = Memory.objects.first()
        self.assertEqual(memory.decrypted_content, "New insight")

    @patch("openai.OpenAI")
    def test_extract_memories_task_reinforcement(self, mock_openai):
        # Setup existing memory
        existing_memory = Memory.objects.create(
            user=self.user, content="Existing fact", reinforcement_count=1
        )
        MemoryVector.objects.create(
            memory=existing_memory,
            user_id=self.user.id,
            embedding=[0.1] * 1536,
        )

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock chat completion (same content)
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps(
            [{"content": "Existing fact", "category": "theme", "confidence": 0.9}]
        )
        mock_client.chat.completions.create.return_value = mock_chat_response

        # Mock embedding (exact match distance=0, similarity=1)
        mock_emb_response = MagicMock()
        mock_emb_response.data = [MagicMock()]
        mock_emb_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_emb_response

        extract_memories_task(self.session.id)

        existing_memory.refresh_from_db()
        self.assertEqual(existing_memory.reinforcement_count, 2)
        # Should not create a new memory
        self.assertEqual(Memory.objects.count(), 1)

    @patch("openai.OpenAI")
    def test_extract_memories_task_review_flag(self, mock_openai):
        # Setup existing memory
        existing_memory = Memory.objects.create(
            user=self.user, content="Similar fact", reinforcement_count=1
        )
        # Something close but not identical
        MemoryVector.objects.create(
            memory=existing_memory,
            user_id=self.user.id,
            embedding=[0.1] * 1536,
        )

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock chat completion
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps(
            [
                {
                    "content": "Somewhat similar fact",
                    "category": "theme",
                    "confidence": 0.9,
                }
            ]
        )
        mock_client.chat.completions.create.return_value = mock_chat_response

        # Mock embedding with distance 0.2 (similarity 0.8)
        # Threshold for REVIEW is 0.75, reinforcement is 0.92
        mock_emb_response = MagicMock()
        mock_emb_response.data = [MagicMock()]
        mock_emb_response.data[0].embedding = [0.11] * 1536  # Slightly different
        mock_client.embeddings.create.return_value = mock_emb_response

        # We need to ensure the query returns a distance in the 0.75-0.92 range
        # CosineDistance is 1 - CosineSimilarity. Similarity 0.8 -> Distance 0.2
        with patch("apps.counseling.tasks.MemoryVector.objects.filter") as mock_filter:
            mock_queryset = MagicMock()
            mock_ann = MagicMock()
            mock_order = MagicMock()
            mock_vector = MagicMock()
            mock_vector.distance = 0.2
            mock_vector.memory = existing_memory

            mock_filter.return_value = mock_queryset
            mock_queryset.annotate.return_value = mock_ann
            mock_ann.order_by.return_value = mock_order
            mock_order.first.return_value = mock_vector

            extract_memories_task(self.session.id)

        new_memory = Memory.objects.exclude(id=existing_memory.id).first()
        self.assertTrue(new_memory.metadata.get("flagged_for_review"))

    @patch("openai.OpenAI")
    def test_extract_memories_task_empty_insight(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock chat completion (one empty insight, one valid)
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps(
            [
                {"category": "theme"},  # missing content
                {"content": "Valid", "category": "theme", "confidence": 0.9},
            ]
        )
        mock_client.chat.completions.create.return_value = mock_chat_response

        # Mock embedding
        mock_emb_response = MagicMock()
        mock_emb_response.data = [MagicMock()]
        mock_emb_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_emb_response

        extract_memories_task(self.session.id)

        # Only the valid one should be created
        self.assertEqual(Memory.objects.count(), 1)

    @patch("apps.counseling.tasks.logger")
    def test_tasks_error_handling(self, mock_logger):
        # Test generate_session_summary_task error
        generate_session_summary_task(uuid.uuid4())  # Non-existent ID
        self.assertTrue(mock_logger.exception.called)

        # Test extract_memories_task error
        extract_memories_task(uuid.uuid4())  # Non-existent ID
        self.assertTrue(mock_logger.exception.called)
