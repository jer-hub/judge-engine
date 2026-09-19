from django.test import SimpleTestCase

from accounts.csv_import import MAX_ROWS, parse_roster_csv


class ParseRosterCsvTests(SimpleTestCase):
    def test_normalizes_headers_and_strips_bom(self):
        csv_text = "\ufeffUsername, Password, school_id\nalice,pass12345,S1\n"
        rows = parse_roster_csv(csv_text)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].error)
        self.assertEqual(rows[0].line_no, 2)
        self.assertEqual(
            rows[0].data,
            {
                "username": "alice",
                "password": "pass12345",
                "school_id": "S1",
            },
        )

    def test_missing_password_header_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_roster_csv("username\nalice\n")
        self.assertIn("password", str(ctx.exception).lower())

    def test_skips_blank_lines_and_keeps_file_line_numbers(self):
        csv_text = (
            "username,password\n"
            "alice,pass12345\n"
            "\n"
            "  \n"
            "bob,pass12345\n"
        )
        rows = parse_roster_csv(csv_text)
        self.assertEqual([r.line_no for r in rows], [2, 5])
        self.assertEqual([r.data["username"] for r in rows], ["alice", "bob"])

    def test_in_file_duplicate_username_flags_second_row(self):
        csv_text = (
            "username,password\n"
            "alice,pass12345\n"
            "alice,otherpass9\n"
        )
        rows = parse_roster_csv(csv_text)
        self.assertIsNone(rows[0].error)
        self.assertIsNotNone(rows[1].error)
        self.assertIn("duplicate", rows[1].error.lower())

    def test_rejects_too_many_rows(self):
        lines = ["username,password"]
        for i in range(MAX_ROWS + 1):
            lines.append(f"u{i},pass12345")
        with self.assertRaises(ValueError) as ctx:
            parse_roster_csv("\n".join(lines) + "\n")
        self.assertIn(str(MAX_ROWS), str(ctx.exception))

    def test_rejects_oversized_text(self):
        with self.assertRaises(ValueError):
            parse_roster_csv("x" * 100_001)
