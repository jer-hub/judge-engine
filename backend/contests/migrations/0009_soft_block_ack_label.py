from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0008_contest_is_archived"),
    ]

    operations = [
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
                    ("soft_block_ack", "Teacher unlock"),
                ],
                max_length=32,
            ),
        ),
    ]
