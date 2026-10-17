from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0007_integrity_strict_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="is_archived",
            field=models.BooleanField(
                default=False,
                help_text="Hidden from students; admins can still manage or permanently delete.",
            ),
        ),
    ]
