from django.db import migrations

MIN_TIME_LIMIT_MS = 1000  # problems.constants at the time of 0005


def clamp_time_limits(apps, schema_editor):
    """0005 raised the minimum to 1000 ms (JVM startup alone takes ~0.5 s)
    but left older problems below it, so correct solutions there TLE and the
    problem cannot be saved until the limit is fixed by hand."""
    Problem = apps.get_model("problems", "Problem")
    Problem.objects.filter(time_limit_ms__lt=MIN_TIME_LIMIT_MS).update(
        time_limit_ms=MIN_TIME_LIMIT_MS
    )


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0005_min_time_limit_1000"),
    ]

    operations = [
        migrations.RunPython(clamp_time_limits, migrations.RunPython.noop),
    ]
