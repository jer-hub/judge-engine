from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from problems.management.commands.seed_icpc_davao import build_specs, _load_meta
from problems.models import Problem


EXPECTED_SLUGS = [
    "durian-stall-ledger",
    "jeepney-signboard-codes",
    "cooperative-ledger-periods",
    "kadayawan-cup-scoreboard",
    "samal-ferry",
    "flash-flood-matina",
    "davao-river-toll-passes",
    "smx-hall-bookings",
    "barangay-health-hub",
    "agdao-market-price-board",
]


class SeedIcpcDavaoTests(TestCase):
    def test_seeds_ten_problems_idempotently(self):
        call_command("seed_icpc_davao", stdout=StringIO())
        call_command("seed_icpc_davao", "--draft", stdout=StringIO())
        problems = Problem.objects.filter(tags__contains="icpc-davao")
        self.assertEqual(problems.count(), 10)
        self.assertEqual(
            set(problems.values_list("slug", flat=True)),
            set(EXPECTED_SLUGS),
        )
        for problem in problems:
            self.assertFalse(problem.is_published)
            self.assertIn("public class Solution", problem.statement)
            cases = list(problem.test_cases.order_by("order"))
            self.assertGreaterEqual(len(cases), 5, problem.slug)
            sample_count = sum(1 for c in cases if c.is_sample)
            self.assertGreaterEqual(sample_count, 2, problem.slug)
            self.assertTrue(all(c.is_sample for c in cases[:sample_count]), problem.slug)
            self.assertTrue(all(not c.is_sample for c in cases[sample_count:]), problem.slug)
            for sample in cases[:sample_count]:
                self.assertTrue(sample.input_data.endswith("\n"), problem.slug)
                self.assertTrue(sample.expected_output.endswith("\n"), problem.slug)
                self.assertIn(sample.input_data, problem.statement)
                self.assertIn(sample.expected_output, problem.statement)

    def test_solvers_match_every_json_sample(self):
        meta = {row["letter"]: row for row in _load_meta()}
        letter_by_slug = {
            "durian-stall-ledger": "A",
            "jeepney-signboard-codes": "B",
            "cooperative-ledger-periods": "C",
            "kadayawan-cup-scoreboard": "D",
            "samal-ferry": "E",
            "flash-flood-matina": "F",
            "davao-river-toll-passes": "G",
            "smx-hall-bookings": "H",
            "barangay-health-hub": "I",
            "agdao-market-price-board": "J",
        }
        for spec in build_specs():
            letter = letter_by_slug[spec.slug]
            for i, sample in enumerate(meta[letter]["samples"], 1):
                inp = sample["input"] if sample["input"].endswith("\n") else sample["input"] + "\n"
                exp = sample["output"] if sample["output"].endswith("\n") else sample["output"] + "\n"
                self.assertEqual(spec.solve(inp), exp, f"{spec.slug} sample {i}")

    def test_seed_demo_flag_adds_the_published_set(self):
        call_command("seed_demo", force=True, stdout=StringIO())
        self.assertFalse(Problem.objects.filter(tags__contains="icpc-davao").exists())
        out = StringIO()
        call_command("seed_demo", force=True, icpc_davao=True, stdout=out)
        problems = Problem.objects.filter(tags__contains="icpc-davao")
        self.assertEqual(problems.filter(is_published=True).count(), 10)
        self.assertIn("ICPC Davao training problems", out.getvalue())
