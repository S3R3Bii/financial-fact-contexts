# Minimal current financial-fact contexts

Source: SEC Financial Statement Data Sets, current2026Q3 reprocessed archive. The protocol fixed the quarter,three CIKs,six standard tags and all six nested keys before archive retrieval. Native row totals are6,516 SUB,87,871 TAG,731,170 PRE and3,905,397 NUM. All three selected company filings contain1,554 NUM rows;247 match the fixed six-tag cohort. Every selected fact is retained.

facts.csv carries only minimal factual filing/context tokens,numeric values and source/link accounts. All247 source values are known and all complete keys are unique in this finite cohort. Segment/coregistrant strings are represented by SHA-256 plus blank/nonblank status. Native footnotes,TAG documentation,PRE labels,business addresses,phone numbers,EINs and raw archives remain private. These projections are not a general anonymity guarantee.

The documented complete NUM identity contains accession,tag,taxonomy version,period end,duration,unit,segments and coregistrant. SUB identity is accession;PRE can contain multiple presentation rows for one fact tag. Repeated presentation is not a duplicate numeric fact. Source metadata and their meaning remain attached.

SUB period/fye and NUM ddate are rounded to nearest month-end. NUM qtrs is a rounded duration count,with0for an instant. SUB fiscal year/period describe the filing focus;they are not automatically every fact's own reporting period. Accepted timestamps are serialized to six fractional digits without timezone conversion;the native suffix.0 is preserved in the private archive and source hash.

This is one current extract,not an immutable original-time capture. Numeric disagreement across different contexts is not a verified restatement or source error. Missing and invalid values are not zero. The original broad historical leakage assessment remains unexecuted. See PROTOCOL.md,DATA_RIGHTS.md,SOURCE_HISTORY.md,capture_receipt.json and native_verification.json.
