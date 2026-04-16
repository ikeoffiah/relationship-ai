from rest_framework import serializers
from .models import UserConsent


class UserConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConsent
        fields = [
            "id",
            "user_id",
            "relationship_id",
            "session_transcript_retention",
            "cross_partner_insight_sharing",
            "joint_session_participation",
            "shared_relationship_context",
            "therapist_summary_access",
            "model_improvement_data",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "updated_at"]

    def update(self, instance, validated_data):
        # Extract non-model-field arguments passed via serializer.save()
        session_context = validated_data.pop("session_context", None)
        updated_by = validated_data.pop("updated_by", None)

        # Standard update logic
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if updated_by:
            instance.updated_by = updated_by

        # Explicitly pass session_context to the model's save() method
        instance.save(session_context=session_context)
        return instance
