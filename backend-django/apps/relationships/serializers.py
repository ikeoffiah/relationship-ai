from rest_framework import serializers
from .models import Relationship, RelationshipInvite

class RelationshipSerializer(serializers.ModelSerializer):
    partner_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Relationship
        fields = [
            'id', 'status', 'partner_a_id', 'partner_b_id', 
            'invited_at', 'accepted_at', 'partner_display_name'
        ]

    def get_partner_display_name(self, obj):
        # In a real app, we would fetch the partner's name from the User model
        # For now, return a placeholder or handle the logic in the view
        user = self.context.get('request').user
        other_partner_id = obj.partner_b_id if obj.partner_a_id == user.id else obj.partner_a_id
        if not other_partner_id:
            return "Pending Partner"
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            partner = User.objects.get(id=other_partner_id)
            return partner.full_name.split(' ')[0] if partner.full_name else "Partner"
        except User.DoesNotExist:
            return "Partner"

class RelationshipInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipInvite
        fields = ['id', 'relationship', 'inviter_id', 'invitee_email', 'status', 'expires_at']
