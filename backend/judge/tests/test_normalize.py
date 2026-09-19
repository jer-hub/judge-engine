from django.test import SimpleTestCase

from judge.executor import normalize_output


class NormalizeOutputTests(SimpleTestCase):
    def test_trims_trailing_whitespace_and_newlines(self):
        self.assertEqual(normalize_output("1 2\n"), normalize_output("1 2"))
        self.assertEqual(normalize_output("a  \n\n"), "a")

    def test_preserves_internal_blank_lines(self):
        self.assertEqual(normalize_output("a\n\nb\n"), "a\n\nb")
