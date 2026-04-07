import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from apps.safety.models import SafetySignal

class SafetySignalModelTest(TestCase):
    def test_create_safety_signal(self):
        signal = SafetySignal.objects.create(
            category="harm",
            phrase="test phrase",
            severity=0.8,
            source="manual"
        )
        self.assertEqual(str(signal), "[harm] test phrase...")
        self.assertIsNotNone(signal.id)

class LoadSafetySignalsCommandTest(TestCase):
    def setUp(self):
        self.mock_data = [
            {"category": "suicide", "phrase": "kill myself", "severity": 0.9, "source": "test_source"}
        ]
        
    @patch("apps.safety.management.commands.load_safety_signals.OpenAI")
    @patch("apps.safety.management.commands.load_safety_signals.os.path.exists")
    @patch("apps.safety.management.commands.load_safety_signals.open", create=True)
    def test_load_safety_signals_success(self, mock_open, mock_exists, mock_openai):
        # Mocking
        mock_exists.return_value = True
        
        # Mock file content
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.__iter__.return_value = [json.dumps(d) for d in self.mock_data]
        
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )
        
        # Run command
        call_command("load_safety_signals")
        
        # Verify
        self.assertEqual(SafetySignal.objects.count(), 1)
        signal = SafetySignal.objects.first()
        self.assertEqual(signal.phrase, "kill myself")
        self.assertEqual(len(signal.embedding), 1536)
        
    @patch("apps.safety.management.commands.load_safety_signals.os.path.exists")
    def test_load_safety_signals_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        # Running command should not raise exit but print error
        call_command("load_safety_signals")
        self.assertEqual(SafetySignal.objects.count(), 0)
