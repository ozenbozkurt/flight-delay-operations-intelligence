# Contributing

Start by running the synthetic demo described in the README. No flight data
download, paid account, API key, or Windows installation is required.

## Development

```sh
python -m venv .venv
# Activate .venv using the command for your operating system.
python -m pip install -e ".[charts]"
python -m unittest discover -s tests -v
```

Discuss substantial changes in an issue before implementation. Describe the
user problem, a small example, and expected results. A pull request should
include a focused change and a regression test when behavior changes.

Good first contributions:

- Improve a confusing setup step after testing it on a fresh computer.
- Add a minimal regression fixture for a CSV format that fails unexpectedly.
- Translate the quickstart while retaining executable command examples.

Please use synthetic records in issues and tests. Do not upload personal data,
credentials, or source datasets without redistribution permission. Real-world
validation should state the source, sampling, and metric convention.

## Review

The maintainer reviews each contribution for usefulness, correctness, and
compatibility. Small datasets and missing values are supported cases, not
errors to hide. Keep the strictly-greater-than threshold convention explicit.

## Licensing status

Code, synthetic examples, and repository documentation are available under the
[MIT License](LICENSE). See [DATA_SOURCES.md](DATA_SOURCES.md) for the separate
status of the historical data files. Public visibility alone does not grant
redistribution rights for third-party data.
