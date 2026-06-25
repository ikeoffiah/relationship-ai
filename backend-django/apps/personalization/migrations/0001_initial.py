from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('onboarding_completed', models.BooleanField(default=False)),
                ('onboarding_completed_at', models.DateTimeField(blank=True, null=True)),
                ('rsq_responses', models.JSONField(blank=True, default=dict)),
                ('attachment_style', models.CharField(blank=True, max_length=50)),
                ('attachment_style_source', models.CharField(blank=True, max_length=50)),
                ('attachment_assessed_at', models.DateTimeField(blank=True, null=True)),
                ('relationship_stage', models.CharField(blank=True, max_length=50)),
                ('relationship_duration_months', models.IntegerField(blank=True, null=True)),
                ('cohabiting', models.BooleanField(blank=True, null=True)),
                ('children_count', models.IntegerField(default=0)),
                ('reason_for_using', models.CharField(blank=True, max_length=200)),
                ('cultural_background', models.CharField(blank=True, max_length=255)),
                ('religious_values', models.CharField(blank=True, max_length=255)),
                ('communication_style_preference', models.CharField(blank=True, max_length=50)),
                ('family_community_orientation', models.CharField(blank=True, max_length=50)),
                ('communication_style_quiz_responses', models.JSONField(blank=True, default=dict)),
                ('communication_style_self_report', models.CharField(blank=True, max_length=50)),
                ('prompt_modifiers', models.JSONField(blank=True, default=dict)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='personalization_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'personalization_profiles',
            },
        ),
    ]
