# Contributing to Ag Salinity Manager

Open an issue with a reproducible example, expected behavior, actual behavior, application version, and Python version. Use the demonstration farm or fabricated inputs when sharing field and water data. For scientific discrepancies, provide the exact equation or table, units, and page or section from an authoritative source.

Use a branch for your change and run `python -m pytest` before opening a pull request. Explain the management implications if your change alters calculated outcomes. Include before and after values, an explanation of the difference, and how you verified it. Add an automated regression test for scientific or persistence changes and a source citation or derivation for any altered scientific assumption. Update the methods and references together so the app, report, and documentation stay aligned.

For an interface change, verify setup, navigation, and related exports with the demonstration farm. For a report change, inspect a rendered multipage example. Preserve existing plan versions or document and test their migration. Keep farm data, credentials, and generated reports out of submissions.

Use the project copyright and SPDX format on original Python contributions and preserve third-party notices where applicable. See [README.md](README.md) for setup and [docs/dependency-licenses.md](docs/dependency-licenses.md) for release review.
