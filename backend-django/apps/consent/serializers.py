from rest_framework import serializers
from apps.consent.models import UserConsent, ConsentChangeLog
from apps.consent.constants import CONSENT_PLAIN_LANGUAGE_MAP
from apps.relationships.models import Relationship

class ConsentSerializer(serializers.ModelSerializer):
    plain_language_summary = serializers.SerializerMethodField()

    class Meta:
        model = UserConsent
        fields = [
            'user_id',
            'session_transcript_retention',
            'cross_partner_insight_sharing',
            'joint_session_participation',
            'shared_relationship_context',
            'therapist_summary_access',
            'model_improvement_data',
            'updated_at',
            'plain_language_summary'
        ]
        read_only_fields = ['user_id', 'updated_at']

    def get_plain_language_summary(self, obj):
        return {
            'session_transcript_retention': CONSENT_PLAIN_LANGUAGE_MAP['session_transcript_retention'][obj.session_transcript_retention],
            'cross_partner_insight_sharing': CONSENT_PLAIN_LANGUAGE_MAP['cross_partner_insight_sharing'][obj.cross_partner_insight_sharing],
            'joint_session_participation': CONSENT_PLAIN_LANGUAGE_MAP['joint_session_participation'][obj.joint_session_participation],
            'shared_relationship_context': CONSENT_PLAIN_LANGUAGE_MAP['shared_relationship_context'][obj.shared_relationship_context],
            'therapist_summary_access': CONSENT_PLAIN_LANGUAGE_MAP['therapist_summary_access'][obj.therapist_summary_access],
            'model_improvement_data': CONSENT_PLAIN_LANGUAGE_MAP['model_improvement_data'][obj.model_improvement_data],
        }

    def validate(self, data):
        user = self.context['request'].user
        
        # Rule: joint_session_participation: enrolled requires the user to have a linked partner
        new_joint = data.get('joint_session_participation')
        new_shared = data.get('shared_relationship_context')
        
        needs_partner = (new_joint == 'enrolled' or 
                         (new_shared and new_shared != 'not_participating'))
        
        if needs_partner:
            from django.db.models import Q
            relationship_exists = Relationship.objects.filter(
                (Q(partner_a_id=user.id) | Q(partner_b_id=user.id)) & 
                Q(status='active')
            ).exists()
            
            if not relationship_exists:
                raise serializers.ValidationError({
                    "relationship": "Participation requires an active relationship link. Please link with a partner first."
                })

        # Rule: model_improvement_data: true requires explicit user acknowledgment
        if data.get('model_improvement_data') is True:
            ack = self.context['request'].data.get('model_improvement_acknowledged')
            if ack is not True:
                raise serializers.ValidationError({
                    "model_improvement_acknowledged": "You must acknowledge that your data will be used for model improvement."
                })

        return data

class ConsentChangeLogSerializer(serializers.ModelSerializer):
    plain_language = serializers.SerializerMethodField()

    class Meta:
        model = ConsentChangeLog
        fields = ['dimension', 'old_value', 'new_value', 'changed_at', 'plain_language']

    def get_plain_language(self, obj):
        # Generate a human-readable string for the history entry
        dim_label = obj.dimension.replace('_', ' ')
        
        # Try to get labels for values if they are choices
        def get_val_label(dim, val):
            if val in ['True', 'False']:
                bool_val = val == 'True'
                return "Enabled" if bool_val else "Disabled"
            return val.replace('_', ' ').capitalize()

        old_label = get_val_label(obj.dimension, obj.old_value)
        new_label = get_val_label(obj.dimension, obj.new_value)
        
        return f"You changed {dim_label} from '{old_label}' to '{new_label}'."
