import logging
from celery import shared_task
from apps.counseling.models import Session
from apps.memory.models import Memory, MemoryVector
import openai
from django.conf import settings

logger = logging.getLogger(__name__)

# Constants for semantic deduplication
SEMANTIC_THRESHOLD_REINFORCE = 0.92
SEMANTIC_THRESHOLD_REVIEW = 0.75

SUMMARY_PROMPT = """
You are a clinical documentation assistant for a relationship counseling AI. 
Summarize this session in 3–5 sentences. 
Focus on: (1) the primary emotional theme raised, (2) any communication patterns observed (e.g., criticism, defensiveness, stonewalling, contempt), 
(3) any repair attempts or positive moments, and (4) what the user seemed to need most. 
Do not diagnose. Do not use the partner's name. Write in neutral, compassionate clinical language.

Transcript:
{transcript}
"""

MEMORY_EXTRACTION_PROMPT = """
Extract structured insights from this session transcript. 
For each insight, return a JSON list of objects with the following fields:
- category: one of [attachment_pattern, conflict_trigger, communication_style, recurring_theme, successful_repair, expressed_need]
- content: a single factual sentence
- confidence: 0.0–1.0
- session_context: brief quote or paraphrase

Only include insights with confidence ≥ 0.5. 
Do not infer partner's internal state. Focus on the user's expressed experience only.

Transcript:
{transcript}

Return ONLY the JSON list.
"""


@shared_task(name="counseling.tasks.process_post_session_async")
def process_post_session_async(session_id):
    """Orchestrates post-session processing."""
    try:
        Session.objects.get(id=session_id)
        logger.info(f"Starting post-session processing for session {session_id}")

        # Trigger parallel sub-tasks or run sequentially for MVP simplicity
        generate_session_summary_task.delay(session_id)
        extract_memories_task.delay(session_id)

    except Session.DoesNotExist:
        logger.error(f"Session {session_id} not found for async processing")


@shared_task(name="counseling.tasks.generate_session_summary_task")
def generate_session_summary_task(session_id):
    """Generates an encrypted clinical summary using OpenAI."""
    try:
        session = Session.objects.get(id=session_id)
        transcript = session.decrypted_transcript

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a reasonably fast/cheap model for MVP
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(transcript=transcript),
                }
            ],
            max_tokens=300,
        )

        summary = response.choices[0].message.content.strip()
        session.summary = summary
        session.save()
        logger.info(f"Summary generated for session {session_id}")

    except Exception as e:
        logger.exception(f"Error generating summary for session {session_id}: {e}")


@shared_task(name="counseling.tasks.extract_memories_task")
def extract_memories_task(session_id):
    """Extracts insights and performs semantic deduplication before indexing."""
    try:
        session = Session.objects.get(id=session_id)
        transcript = session.decrypted_transcript
        user = session.user

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # 1. Extract Insights
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": MEMORY_EXTRACTION_PROMPT.format(transcript=transcript),
                }
            ],
            response_format={"type": "json_object"},
        )

        import json

        insights_raw = json.loads(response.choices[0].message.content)
        insights = (
            insights_raw.get("insights", [])
            if isinstance(insights_raw, dict)
            else insights_raw
        )

        for insight in insights:
            content = insight.get("content")
            if not content:
                continue

            # 2. Semantic Deduplication
            # Embed the new insight
            embedding_response = client.embeddings.create(
                input=content, model=settings.EMBEDDING_MODEL
            )
            new_embedding = embedding_response.data[0].embedding

            # Query pgvector for existing similar memories
            # We filter by user to ensure privacy
            # We use the MemoryVector model
            from pgvector.django import CosineDistance

            similar_vector = (
                MemoryVector.objects.filter(user_id=user.id)
                .annotate(distance=CosineDistance("embedding", new_embedding))
                .order_by("distance")
                .first()
            )

            if similar_vector:
                similarity = 1 - similar_vector.distance

                if similarity >= SEMANTIC_THRESHOLD_REINFORCE:
                    # Increment reinforcement count
                    memory = similar_vector.memory
                    memory.reinforcement_count += 1
                    memory.save()
                    logger.info(
                        f"Reinforced existing memory {memory.id} (similarity: {similarity:.4f})"
                    )
                    continue

                elif similarity >= SEMANTIC_THRESHOLD_REVIEW:
                    # Flag for review in metadata but create new
                    insight["flagged_for_review"] = True
                    insight["nearest_neighbor_id"] = str(similar_vector.memory.id)
                    insight["similarity"] = float(similarity)

            # 3. Create New Memory
            metadata = {
                "source_session_id": str(session_id),
                "category": insight.get("category"),
                "confidence": insight.get("confidence"),
                "session_context": insight.get("session_context"),
                **insight.get("metadata", {}),
            }
            if "flagged_for_review" in insight:
                metadata["flagged_for_review"] = True
                metadata["review_similarity"] = insight["similarity"]

            new_memory = Memory.objects.create(
                user=user, content=content, metadata=metadata
            )

            # Create the vector
            MemoryVector.objects.create(
                memory=new_memory,
                user_id=user.id,
                embedding=new_embedding,
                metadata=metadata,
                memory_type=insight.get("category"),
            )
            logger.info(f"Created new memory {new_memory.id} for session {session_id}")

    except Exception as e:
        logger.exception(f"Error extracting memories for session {session_id}: {e}")
