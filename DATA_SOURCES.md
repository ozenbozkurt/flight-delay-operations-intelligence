# Data sources and reuse

## Current repository files

The historical CSV files under `data/` were already present when the reusable
CLI was added. Their exact download URLs, dates, transformation steps, and
redistribution terms were not recorded in the repository, so they are **not
covered by this repository's MIT license**.

Their column names match the U.S. Bureau of Transportation Statistics (BTS)
Reporting Carrier On-Time Performance schema. That is a useful lead, not a
verified provenance claim. Do not rely on the historical sample for a new
publication or redistribute it as BTS data until its original retrieval record
is reconstructed.

## Recommended reproducible source

For a new analysis, obtain the desired monthly files directly from the official
[BTS Reporting Carrier On-Time Performance table](https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ).
The official field reference documents flight date, carrier, delay, and delay
cause fields: [BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ).

Record the URLs, download dates, selected periods, exact transforms, and a
checksum for every generated analysis input. Retain the applicable BTS terms
and attribution with the resulting dataset or report.

## License boundary

`LICENSE` applies to source code, synthetic examples, and documentation written
for this repository. It does not grant rights to third-party datasets, logos,
or external content. Contributors must only add data that they have the right
to distribute and must document its source in this file.
