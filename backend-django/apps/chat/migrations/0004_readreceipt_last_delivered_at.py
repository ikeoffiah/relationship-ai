from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0003_threadsummary")]

    operations = [
        migrations.AddField(
            model_name="readreceipt",
            name="last_delivered_at",
            # Nullable rather than backfilled from last_read_at: a thread that
            # predates delivery tracking should admit it does not know, and show
            # one tick, instead of asserting a delivery that was never observed.
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
