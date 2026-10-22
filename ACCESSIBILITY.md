
# Accessibility

ETLRelay aims to make its documentation, command-line interface,
and contribution process accessible to a broad range of users
and contributors.

Accessibility is considered part of the project's usability and
maintainability.

## Project scope

ETLRelay is a Python library with a command-line interface and
documentation website.

It does not currently provide a graphical user interface.

The primary accessibility considerations are:

- Readable, structured documentation.
- Clear command-line messages and diagnostic output.
- Text-based examples that do not depend on visual presentation.
- Consistent terminology and descriptive error messages.
- Accessible contribution and issue-reporting processes.

## Documentation

ETLRelay documentation is maintained using Markdown and MkDocs.

Contributions should aim to:

- Use descriptive headings with a logical hierarchy.
- Provide meaningful text for links.
- Include alternative descriptions for informative images.
- Avoid relying exclusively on colour to communicate information.
- Keep examples understandable without requiring visual context.
- Use readable tables and code examples where appropriate.

Accessibility improvements to the documentation are welcome.

## Command-line interface

ETLRelay provides text-based CLI commands for configuration validation,
pipeline execution, version reporting, and help.

CLI output should remain understandable through terminal-based and
assistive technologies where practical.

Normal command output and operational diagnostics are separated
between stdout and stderr.

Error messages should provide useful context without requiring
users to interpret colour or other presentation effects.

## Known limitations

ETLRelay has not undergone a comprehensive independent accessibility
audit or formal conformance assessment against WCAG or another
accessibility standard.

The accessibility of rendered documentation may also depend on
MkDocs, the selected theme, browsers, and assistive technologies.

No claim of complete accessibility or formal certification is made.

## Reporting accessibility issues

Accessibility problems can be reported through
[GitHub Issues](https://github.com/apaquette/ETLRelay/issues).

Please include:

- The affected documentation page, CLI command, or project feature.
- A description of the accessibility barrier.
- Steps to reproduce the issue, where applicable.
- Relevant browser, terminal, operating-system, or assistive
  technology information, if you are comfortable sharing it.

You do not need to disclose a disability or personal medical
information to report an accessibility issue.

Accessibility reports and improvements will be considered alongside
other project maintenance priorities. No fixed remediation timeline
is guaranteed.

## Contributions

Contributions that improve accessibility, documentation clarity,
and usability are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and
contribution guidelines.
