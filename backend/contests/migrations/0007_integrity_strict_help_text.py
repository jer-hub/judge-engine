# Generated manually — AlterField help_text only (teacher unlock wording).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0006_integrity_strict"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contest",
            name="integrity_strict",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Require fullscreen and soft-block submit until a teacher "
                    "unlocks the student."
                ),
            ),
        ),
    ]
