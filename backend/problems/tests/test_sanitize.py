from django.test import TestCase

from problems.models import Problem
from problems.sanitize import sanitize_statement


class StatementSanitizeTests(TestCase):
    def test_html_statement_is_cleaned_on_save(self):
        p = Problem.objects.create(
            title="X",
            statement=(
                '<p onclick="steal()">Sum <strong>two</strong> numbers.</p>'
                "<script>alert(1)</script>"
                '<a href="javascript:alert(1)">bad</a>'
                '<a href="https://example.com" target="_blank">ok</a>'
                '<img src="x" onerror="alert(1)">'
                '<pre class="ql-syntax">int x = 1;</pre>'
            ),
        )
        p.refresh_from_db()
        s = p.statement
        self.assertIn("<strong>two</strong>", s)
        self.assertIn('<a href="https://example.com" target="_blank">ok</a>', s)
        self.assertIn('<pre class="ql-syntax">', s)
        for bad in ("onclick", "<script", "javascript:", "<img", "onerror"):
            self.assertNotIn(bad, s)

    def test_markdown_statement_is_untouched(self):
        md = "> Read **n** then `a < b`\n\n- item & more\n\n```java\nif (a > b) {}\n```"
        self.assertEqual(sanitize_statement(md), md)
        p = Problem.objects.create(title="Y", statement=md)
        p.refresh_from_db()
        self.assertEqual(p.statement, md)
