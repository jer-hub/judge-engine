# Student registration with Google Forms

Students fill in a Google Form. You download its responses as CSV and import that file into the judge as-is. Passwords never go through Google: you hand them out with **Bulk password reset**.

## 1. Create the form (once)

1. Open <https://script.google.com> while signed in to the school Google account that should own the form, and click **New project**.
2. Replace the editor's contents with [`student-registration.gs`](student-registration.gs).
3. Edit `CONFIG` at the top:
   - `sections`: the class sections students choose from. Use exactly the names you'll use in the judge, because password slips are printed per section.
   - `requireSignIn`: keep `true` if students have school Google accounts. It records each student's verified email and allows one response per student, while still letting them edit it.
4. Choose **createStudentRegistrationForm** in the toolbar and click **Run**. Allow the access it asks for (creating a form and a sheet in your Drive).
5. Open **Execution log**. It prints three links: the form link to share with students, the edit link, and the responses sheet.

The form asks for:

| Question | Becomes |
|---|---|
| Email (collected automatically when sign-in is on) | `email` |
| School ID (required; letters, numbers and `. _ - @ +`) | `school_id` and the **username** |
| Last name | `last_name` |
| First name | `first_name` |
| Class section (dropdown) | `class_section` |

Don't rename the questions. The judge maps these titles to account fields. Other columns, such as Google's Timestamp, are ignored.

## 2. Export the responses

When students are done, open the responses sheet and choose **File → Download → Comma-separated values (.csv)**. (In the form, **Responses → ⋮ → Download responses (.csv)** gives the same file inside a zip.)

## 3. Import into the judge

1. Sign in as a teacher and open **Admin → Accounts → Import students from CSV**.
2. Click **Upload .csv** and choose the downloaded file.
3. Click **Preview** and fix anything listed under errors, for example a School ID that is already taken, or two responses with the same School ID.
4. Click **Import**. Every account is a student account. School IDs that already exist are skipped and those accounts are left unchanged.

The CSV has no passwords, so each new account gets a random password that nobody knows. The import result reminds you how many accounts need one.

## 4. Give students their passwords

Open **Admin → Accounts → Bulk password reset**, enter a section (e.g. `BSIT-1A`) and confirm. You get each student's new password once, to print as sign-in slips or download as CSV. Students sign in with their **School ID** and that password.

## Limits

- One import takes up to 500 rows (about 100 KB). Split bigger rosters by section.
- A School ID becomes the username, so it can't contain spaces. The form's validation already enforces this.
