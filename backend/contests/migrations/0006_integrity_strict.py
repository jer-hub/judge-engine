from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0005_integrity_monitoring"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="integrity_strict",
            field=models.BooleanField(
                default=False,
                help_text="Require fullscreen and soft-block submit until the student acknowledges after leaving focus.",
            ),
        ),
        migrations.AddField(
            model_name="contestparticipant",
            name="integrity_blocked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contestparticipant",
            name="integrity_ack_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="contestparticipant",
            name="integrity_focus_since_ack",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="contestparticipant",
            name="integrity_paste_since_ack",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="contestintegrityevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("visibility_hidden", "Tab hidden"),
                    ("visibility_visible", "Tab visible"),
                    ("window_blur", "Window blur"),
                    ("window_focus", "Window focus"),
                    ("editor_paste", "Editor paste"),
                    ("fullscreen_exit", "Fullscreen exit"),
                    ("fullscreen_enter", "Fullscreen enter"),
                    ("soft_block_ack", "Soft-block acknowledgment"),
                ],
                max_length=32,
            ),
        ),
    ]
