from django.db import migrations, models


class Migration(migrations.Migration):
    """Partner invites on calendar items.

    Existing rows default to "none", which keeps their current behaviour of
    reminding both partners. Backfilling them to "accepted" would have been
    tidier as a state machine and dishonest as a record — nobody accepted
    anything they were never shown.
    """

    dependencies = [("engagement", "0017_widen_blissitem_source")]

    operations = [
        migrations.AddField(
            model_name="blissitem",
            name="partner_invite",
            field=models.CharField(
                choices=[
                    ("none", "Not tagged"),
                    ("pending", "Waiting on partner"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="none",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="blissitem",
            name="partner_responded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
