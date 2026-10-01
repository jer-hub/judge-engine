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

    def test_tiptap_output_survives_unchanged(self):
        # Exactly what the admin editor saves (captured from a browser session).
        tiptap = (
            "<h2>Title</h2><p>Read <strong>two</strong> and <em>sum</em>.</p>"
            "<ul><li><p>first</p></li></ul><ol start=\"3\"><li><p>third</p></li></ol>"
            "<blockquote><p>Note</p></blockquote>"
            "<pre><code>Scanner s = new Scanner(System.in);\n</code></pre>"
            '<p>See <a target="_blank" rel="noopener noreferrer nofollow" '
            'href="https://example.com">the docs</a>.</p>'
            "<p><strong>Constraints</strong></p><ul><li><p>1 &lt;= n &lt;= 100</p></li></ul>"
        )
        self.assertEqual(sanitize_statement(tiptap), tiptap)

    def test_markdown_statement_is_untouched(self):
        md = "> Read **n** then `a < b`\n\n- item & more\n\n```java\nif (a > b) {}\n```"
        self.assertEqual(sanitize_statement(md), md)
        p = Problem.objects.create(title="Y", statement=md)
        p.refresh_from_db()
        self.assertEqual(p.statement, md)
