from rest_framework import serializers
from .models import Therapist, TherapistConnection, TherapistStrategyNote
from django.contrib.auth import authenticate

class TherapistLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        try:
            therapist = user.therapist_profile
        except Therapist.DoesNotExist:
            raise serializers.ValidationError('User is not a therapist')
        attrs['user'] = user
        attrs['therapist'] = therapist
        return attrs

class TherapistConnectionSerializer(serializers.ModelSerializer):
    therapist = serializers.PrimaryKeyRelatedField(read_only=True)
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    # The client's consent belongs to the client. It was a writable field, so
    # a therapist could POST consent_client=true and manufacture a
    # fully-consented connection to any user without their involvement.
    consent_client = serializers.BooleanField(read_only=True)

    class Meta:
        model = TherapistConnection
        fields = ['id', 'therapist', 'client', 'consent_therapist', 'consent_client', 'created_at', 'updated_at']

class ClientListSerializer(serializers.ModelSerializer):
    client_id = serializers.IntegerField(source='client.id')
    client_email = serializers.EmailField(source='client.email')
    consent_therapist = serializers.BooleanField()
    consent_client = serializers.BooleanField()

    class Meta:
        model = TherapistConnection
        fields = ['client_id', 'client_email', 'consent_therapist', 'consent_client']

class TherapistStrategyNoteSerializer(serializers.ModelSerializer):
    # Set from the authenticated therapist and the validated client in the
    # view; declaring them writable invited a payload override.
    therapist = serializers.PrimaryKeyRelatedField(read_only=True)
    client = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TherapistStrategyNote
        fields = ['id', 'therapist', 'client', 'note', 'created_at']
