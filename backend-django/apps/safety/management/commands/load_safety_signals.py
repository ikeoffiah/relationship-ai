import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.safety.models import SafetySignal
from openai import OpenAI


class Command(BaseCommand):
    help = "Load safety signals from JSONL and generate embeddings"

    def handle(self, *args, **options):
        file_path = os.path.join(
            settings.BASE_DIR, "..", "infra", "safety_signals.jsonl"
        )

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = settings.EMBEDDING_MODEL

        with open(file_path, "r") as f:
            for line in f:
                data = json.loads(line)
                phrase = data.get("phrase")
                category = data.get("category")
                severity = data.get("severity", 0.5)
                source = data.get("source", "manual")

                self.stdout.write(f"Processing: {phrase}")

                # Generate embedding
                response = client.embeddings.create(input=[phrase], model=model)
                embedding = response.data[0].embedding

                # Save or update
                SafetySignal.objects.update_or_create(
                    phrase=phrase,
                    defaults={
                        "category": category,
                        "embedding": embedding,
                        "severity": severity,
                        "source": source,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Successfully loaded safety signals."))
