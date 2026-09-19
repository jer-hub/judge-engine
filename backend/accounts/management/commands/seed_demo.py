"""Seed a complete demo dataset for classroom walkthroughs."""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contests.models import Contest, ContestParticipant, ContestProblem
from problems.models import Problem, TestCase

User = get_user_model()


PROBLEMS = [
    {
        "slug": "a-plus-b",
        "title": "A Plus B",
        "difficulty": Problem.Difficulty.EASY,
        "tags": "math,beginner",
        "statement": """# A Plus B

Read two integers **a** and **b** and print their sum.

### Input
A single line with two integers `a` and `b` (−1000 ≤ a, b ≤ 1000).

### Output
Print one integer: `a + b`.

### Sample
**Input**
```
1 2
```
**Output**
```
3
```
""",
        "tests": [
            {"order": 1, "is_sample": True, "input_data": "1 2\n", "expected_output": "3\n"},
            {"order": 2, "is_sample": False, "input_data": "10 20\n", "expected_output": "30\n"},
            {"order": 3, "is_sample": False, "input_data": "-5 8\n", "expected_output": "3\n"},
        ],
    },
    {
        "slug": "max-of-two",
        "title": "Maximum of Two",
        "difficulty": Problem.Difficulty.EASY,
        "tags": "math,conditionals",
        "statement": """# Maximum of Two

Read two integers and print the larger one. If equal, print either.

### Input
Two integers on one line.

### Output
The maximum value.

### Sample
**Input**
```
7 3
```
**Output**
```
7
```
""",
        "tests": [
            {"order": 1, "is_sample": True, "input_data": "7 3\n", "expected_output": "7\n"},
            {"order": 2, "is_sample": False, "input_data": "4 9\n", "expected_output": "9\n"},
            {"order": 3, "is_sample": False, "input_data": "5 5\n", "expected_output": "5\n"},
        ],
    },
    {
        "slug": "sum-1-to-n",
        "title": "Sum 1 to N",
        "difficulty": Problem.Difficulty.MEDIUM,
        "tags": "loops,math",
        "statement": """# Sum 1 to N

Given a positive integer **n**, print the sum `1 + 2 + … + n`.

### Input
A single integer `n` (1 ≤ n ≤ 10000).

### Output
The sum.

### Sample
**Input**
```
5
```
**Output**
```
15
```
""",
        "tests": [
            {"order": 1, "is_sample": True, "input_data": "5\n", "expected_output": "15\n"},
            {"order": 2, "is_sample": False, "input_data": "1\n", "expected_output": "1\n"},
            {"order": 3, "is_sample": False, "input_data": "100\n", "expected_output": "5050\n"},
        ],
    },
]

STUDENTS = [
    ("alice", "Alice", "Demo"),
    ("bob", "Bob", "Demo"),
    ("carol", "Carol", "Demo"),
]

DEMO_PASSWORD = "demo123"
DEMO_ADMIN_PASSWORD = "JudgeDev-Admin-ChangeMe!"


class Command(BaseCommand):
    help = "Seed demo users, problems, and a live contest for walkthroughs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo contest/problems with matching slugs before seeding.",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset demo student passwords to the demo default.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding when DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed demo data when DEBUG=False. Pass --force if intentional."
            )

        admin = self._ensure_admin()
        students = self._ensure_students(reset_passwords=options["reset_passwords"])
        problems = self._ensure_problems(admin, reset=options["reset"])
        contest = self._ensure_contest(admin, problems, students, reset=options["reset"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo ready"))
        self.stdout.write("  Frontend:  http://localhost:3000")
        self.stdout.write("  Admin:     http://localhost:8000/admin/")
        self.stdout.write("")
        self.stdout.write("Accounts")
        self.stdout.write(f"  admin / {DEMO_ADMIN_PASSWORD} (only if newly created)")
        for u in students:
            self.stdout.write(f"  {u.username} / {DEMO_PASSWORD} (new users only unless --reset-passwords)")
        self.stdout.write("")
        self.stdout.write(f"Contest: {contest.title} (id={contest.id}, status={contest.status})")
        self.stdout.write("Problems: " + ", ".join(p.slug for p in problems))
        self.stdout.write("")
        self.stdout.write("Walkthrough:")
        self.stdout.write("  1. Log in as alice → Problems → A Plus B → submit sample Java")
        self.stdout.write(f"  2. Contests → {contest.title} → Register → open problem A")
        self.stdout.write("  3. Open Scoreboard and refresh while bob/carol also submit")

    def _ensure_admin(self) -> User:
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@school.local",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password(DEMO_ADMIN_PASSWORD)
            admin.role = User.Role.ADMIN
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(
                self.style.WARNING(f"Created admin / {DEMO_ADMIN_PASSWORD}")
            )
        return admin

    def _ensure_students(self, reset_passwords: bool) -> list[User]:
        users = []
        for username, first, last in STUDENTS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.STUDENT,
                    "class_section": "Demo-A",
                    "school_id": f"DEMO-{username.upper()}",
                },
            )
            user.role = User.Role.STUDENT
            if created or reset_passwords:
                user.set_password(DEMO_PASSWORD)
            user.save()
            users.append(user)
            action = "Created" if created else ("Reset password for" if reset_passwords else "Updated")
            self.stdout.write(self.style.SUCCESS(f"{action} student {username}"))
        return users

    def _ensure_problems(self, admin: User, reset: bool) -> list[Problem]:
        problems = []
        for spec in PROBLEMS:
            if reset:
                Problem.objects.filter(slug=spec["slug"]).delete()
            problem, created = Problem.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "statement": spec["statement"],
                    "difficulty": spec["difficulty"],
                    "tags": spec["tags"],
                    "is_published": True,
                    "time_limit_ms": 2000,
                    "memory_limit_mb": 256,
                    "created_by": admin,
                },
            )
            problem.test_cases.all().delete()
            for tc in spec["tests"]:
                TestCase.objects.create(problem=problem, **tc)
            problems.append(problem)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Created' if created else 'Updated'} problem {problem.slug} "
                    f"({problem.test_cases.count()} tests)"
                )
            )
        return problems

    def _ensure_contest(
        self,
        admin: User,
        problems: list[Problem],
        students: list[User],
        reset: bool,
    ) -> Contest:
        title = "Demo Cup 2026"
        if reset:
            Contest.objects.filter(title=title).delete()

        now = timezone.now()
        contest, created = Contest.objects.update_or_create(
            title=title,
            defaults={
                "description": (
                    "Live demo contest for classroom walkthroughs. "
                    "Solve A–C in Java. Scoreboard updates every few seconds."
                ),
                "start_time": now - timedelta(minutes=5),
                "end_time": now + timedelta(hours=2),
                "is_public": True,
                "freeze_scoreboard_minutes_before_end": 15,
                "created_by": admin,
            },
        )
        contest.contest_problems.all().delete()
        letters = "ABC"
        for i, problem in enumerate(problems):
            ContestProblem.objects.create(
                contest=contest,
                problem=problem,
                letter=letters[i],
                display_order=i,
                points=100,
            )
        for student in students:
            ContestParticipant.objects.get_or_create(contest=contest, user=student)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} contest '{contest.title}' "
                f"with {len(problems)} problems; {len(students)} students registered"
            )
        )
        return contest
