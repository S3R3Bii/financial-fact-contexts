"""Write a source-bound independent financial-context manuscript."""

from pathlib import Path
import csv, json, shutil

ROOT = Path(__file__).resolve().parents[1]
bindings = []


def letters(index):
    result = ""
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            return result


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def bind(file, field=None, query=None, operation="value"):
    value = load(file)
    if query is not None:
        found = [r for r in value if all(r[k] == v for k, v in query.items())]
        assert len(found) == 1
        value = found[0]
    for key in field or []:
        value = value[key]
    if operation == "length":
        value = len(value)
    display = format(int(value), ",") if operation == "commas" else str(value)
    name = "Bound" + letters(len(bindings))
    bindings.append(
        dict(
            name=name,
            file=file,
            field=field,
            query=query,
            operation=operation,
            display=display,
        )
    )
    return "\\" + name + "{}"


def headline(field):
    return bind("results/summary.json", [field], operation="commas")


def level(key, field):
    return bind("results/summary.json", ["by_key", key, field], operation="commas")


def checked(field):
    return bind("results/verification.json", [field], operation="commas")


p1 = (
    r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=.72in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,array,graphicx,pdflscape,xcolor,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue,pdftitle={Financial facts need their full context}}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\newcommand{\heading}[1]{\vspace{4pt}{\large\bfseries #1}\par}
%%BINDINGS%%
\begin{document}
{\LARGE\bfseries Financial facts need their full context\par}
\vspace{5pt}
Independent research program\hfill 31 October 2026 UTC\\
\textit{Not peer reviewed. One current SEC extract; fixed relational-key comparisons.}

\heading{Practical finding}
A company, tag and period-end date do not uniquely identify a financial fact. In this fixed cohort, that short key collapses """
    + headline("eligible_facts")
    + r""" facts into """
    + level("K0", "groups")
    + r""" groups. A one-row-per-key join would discard """
    + level("K0", "rows_beyond_one")
    + r""" distinct source contexts.

The short key mixes durations in """
    + level("K0", "mixed_duration")
    + r""" groups and segment/coregistrant contexts in """
    + level("K0", "mixed_segment_coreg")
    + r""" groups. Adding duration still leaves """
    + level("K1", "rows_beyond_one")
    + r""" extra contexts within """
    + level("K1", "groups")
    + r""" groups. Retaining segment/coregistrant identity separates every observed fact here. Accession remains part of the full source key even though each company has only one selected filing in this archive.

An authored naive-winner simulation finds """
    + level("K0", "numeric_disagreements")
    + r""" source facts with a different numeric value from their short-key winner. Different durations or dimensions can describe different quantities. This is not a count of verified restatements, financial losses or historical feature leakage.

\heading{Recommended use}
Carry accession, tag, taxonomy version, period, duration, unit, segment and coregistrant identity through a financial-data join. Require a complete context before returning a qualified fact; abstain when it is absent or ambiguous. Classify context differences before interpreting a changed value as a revision.

The implementation exercise retains a useful failed assumption: an Apple example requested a 2026 taxonomy, while the source uses a 2025 taxonomy. The lookup correctly abstains. A separately labeled post-analysis positive control uses the actual version and returns a qualified source value. Filing year is insufficient evidence for taxonomy version.

\heading{Fixed source and scope}
The official current 2026 Q3 face-financial archive supplies """
    + headline("selected_accessions")
    + r""" selected filings from Apple, Microsoft and Walmart. The protocol fixed those CIKs, six standard financial tags and all six key specifications before retrieval. All """
    + headline("fixed_company_tag_cases")
    + r""" company/tag cells are retained, including empty cells; this is a convenience cohort.

The original broad historical restatement/model-leakage question remains unexecuted. There are """
    + headline("repeated_context_observations")
    + r""" repeated-context observations across accessions in this selected cohort. That absence cannot establish that historical financial values are stable.
\newpage
"""
)
p2 = r"""{\Large\bfseries Complete fixed key accounts\par}
{\small\setlength{\tabcolsep}{5pt}
\begin{tabular}{@{}lrrrrrr@{}}\toprule
Key & Groups & Extra contexts & Conflicts & Value differences & Mixed duration & Mixed segment\\\midrule
"""
for key in ["K0", "K1", "K2", "K3", "K4", "K5"]:
    p2 += (
        " & ".join(
            [key]
            + [
                level(key, field)
                for field in [
                    "groups",
                    "rows_beyond_one",
                    "numeric_conflict",
                    "numeric_disagreements",
                    "mixed_duration",
                    "mixed_segment_coreg",
                ]
            ]
        )
        + r" \\"
        + "\n"
    )
p2 += r"""\bottomrule\end{tabular}}

K0 uses CIK, tag and rounded end date. K1 adds duration, K2 unit, K3 taxonomy, K4 segment/coregistrant identity and K5 accession. All units and taxonomy versions remain explicit even where they do not split a group in this cohort. Conflicting-group counts need not decline at every step: a larger group can split into several groups that each contain differing values.

\heading{All company/tag cells, including zero coverage}
{\small\setlength{\tabcolsep}{5pt}
\begin{tabular}{@{}llrrrrr@{}}\toprule
Company & Tag label & Facts & K0 groups & K0 extra & K0 value differences & K4 groups\\\midrule
"""
companies = [("104169", "Walmart"), ("320193", "Apple"), ("789019", "Microsoft")]
tags = [
    ("Assets", "Assets"),
    ("Liabilities", "Liabilities"),
    ("NetIncomeLoss", "Net income"),
    ("RevenueFromContractWithCustomerExcludingAssessedTax", "Contract revenue"),
    ("Revenues", "Revenues"),
    ("SalesRevenueNet", "Net sales"),
]
for cik, company in companies:
    for tag, label in tags:
        q = dict(cik=cik, tag=tag, level="K0")
        parts = [company, label]
        for field in [
            "source_records",
            "groups",
            "rows_beyond_one",
            "numeric_disagreements",
        ]:
            parts.append(bind("results/company_tag_keys.csv", [field], q, "commas"))
        parts.append(
            bind(
                "results/company_tag_keys.csv",
                ["groups"],
                dict(cik=cik, tag=tag, level="K4"),
                "commas",
            )
        )
        p2 += " & ".join(parts) + r" \\" + "\n"
p2 += (
    r"""\bottomrule\end{tabular}}

Tag labels are abbreviated for readability; the CSV retains the exact XBRL identifiers. Counts of zero indicate no selected facts for that company/tag, not a zero financial amount. The repository retains all """
    + headline("company_tag_key_cases")
    + r""" company/tag/key cells, """
    + headline("group_accounts")
    + r""" full group accounts and """
    + headline("memberships")
    + r""" memberships.

The naive winner is the lexicographic maximum of accepted timestamp, accession and complete context. This deterministic rule is authored for the audit, not a defensible financial selection policy. No dollar differences are pooled across incompatible quantities, and no source observation is silently averaged or removed.
\newpage
"""
)
p3 = (
    r"""{\Large\bfseries Verification, implementation and limits\par}
\heading{Independent evidence}
The native archive controls cover """
    + bind("data/source_accounts.json", ["native_rows", "sub.txt"], operation="commas")
    + r""" SUB rows, """
    + bind("data/source_accounts.json", ["native_rows", "tag.txt"], operation="commas")
    + r""" TAG rows, """
    + bind("data/source_accounts.json", ["native_rows", "pre.txt"], operation="commas")
    + r""" PRE rows and """
    + bind("data/source_accounts.json", ["native_rows", "num.txt"], operation="commas")
    + r""" NUM rows. Independent pandas C chunks, SQLite key multiplicities, Fraction values and date parsing reconcile every selected fact in """
    + checked("native_source_conditions")
    + r""" finite conditions. Saved-source checks pass """
    + checked("saved_source_conditions")
    + r"""; complete independent relational/numeric checks pass """
    + checked("independent_analysis_conditions")
    + r""".

The original committed freeze bound """
    + checked("original_frozen_dependencies")
    + r""" actual dependencies before comparisons. One disclosed post-comparison checker correction replaces an incorrect expectation that every complete request must succeed. The original seven requests, production logic, source and all six primary output bytes remain unchanged. HISTORY preserves the original freeze, checker and output hashes; the additional positive control is explicitly post-analysis.

All """
    + checked("authored_fixture_methods")
    + r""" authored fixture methods pass. Separate full-history CPython """
    + bind("results/reproduction_cpython310.json", ["python"])
    + r""" and """
    + bind("results/reproduction_cpython312.json", ["python"])
    + r""" replays reproduce six primary files exactly, preserving all eight source-directory files. Both also reproduce and independently check the additional positive control. Current figure checks bind """
    + bind("figures/verification.json", ["source_bound_artists"])
    + r""" bars and """
    + bind("figures/verification.json", ["svg_coordinate_conditions"])
    + r""" actual SVG coordinate conditions. Finite checks are not universal correctness guarantees.

\heading{Runnable implementation exercise}
The original seven requests return two abstentions and five rejections. One additional positive control returns a qualified current fact and passes """
    + checked("positive_control_conditions")
    + r""" independent source/history checks. The interface retains units, duration, accession and explicit unknown source truth, original-time availability and formal-restatement status. It does not certify arbitrary caller input or a production service.
\begin{verbatim}
python -m pip install -r requirements.txt
python src/replay.py --out ../financial-context-replay
python src/positive_control.py --out ../positive-control
python src/check_positive_control.py
\end{verbatim}
Use new output directories. Saved-data replay does not redownload mutable native sources.

\heading{Material limits}
One quarter, three familiar filers and six tags do not represent all financial reporting. Source values were visible during reconciliation; this was source informed, not blinded. SEC reprocessed the current files with segment facts. Rounded month-end and quarter-duration fields do not recover exact fiscal boundaries. Accepted timestamps receive no verified timezone conversion or original-publication interpretation.

There is no verified formal restatement, predictive accuracy, investment advice, source-truth certification, new estimator, deployment or realized saving. Native archives, corporate report prose, footnotes, labels, business contact fields and EINs remain private. Separate formal-publication projects, including Azure optimization, remain private.

{\small Source: SEC Financial Statement Data Sets, current 2026 Q3 archive, captured 31 October 2026 UTC.
\url{https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets}.
Exact source/member hashes, all native table counts and earlier access/parser failures are retained. SEC warns that extracts may contain errors and do not replace full filings. SEC does not endorse this independent analysis. MIT covers original code; minimal government/registrant facts are attributed separately.}
"""
)
figs = []
for title, name in [
    ("Complete source-context retention", "key_retention"),
    ("All omitted-context accounts", "context_collisions"),
    ("Numeric disagreement and interpretation", "numeric_disagreement"),
]:
    figs.append(
        r"\begin{landscape}"
        + "\n"
        + r"{\large\bfseries "
        + title
        + r"\par}"
        + "\n"
        + r"\begin{center}\includegraphics[width=9.4in,height=6.25in,keepaspectratio]{images/"
        + name
        + r".pdf}\end{center}"
        + "\n"
        + r"\end{landscape}"
        + "\n"
    )
tex = p1 + p2 + p3 + "".join(figs) + r"\end{document}" + "\n"
tex = tex.replace(
    "%%BINDINGS%%",
    "\n".join(
        "\\newcommand{\\" + r["name"] + "}{" + r["display"] + "}" for r in bindings
    ),
)
paper = ROOT / "paper"
(paper / "images").mkdir(parents=True, exist_ok=True)
for name in ["key_retention", "context_collisions", "numeric_disagreement"]:
    shutil.copy2(ROOT / "figures" / (name + ".pdf"), paper / "images" / (name + ".pdf"))
(paper / "main.tex").write_bytes(tex.rstrip().encode() + b"\n")
(paper / "bindings.json").write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
print("SOURCE_BOUND_MANUSCRIPT_WRITTEN", len(bindings))
