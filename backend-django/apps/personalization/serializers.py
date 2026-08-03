from rest_framework import serializers
from apps.personalization.models import UserProfile
from apps.personalization.tasks import (
    calculate_rsq_attachment_style,
    calculate_communication_style,
    build_modifiers
)
from django.utils import timezone


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'email',
            'onboarding_completed',
            'onboarding_completed_at',
            'rsq_responses',
            'attachment_style',
            'attachment_style_source',
            'attachment_assessed_at',
            'relationship_stage',
            'relationship_duration_months',
            'cohabiting',
            'children_count',
            'reason_for_using',
            'cultural_background',
            'religious_values',
            'communication_style_preference',
            'family_community_orientation',
            'communication_style_quiz_responses',
            'communication_style_self_report',
            'prompt_modifiers',
        ]
        read_only_fields = [
            'id',
            'email',
            'onboarding_completed',
            'onboarding_completed_at',
            'attachment_style',
            'attachment_style_source',
            'attachment_assessed_at',
            'communication_style_self_report',
            'prompt_modifiers',
        ]

    def update(self, instance, validated_data):
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Synchronously compute the fields on save for immediate client response
        if instance.rsq_responses:
            style, _ = calculate_rsq_attachment_style(instance.rsq_responses)
            # `style` is None when the answers do not distinguish a prototype —
            # too few items, or a tie at the top. The column is a non-null
            # CharField, and every reader guards on falsiness, so the empty
            # string is the right storage for "we looked and could not say".
            instance.attachment_style = style or ''
            instance.attachment_style_source = 'rsq_onboarding' if style else ''
            if not instance.attachment_assessed_at:
                instance.attachment_assessed_at = timezone.now()

        if instance.communication_style_quiz_responses:
            comm_style = calculate_communication_style(instance.communication_style_quiz_responses)
            instance.communication_style_self_report = comm_style

        instance.prompt_modifiers = build_modifiers(instance)

        # Mark onboarding completed if all sections are completed.
        #
        # Gated on the questionnaire having been *answered*, not on a prototype
        # having been assigned. Those came apart the moment the scorer learned
        # to say "I cannot tell": a couple whose answers tie would otherwise
        # finish every screen and never be marked complete, looping them back
        # into onboarding for ever. Completing a section is something the user
        # does; assigning a prototype is something we may fail to do.
        if (instance.rsq_responses and instance.relationship_stage and
                instance.cultural_background and instance.communication_style_self_report):
            if not instance.onboarding_completed:
                instance.onboarding_completed = True
                instance.onboarding_completed_at = timezone.now()

        instance.save()
        return instance
