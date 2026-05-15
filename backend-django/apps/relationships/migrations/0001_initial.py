import django.db.models.deletion
import uuid
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('partner_a_id', models.UUIDField(db_index=True)),
                ('partner_b_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('dissolved', 'Dissolved')], default='pending', max_length=20)),
                ('invited_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('dissolved_at', models.DateTimeField(blank=True, null=True)),
                ('dissolved_by', models.UUIDField(blank=True, null=True)),
            ],
            options={
                'db_table': 'relationships',
            },
        ),
        migrations.CreateModel(
            name='RelationshipInvite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('inviter_id', models.UUIDField()),
                ('invitee_email', models.EmailField(max_length=254)),
                ('token', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('expired', 'Expired'), ('revoked', 'Revoked')], default='pending', max_length=20)),
                ('relationship', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='relationships.relationship')),
            ],
            options={
                'db_table': 'relationship_invites',
            },
        ),
        migrations.AddConstraint(
            model_name='relationship',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'active')), fields=('partner_a_id',), name='unique_active_relationship_a'),
        ),
        migrations.AddConstraint(
            model_name='relationship',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'active')), fields=('partner_b_id',), name='unique_active_relationship_b'),
        ),
    ]
