from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from problems.management.commands.seed_number_theory import build_specs
from problems.models import Problem

# Sample outputs printed in "Number Theory Problem Set in Java".
FROM_THE_PDF = {
    "big-powers": "1024\n1\n1\n",
    "fractions-mod-prime": "833333340\n",
    "factor-queries": "2^2 3^1\n97^1\n1\n",
    "divisor-report": "6 28 4\n1 1 1\n2 98 96\n",
    "balance-the-scale": "3 -1\n-1\n0 0\n",
    "secret-number": "23\n",
    "grid-paths": "6\n4\n1\n",
    "coprime-pairs": "1\n3\n19\n63\n",
}


class SeedNumberTheoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_number_theory", stdout=StringIO())

    def test_eight_problems_with_two_visible_samples_each(self):
        problems = Problem.objects.filter(tags__contains="number-theory")
        self.assertEqual(problems.count(), 8)
        for problem in problems:
            self.assertTrue(problem.is_published)
            cases = list(problem.test_cases.order_by("order"))
            self.assertEqual([c.is_sample for c in cases[:2]], [True, True], problem.slug)
            self.assertTrue(all(not c.is_sample for c in cases[2:]), problem.slug)
            self.assertGreaterEqual(len(cases) - 2, 3, problem.slug)  # hidden tests
            for sample in cases[:2]:
                self.assertIn(sample.input_data, problem.statement)
                self.assertIn(sample.expected_output, problem.statement)

    def test_first_sample_matches_the_pdf(self):
        for slug, expected in FROM_THE_PDF.items():
            first = Problem.objects.get(slug=slug).test_cases.order_by("order").first()
            self.assertEqual(first.expected_output, expected, slug)

    def test_rerun_as_draft_updates_in_place(self):
        call_command("seed_number_theory", "--draft", stdout=StringIO())
        problems = Problem.objects.filter(tags__contains="number-theory")
        self.assertEqual(problems.count(), 8)
        self.assertFalse(problems.filter(is_published=True).exists())

    def test_secret_number_inputs_respect_the_constraints(self):
        import math

        spec = next(s for s in build_specs() if s.slug == "secret-number")
        for inp in spec.samples + spec.hidden:
            nums = [int(x) for x in inp.split()]
            pairs = list(zip(nums[1::2], nums[2::2]))
            self.assertEqual(len(pairs), nums[0])
            lcm = 1
            for a, m in pairs:
                self.assertTrue(1 <= m <= 10**9 and 0 <= a < m)
                lcm = lcm * m // math.gcd(lcm, m)
            if spec.solve(inp) != "-1\n":
                self.assertLessEqual(lcm, 10**18)
