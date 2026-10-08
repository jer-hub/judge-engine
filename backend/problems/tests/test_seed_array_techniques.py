from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from problems.management.commands.seed_array_techniques import build_specs, solve_pair
from problems.models import Problem


class SeedArrayTechniquesTests(TestCase):
    def test_seeds_ten_problems_idempotently(self):
        call_command("seed_array_techniques", stdout=StringIO())
        call_command("seed_array_techniques", "--draft", stdout=StringIO())
        problems = Problem.objects.filter(tags__contains="array-techniques")
        self.assertEqual(problems.count(), 10)
        for problem in problems:
            self.assertFalse(problem.is_published)  # the second run left them as drafts
            cases = list(problem.test_cases.order_by("order"))
            self.assertGreaterEqual(len(cases), 6)
            self.assertEqual([c.is_sample for c in cases].count(True), 1)
            self.assertTrue(cases[0].is_sample)
            # The statement shows exactly the sample the judge uses.
            self.assertIn(cases[0].input_data, problem.statement)
            self.assertIn(cases[0].expected_output, problem.statement)

    def test_balanced_pair_tests_have_at_most_one_answer(self):
        # The judge compares exact output, so "print any pair" must be unambiguous.
        spec = next(s for s in build_specs() if s.slug == "balanced-pair")
        for inp in [spec.sample, *spec.hidden]:
            nums = [int(x) for x in inp.split()]
            n = nums[0]
            a, target = nums[1 : 1 + n], nums[1 + n]
            seen, pairs = {}, 0
            for x in a:
                pairs += seen.get(target - x, 0)
                seen[x] = seen.get(x, 0) + 1
            self.assertLessEqual(pairs, 1, inp[:60])
            self.assertEqual(solve_pair(inp) == "-1 -1\n", pairs == 0)
