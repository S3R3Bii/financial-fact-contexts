# Fixed financial-fact context audit

31 October 2026 UTC. Independent Study 22. No financial fact values have been obtained or inspected at this commitment. Earlier ordinary SEC API/archive requests returned 403 and remain preserved. The original broad historical restatement/model-leakage proposal remains unexecuted.

## Decision and fixed source

How many distinct source fact contexts does a short latest-value key collapse, and which omitted context fields explain the collisions? Use exactly the current official 2026 Q3 Financial Statement Data Sets archive linked at https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets , URL https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q3.zip . Documentation: https://www.sec.gov/files/financial-statement-data-sets.pdf . The current files were reprocessed using primary-financial-statement rendering, with segments added to NUM. They are not an immutable original-vintage capture.

Attempt the ordinary visible public browser download link once. Stop at access denial or security challenge. Do not rotate agents, use proxies, bypass controls or retrieve private exports. Keep the exact archive privately with URL, timing, size, SHA-256 and every member hash/CRC/header. Count all native SUB, NUM, TAG, PRE rows without publishing raw files.

## Cohort fixed before values

Company CIKs are 320193(Apple), 789019(Microsoft), 104169(Walmart). These familiar filers are an authored convenience cohort, not a representative company sample. Use all their SUB entries in this archive with form 10-K,10-Q,10-K/A or10-Q/A. Retain zero-company/form coverage; do not replace a company after outcomes.

From selected accessions retain all NUM rows for exactly six case-sensitive standard tags: Assets, Liabilities, NetIncomeLoss, RevenueFromContractWithCustomerExcludingAssessedTax, Revenues, SalesRevenueNet. Standard taxonomy versions begin us-gaap/. Retain every observed unit, duration, period, segment, coregistrant and missing numeric value. Keep all 18 company/tag cells, including empty cells.

SUB is keyed by adsh; NUM's documented complete key is adsh, tag, version, ddate, qtrs, uom, segments, coreg. Retain whole duplicate-key groups explicitly; do not choose one silently. Missing/malformed identity or source dates remain unavailable. Blank segments/coreg are valid documented contexts; nonnull content is represented by SHA-256 and blank status in public projections. No footnote, company report text, TAG documentation or PRE labels are public.

Reconcile selected NUM rows to unique SUB and TAG identities and PRE presence; PRE may legitimately have multiple presentation rows per NUM tag. A repeated presentation is not a duplicate financial fact. Parse source numeric tokens with Decimal/Fraction, not binary float; missing and invalid numeric states are separate from zero. Date fields use their actual documented formats. Accepted timestamps have no verified timezone conversion here. SUB period/fye and NUM ddate are rounded to month-end; NUM qtrs is a rounded duration count, with 0 for an instant. Do not infer exact fiscal start dates or real-time publication from these fields.

## All six nested key specifications

K0=(CIK, tag, ddate).
K1=K0+qtrs.
K2=K1+uom.
K3=K2+version.
K4=K3+segment_hash+coreg_hash.
K5=K4+adsh, the complete source identity with redundant CIK.

For every key, company and tag, export all groups and complete memberships. Report source rows, groups, rows beyond one per group, groups with multiple distinct known numeric values, and counts mixing duration, unit, taxonomy, segment/coreg or accession. Missing/invalid values remain separate. Addition of key fields must not increase rows beyond one; do not assume conflicting-group count is monotone. All 108 company/tag/key cells are retained; no key or company is selected away.

A declared naive overwrite simulation chooses the lexicographic maximum tuple(accepted, adsh, complete_context_key) per group. This deterministic tie-break is authored for audit, not a defensible financial selection rule. Count known numeric disagreements with its winner and expose whether they cross units/durations/segments/versions. Never sum dollar differences across incompatible units or describe such disagreement as a verified restatement. Also count latest-accession groups with multiple complete contexts where a conservative caller must abstain.

Across K4 groups that contain multiple accessions, export all repeated-context values and filing dates, including agreement and missingness. A value difference is a repeated-context disagreement in a current extract, not proof of a formal restatement, original historical availability or predictive leakage. Do not fit a financial model or claim investment value.

## Source and method checks

Use csv/Decimal production projection and an independent pandas C/Fraction/SQLite parser over the native archive. Independently reconcile every selected fact, all full-key duplicate groups, all metadata/link accounts, all minimal projections and all native row/hash/CRC controls. Preserve unknowns and complete source exclusions.

Commit the actual source/method/test dependency freeze before key comparisons. Independently reconstruct every group, membership, nested-key account, naive winner, abstention and repeated-context output using SQLite and exact rational values without production helpers. Meaningful fixtures cover duration/unit/segment/version/accession collisions, blank contexts, missing versus zero, signed values, timestamp ties, duplicate groups, rounded dates, instant versus duration and unsupported historical/restatement/investment requests. Preserve all results and failures.

A runnable implementation exercise should return a qualified unique current fact context or abstain when fields are insufficient. Reject requests for formal-restatement conclusions, original-time features, exact fiscal dates, forecast accuracy or investment advice. It certifies neither arbitrary caller data nor a production service.

## Acceptance, presentation and limits

Release requires lawful reconciled native source, actual committed precomparison dependencies, complete source accounts and all six key cases, independent exact reconstruction, meaningful fixtures, two isolated saved-data replays, clear practical recommendation, readable source-bound figures and manuscript, privacy scope and verified exact candidate/main CI/tree/tag/metadata.

This is a finite current-source convenience audit using established relational keys and arithmetic; no new estimator or exhaustive scientific-priority claim. Source accuracy and original-vintage availability remain unestablished. Do not call the original broad restatement/leakage study executed. Native files and third-party prose stay private. Original code is MIT licensed; minimal facts are attributed. No SEC endorsement. Formal-publication projects including Azure remain private.
