"""Independently verify used manuscript values, complete tables and reviewed scope."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, hashlib, json, re, unicodedata
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    if name.endswith(".csv"):
        with (ROOT / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / name).read_bytes())


def expected(binding):
    value = load(binding["file"])
    if binding["query"] is not None:
        matched = [
            r for r in value if all(r[k] == v for k, v in binding["query"].items())
        ]
        assert len(matched) == 1
        value = matched[0]
    for key in binding["field"] or []:
        value = value[key]
    op = binding["operation"]
    if op == "length":
        return str(len(value))
    if op == "commas":
        return format(int(value), ",")
    if op in ["percent2", "percent3"]:
        exact = Fraction(value) * 100
        with localcontext() as context:
            context.prec = 80
            return format(
                Decimal(exact.numerator) / Decimal(exact.denominator),
                "." + op[-1] + "f",
            )
    assert op == "value"
    return str(value)


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    pdf = PdfReader(ROOT / "paper/manuscript.pdf")
    require(len(pdf.pages) == 6, "six current pages")
    pages = [unicodedata.normalize("NFKC", p.extract_text() or "") for p in pdf.pages]
    compact = re.sub(r"\s+", " ", "\n".join(pages))
    words = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1\2", "\n".join(pages))
    words = re.sub(r"\s+", " ", words)
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bindings = load("paper/bindings.json")
    require(
        len(bindings) == 154 and len({b["name"] for b in bindings}) == len(bindings),
        "unique actual bindings",
    )
    for binding in bindings:
        value = expected(binding)
        require(value == binding["display"], "independent source value and format")
        require(
            "\\newcommand{\\" + binding["name"] + "}{" + value + "}" in tex,
            "actual definition",
        )
        require(
            len(re.findall(r"\\" + re.escape(binding["name"]) + r"\b", tex)) >= 2,
            "actually used beyond definition",
        )
        require(value in compact, "actual PDF value")
    table = re.sub(r"\s+", " ", pages[1])
    summary = load("results/summary.json")
    for level in ["K0", "K1", "K2", "K3", "K4", "K5"]:
        fields = [
            "groups",
            "rows_beyond_one",
            "numeric_conflict",
            "numeric_disagreements",
            "mixed_duration",
            "mixed_segment_coreg",
        ]
        parts = [level] + [format(summary["by_key"][level][k], ",") for k in fields]
        require(" ".join(parts) in table, "complete actual PDF key-level row")
    companies = [("104169", "Walmart"), ("320193", "Apple"), ("789019", "Microsoft")]
    tags = [
        ("Assets", "Assets"),
        ("Liabilities", "Liabilities"),
        ("NetIncomeLoss", "Net income"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Contract revenue"),
        ("Revenues", "Revenues"),
        ("SalesRevenueNet", "Net sales"),
    ]
    cases = load("results/company_tag_keys.csv")
    for cik, company in companies:
        for tag, label in tags:
            row = next(
                r
                for r in cases
                if r["cik"] == cik and r["tag"] == tag and r["level"] == "K0"
            )
            complete = next(
                r
                for r in cases
                if r["cik"] == cik and r["tag"] == tag and r["level"] == "K4"
            )
            parts = (
                [company, label]
                + [
                    format(int(row[k]), ",")
                    for k in [
                        "source_records",
                        "groups",
                        "rows_beyond_one",
                        "numeric_disagreements",
                    ]
                ]
                + [format(int(complete["groups"]), ",")]
            )
            require(
                " ".join(parts) in table,
                "all18 actual company/tag PDF rows including zeros",
            )
    compact_words = "".join(re.findall("[a-z0-9]+", words.lower()))
    for phrase in [
        "Not peer reviewed",
        "not a count of verified restatements",
        "original broad historical restatement/model-leakage question remains unexecuted",
        "absence cannot establish that historical financial values are stable",
        "convenience cohort",
        "not a zero financial amount",
        "not a defensible financial selection policy",
        "source informed,not blinded",
        "One disclosed post-comparison checker correction",
        "all six primary output bytes remain unchanged",
        "positive control is explicitly post-analysis",
        "two abstentions and five rejections",
        "do not recover exact fiscal boundaries",
        "no verified timezone conversion",
        "Azure optimization",
        "SEC does not endorse",
    ]:
        require(
            "".join(re.findall("[a-z0-9]+", phrase.lower())) in compact_words,
            ("actual scope qualification", phrase),
        )
    freeze = load("PLAN_FREEZE.json")
    require(len(freeze["hashes"]) == 24, "24 actual protected dependencies")
    original_path = ROOT / freeze["original_comparison_freeze"]
    require(
        hashlib.sha256(original_path.read_bytes()).hexdigest()
        == freeze["original_freeze_sha256"],
        "preserved original freeze bytes",
    )
    original = json.loads(original_path.read_bytes())
    require(
        [k for k in original["hashes"] if original["hashes"][k] != freeze["hashes"][k]]
        == ["src/check_analysis.py"],
        "single disclosed checker amendment",
    )
    require(
        hashlib.sha256(
            (ROOT / "HISTORY/check_analysis_original.py").read_bytes()
        ).hexdigest()
        == original["hashes"]["src/check_analysis.py"],
        "original failed checker retained",
    )
    for name, digest in load("HISTORY/initial_result_sha256.json").items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "unchanged initial primary output bytes",
        )
    require(
        load("results/positive_control_verification.json")["finite_conditions"] == 25,
        "current additive control checks",
    )
    verification = load("results/verification.json")
    require(verification["authored_fixture_methods"] == 32, "32 authored fixtures")
    for name, digest in verification["result_sha256"].items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "current output bytes",
        )
    for suffix in ["310", "312"]:
        replay = load("results/reproduction_cpython" + suffix + ".json")
        require(
            replay["status"] == "PASS" and replay["full_history"],
            "isolated full history",
        )
        require(
            len(replay["reproduced_files"]) == 6
            and replay["unchanged_source_files"] == 8,
            "actual replay scope",
        )
        require(
            replay["additional_postanalysis_positive_control"]
            == "PASS_BYTE_EXACT_AND_INDEPENDENT_SOURCE_CHECK",
            "additional qualified control replay",
        )
        require(
            replay["reproduced_files"] == list(verification["result_sha256"]),
            "six outputs",
        )
    scope = load("paper/PUBLICATION_SCOPE.json")
    require(
        scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False,
        "independent publication scope",
    )
    require(len(scope["public_files"]) == 5, "five scoped files")
    for name, digest in scope["public_files"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "current scoped bytes",
        )
    for name in ["key_retention", "context_collisions", "numeric_disagreement"]:
        require(
            (ROOT / "figures" / (name + ".pdf")).read_bytes()
            == (ROOT / "paper/images" / (name + ".pdf")).read_bytes(),
            "current figure copy",
        )
    visual = load("paper/visual_review.json")
    require(visual["pages_reviewed"] == [1, 2, 3, 4, 5, 6], "all pages reviewed")
    require(
        visual["manuscript_sha256"]
        == hashlib.sha256((ROOT / "paper/manuscript.pdf").read_bytes()).hexdigest(),
        "reviewed PDF bytes",
    )
    for name, digest in visual["reviewed_figure_png_sha256"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "reviewed figure bytes",
        )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        used_numeric_bindings=len(bindings),
        pages=len(pdf.pages),
        scope_files=5,
        scope="Used source bindings, complete18 company/tag and6 key-level PDF rows, original freeze/unchanged primary outputs/disclosed correction, current output and figure hashes, two replay receipts, all rendered pages and approved independent publication scope. Finite evidence, not universal correctness.",
    )
    (ROOT / "paper/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
