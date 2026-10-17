import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0004_clarifications"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="integrity_monitoring",
            field=models.BooleanField(
                default=True,
                help_text="Log focus/paste signals and show them to admins (warn-only; never auto-penalize).",
            ),
        ),
        migrations.CreateModel(
            name="ContestIntegrityEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("visibility_hidden", "Tab hidden"),
                            ("visibility_visible", "Tab visible"),
                            ("window_blur", "Window blur"),
                            ("window_focus", "Window focus"),
                            ("editor_paste", "Editor paste"),
                        ],
                        max_length=32,
                    ),
                ),
                ("count", models.PositiveIntegerField(default=1)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "contest",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integrity_events",
                        to="contests.contest",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contest_integrity_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["contest", "user", "event_type", "created_at"],
                        name="contests_in_contest_8f3a1b_idx",
                    ),
                ],
            },
        ),
    ]
