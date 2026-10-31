# Financial-statement restatements as a data engineering test

**State: protocol only. No result or novelty claim yet.**

## Decision

How often does a naive latest-value join rewrite the historical features used in a model?

## Target data

- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) — targeted; exact export and rights must be verified.

## Study design

Point-in-time XBRL panel construction and revision audit.

Accession-date joins; unit and taxonomy checks; duplicate-fact tests; manual filing reconciliation.

## Contribution to test

Quantify leakage introduced by revision handling before fitting any financial model. This is a proposed contribution, not a verified gap in the literature. Prior work must be reviewed before any novelty claim.

## Evidence to retain

- Exact source snapshot, request, retrieval time, observation window, definitions, units and redistribution terms.
- Prespecified splits, baseline, search space, tuning budget, seed and decision metric.
- All candidate results, including failures; final holdout used only after model selection.
- Independent headline recomputation, leakage checks and reviewed figures with units and uncertainty.
- Reproduction command and environment; private LaTeX manuscript written from measured results.

## Skills

SQL, data engineering, data lineage, testing. The repository must demonstrate these through executed work before they become portfolio claims.
