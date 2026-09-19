from django.db import migrations

from problems.tags import normalize_tags


def forwards(apps, schema_editor):
    Problem = apps.get_model("problems", "Problem")
    for problem in Problem.objects.all().iterator():
        normalized = normalize_tags(problem.tags)
        if normalized != problem.tags:
            problem.tags = normalized
            problem.save(update_fields=["tags"])


def backwards(apps, schema_editor):
    # Normalization is lossy (lowercasing / dedupe); reverse is a no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("problems", "0002_problem_limits_and_points"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
