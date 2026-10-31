"""Retain every nested-key group,membership and fixed company/tag case."""

from pathlib import Path
import argparse, csv, json
from metrics import KEYS, FULL, groups, account

ROOT = Path(__file__).resolve().parents[1]
CIKS = ["104169", "320193", "789019"]
TAGS = [
    "Assets",
    "Liabilities",
    "NetIncomeLoss",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
GROUP_FIELDS = [
    "level",
    "group_id",
    "cik",
    "tag",
    "key_json",
    "source_records",
    "known_records",
    "missing_records",
    "invalid_records",
    "distinct_known_values",
    "numeric_conflict",
    "rows_beyond_one",
    "mixed_duration",
    "mixed_units",
    "mixed_taxonomy",
    "mixed_segment_coreg",
    "mixed_accession",
    "numeric_disagreements",
    "compared_known_records",
    "unknown_comparison_records",
    "latest_accession_contexts",
    "conservative_abstain",
    "winner_fact",
]
SUM_FIELDS = [
    "source_records",
    "known_records",
    "missing_records",
    "invalid_records",
    "numeric_conflict",
    "rows_beyond_one",
    "mixed_duration",
    "mixed_units",
    "mixed_taxonomy",
    "mixed_segment_coreg",
    "mixed_accession",
    "numeric_disagreements",
    "compared_known_records",
    "unknown_comparison_records",
    "conservative_abstain",
]


def write(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run(out):
    assert not out.exists()
    out.mkdir(parents=True)
    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as f:
        allrows = list(csv.DictReader(f))
    rows = [
        dict(r, fact_id="F" + str(i + 1).zfill(4))
        for i, r in enumerate(allrows)
        if r["state"] == "ELIGIBLE"
    ]
    group_rows = []
    members = []
    cases = []
    repeated = []
    by_key = {}
    for level, fields in KEYS.items():
        for key, observations in groups(rows, fields).items():
            a = account(level, key, observations)
            group_rows.append(a)
            for r in sorted(observations, key=lambda r: r["fact_id"]):
                members.append(
                    dict(
                        level=level,
                        group_id=a["group_id"],
                        fact_id=r["fact_id"],
                        is_naive_winner=int(r["fact_id"] == a["winner_fact"]),
                    )
                )
            if level == "K4" and a["mixed_accession"]:
                for r in sorted(
                    observations, key=lambda r: (r["accepted"], r["adsh"], r["fact_id"])
                ):
                    repeated.append(
                        dict(
                            group_id=a["group_id"],
                            fact_id=r["fact_id"],
                            cik=r["cik"],
                            tag=r["tag"],
                            adsh=r["adsh"],
                            filed=r["filed"],
                            accepted=r["accepted"],
                            value_state=r["value_state"],
                            value=r["value"],
                        )
                    )
        relevant = [r for r in group_rows if r["level"] == level]
        by_key[level] = dict(
            groups=len(relevant),
            **{k: sum(int(r[k]) for r in relevant) for k in SUM_FIELDS}
        )
        for cik in CIKS:
            for tag in TAGS:
                rr = [r for r in relevant if r["cik"] == cik and r["tag"] == tag]
                cases.append(
                    dict(
                        cik=cik,
                        tag=tag,
                        level=level,
                        groups=len(rr),
                        **{k: sum(int(r[k]) for r in rr) for k in SUM_FIELDS}
                    )
                )
    write(out / "group_accounts.csv", group_rows, GROUP_FIELDS)
    write(
        out / "memberships.csv",
        members,
        ["level", "group_id", "fact_id", "is_naive_winner"],
    )
    write(
        out / "company_tag_keys.csv",
        cases,
        ["cik", "tag", "level", "groups"] + SUM_FIELDS,
    )
    write(
        out / "repeated_contexts.csv",
        repeated,
        [
            "group_id",
            "fact_id",
            "cik",
            "tag",
            "adsh",
            "filed",
            "accepted",
            "value_state",
            "value",
        ],
    )
    source = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    summary = dict(
        selected_accessions=source["selected_accessions"],
        source_fact_rows=source["selected_fact_rows"],
        eligible_facts=len(rows),
        fixed_company_tag_cases=18,
        company_tag_key_cases=len(cases),
        key_levels=len(KEYS),
        group_accounts=len(group_rows),
        memberships=len(members),
        repeated_context_observations=len(repeated),
        by_key=by_key,
        original_historical_restatement_leakage_study="UNEXECUTED",
        qualification="Current-source context collision and authored naive-overwrite audit;numeric disagreement is not a verified restatement,source error or historical feature leakage.No model or investment performance.",
    )
    (out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    run(p.parse_args().out)
