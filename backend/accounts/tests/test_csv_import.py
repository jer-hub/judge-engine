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

    def test_missing_username_and_school_id_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_roster_csv("first_name,password\nAlice,pass12345\n")
        self.assertIn("username", str(ctx.exception).lower())

    def test_password_column_is_optional(self):
        rows = parse_roster_csv("username\nalice\n")
        self.assertEqual(rows[0].data, {"username": "alice"})
        self.assertIsNone(rows[0].error)

    def test_google_forms_export_maps_question_titles(self):
        csv_text = (
            '"Timestamp","Email Address","School ID","Last name","First name","Class section"\n'
            '"2026/10/08 9:01:12 AM GMT+8","juan@school.edu","2026-00101","Dela Cruz","Juan","BSIT-1A"\n'
        )
        rows = parse_roster_csv(csv_text)
        self.assertEqual(
            rows[0].data,
            {
                "email": "juan@school.edu",
                "school_id": "2026-00101",
                "last_name": "Dela Cruz",
                "first_name": "Juan",
                "class_section": "BSIT-1A",
                # No username column: the school ID is the username.
                "username": "2026-00101",
            },
        )

    def test_header_aliases(self):
        rows = parse_roster_csv("Student No.,Surname,Given Name,Section,E-mail\nS1,Tan,Al,7A,a@x.edu\n")
        self.assertEqual(
            rows[0].data,
            {"school_id": "S1", "last_name": "Tan", "first_name": "Al",
             "class_section": "7A", "email": "a@x.edu", "username": "S1"},
        )

    def test_row_without_username_or_school_id_is_an_error(self):
        rows = parse_roster_csv("username,school_id,first_name\n,,Alice\nbob,,Bob\n")
        self.assertIn("Missing username", rows[0].error)
        self.assertIsNone(rows[1].error)

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

    def test_rejects_nul_characters(self):
        # PostgreSQL rejects NUL in text, which used to 500 the import.
        with self.assertRaisesMessage(ValueError, "NUL"):
            parse_roster_csv("username,password\nal\x00ice,Secret-Pass-1\n")
