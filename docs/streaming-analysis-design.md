# Memory-Bounded CSV Analysis Design

## Goal

Add an opt-in memory-bounded mode for large flight CSV files without
changing the existing in-memory behavior or the public `analyze()`
DataFrame API.

## Proposed CLI

Add an optional `--chunksize N` argument.

Without `--chunksize`, the CLI keeps the current behavior:

```text
pd.read_csv(...) -> analyze(DataFrame)
