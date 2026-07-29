from django.db import migrations, models


class Migration(migrations.Migration):
    """'couple_chat' is 11 characters and the column was varchar(10).

    Worth noting how this got in: the suite runs against SQLite, which does not
    enforce varchar length, so the model tests passed while Postgres rejected
    every insert with StringDataRightTruncation. Only an end-to-end run against
    the real stack caught it.
    """

    dependencies = [("engagement", "0016_focussession")]

    operations = [
        migrations.AlterField(
            model_name="blissitem",
            name="source",
            field=models.CharField(default="bliss", max_length=20),
        ),
    ]
