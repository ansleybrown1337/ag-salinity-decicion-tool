# Dependency license review

This preliminary review describes the pinned direct requirements and the dependencies resolved on Windows with Python 3.12.14. License identifiers were checked against installed package metadata and available license files. The repository installs dependencies from their upstream distributions and includes no vendored package code.

| Direct dependency | Role | Upstream license |
| --- | --- | --- |
| Streamlit 1.56.0 | Local application and navigation | [Apache-2.0](https://pypi.org/project/streamlit/1.56.0/) |
| Altair 5.5.0 | Charts | [BSD-3-Clause](https://github.com/vega/altair/blob/v5.5.0/LICENSE) |
| pandas 2.3.3 | Interactive tables and chart data | [BSD-3-Clause](https://github.com/pandas-dev/pandas/blob/v2.3.3/LICENSE) |
| Pydantic 2.12.5 | Input validation and configuration | [MIT](https://github.com/pydantic/pydantic/blob/v2.12.5/LICENSE) |
| ReportLab 4.4.10 | PDF generation | [BSD-3-Clause](https://pypi.org/project/reportlab/4.4.10/) |
| SciPy 1.18.1 | Mixed-integer crop optimization | [BSD-3-Clause and bundled component notices](https://pypi.org/project/scipy/1.18.1/) |
| pytest 9.0.2 | Test runner | [MIT](https://github.com/pytest-dev/pytest/blob/9.0.2/LICENSE) |
| pypdf 6.8.0 | PDF validation in tests | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/6.8.0/LICENSE) |

## Resolved transitive dependencies

The following groups summarize package-level licenses from the tested environment. Wheels can contain additional components with independent license or notice terms. The [constraints file](../constraints.txt) pins the transitive versions from this review while dependency metadata selects the packages applicable to each platform.

| License | Packages in the tested environment |
| --- | --- |
| Apache-2.0 | pyarrow 26.0.1, pydeck 0.9.3, requests 2.34.2, tenacity 9.2.1, tornado 6.6.1, tzdata 2026.6, watchdog 6.0.0 |
| MIT | annotated-types 0.8.0, attrs 26.1.0, blinker 1.9.0, cachetools 7.3.3, charset-normalizer 3.5.2, iniconfig 2.3.1, jsonschema 4.26.0, jsonschema-specifications 2025.9.1, narwhals 2.29.0, pluggy 1.7.0, pydantic-core 2.41.5, pytz 2026.6, referencing 0.37.0, rpds-py 2026.9.1, toml 0.10.2, typing-inspection 0.4.5, urllib3 2.8.0 |
| BSD-3-Clause | click 8.5.1, colorama 0.4.6, gitdb 4.0.12, GitPython 3.2.1, idna 3.20, Jinja2 3.1.6, MarkupSafe 3.0.4, protobuf 7.36.2, python-dateutil 4.0.0, smmap 5.0.3 |
| BSD-2-Clause | Pygments 2.21.0 |
| Apache-2.0 OR BSD-2-Clause | packaging 26.3 |
| MPL-2.0 | certifi 2026.10.23 CA certificate bundle |
| MIT-CMU | Pillow 12.3.0 |
| PSF-2.0 | typing-extensions 4.16.0 |
| BSD-3-Clause and component terms | NumPy 2.5.5 declares BSD-3-Clause, 0BSD, MIT, Zlib, and CC0-1.0. See its wheel’s license directory and bundled binary notices. |

## Compatibility and release decisions

The proposed `GPL-2.0-or-later` grant applies to original application code. The FSF identifies Apache-2.0 as compatible with GPLv3 and incompatible with GPLv2. When distributing a combined work that requires compatibility with Apache-2.0, the later-version option allows use of GPLv3 for the covered combination. [GNU license list, Apache-2.0](https://www.gnu.org/licenses/license-list.html#apache2)

Before publication, confirm the LLC’s copyright ownership, the grant and compatibility treatment for the intended distribution format, and the applicability of MPL or wheel component terms in any bundled release. If distributing wheels, a frozen executable, a container, or bundled frontend assets, inventory that exact build and preserve upstream license files, copyright notices, and applicable Apache NOTICE and MPL obligations. Source-only distribution with dependency installation instructions has a different package inventory from a bundled release.

The crop and efficiency tables contain attributed numeric facts and concise endpoint descriptions. Third-party publications, figures, and logos are not bundled. Obtain authorization for any separately protected branding assets added to a release.
