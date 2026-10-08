/**
 * Creates the "Judge Engine: student account registration" Google Form and
 * a linked response sheet. Its CSV export imports as-is through
 * Admin → Accounts → Import students from CSV.
 *
 * How to run: see docs/google-forms/README.md. In short: open
 * https://script.google.com, New project, paste this file, edit CONFIG,
 * then Run → createStudentRegistrationForm and allow access.
 *
 * The form never asks for a password. Students get theirs from the teacher
 * (Admin → Accounts → Bulk password reset prints sign-in slips).
 */

const CONFIG = {
  title: 'Judge Engine: student account registration',
  // The dropdown students pick from. Must match how you name sections in the
  // judge, because Bulk password reset works per section.
  sections: ['BSIT-1A', 'BSIT-1B', 'BSIT-2A', 'BSIT-2B'],
  // Require a Google sign-in, record the verified email, and allow one
  // response per account (students can still edit it). Turn off only if
  // your students have no Google accounts.
  requireSignIn: true,
};

function createStudentRegistrationForm() {
  const form = FormApp.create(CONFIG.title);
  form.setDescription(
    'Fill this in once to get your account on the school\'s Java judge.\n' +
      'Your USERNAME will be your School ID. Do not enter any password here: ' +
      'your teacher will give you your password on a sign-in slip.'
  );

  if (CONFIG.requireSignIn) {
    // Verified emails need sign-in; older Apps Script only has setCollectEmail.
    if (form.setEmailCollectionType) {
      form.setEmailCollectionType(FormApp.EmailCollectionType.VERIFIED);
    } else {
      form.setCollectEmail(true);
    }
    form.setLimitOneResponsePerUser(true);
  }
  // Fixing a typo edits the same response instead of adding a second row,
  // which the import would reject as a duplicate username.
  form.setAllowResponseEdits(true);
  form.setConfirmationMessage(
    'Thanks! Your teacher will create your account and give you your password. ' +
      'Your username is the School ID you entered.'
  );

  // Question titles become the CSV column names; the importer recognises
  // these, so do not rename them.
  form
    .addTextItem()
    .setTitle('School ID')
    .setHelpText('This becomes your username. Letters, numbers and . _ - @ + only, no spaces.')
    .setRequired(true)
    .setValidation(
      FormApp.createTextValidation()
        .requireTextMatchesPattern('^[A-Za-z0-9._@+-]{1,150}$')
        .setHelpText('Use only letters, numbers and . _ - @ + (no spaces).')
        .build()
    );
  form.addTextItem().setTitle('Last name').setRequired(true);
  form.addTextItem().setTitle('First name').setRequired(true);
  form
    .addListItem()
    .setTitle('Class section')
    .setChoiceValues(CONFIG.sections)
    .setRequired(true);

  // Collect responses in a sheet: File → Download → CSV gives the import file.
  const sheet = SpreadsheetApp.create(CONFIG.title + ' (responses)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log('Share this link with students: ' + form.getPublishedUrl());
  Logger.log('Edit the form:                ' + form.getEditUrl());
  Logger.log('Responses sheet:              ' + sheet.getUrl());
}
