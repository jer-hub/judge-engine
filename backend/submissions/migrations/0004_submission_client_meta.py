from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0003_output_limit_exceeded"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="client_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="user_agent",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
    ]
