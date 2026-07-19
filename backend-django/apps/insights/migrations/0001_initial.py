from django.db import migrations, models
import uuid
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('relationships', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RelationshipInsight',
            fields=[
                ('insight_id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('type', models.CharField(max_length=30, choices=[
                    ('perception_gap', 'Perception Gap'),
                    ('recurring_theme', 'Recurring Conflict Theme'),
                    ('needs_gap', 'Emotional Needs Gap'),
                    ('progress', 'Progress / Positive Signal'),
                    ('flourishing_pattern', 'Flourishing Pattern'),
                ])),
                ('theme', models.TextField(blank=True)),
                ('confidence', models.FloatField()),
                ('a_narrative_summary', models.TextField(blank=True)),
                ('b_narrative_summary', models.TextField(blank=True)),
                ('synthesis', models.TextField(blank=True)),
                ('suggested_intervention', models.TextField(blank=True)),
                ('session_evidence', models.JSONField(default=list, blank=True)),
                ('shared_with_a', models.BooleanField(default=False)),
                ('shared_with_b', models.BooleanField(default=False)),
                ('approved_for_joint', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(null=True, blank=True)),
                ('relationship', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='insights', to='relationships.Relationship')),
            ],
            options={
                'db_table': 'relationship_insights',
                'indexes': [models.Index(fields=['relationship', 'type'], name='idx_insight_rel_type')],
            },
        ),
    ]
