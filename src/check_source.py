"""Check every minimal fact and provenance hash without reacquiring native files."""

from pathlib import Path
from collections import Counter
from fractions import Fraction
import csv, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    receipt = json.loads((ROOT / "data/native_verification.json").read_bytes())
    require(receipt["status"] == "PASS", "independent native source receipt")
    for name, digest in receipt["hashes"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "native-bound source bytes",
        )
    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    source = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    states = Counter()
    values = Counter()
    seen = set()
    for r in rows:
        require(r["cik"] in ["320193", "789019", "104169"], "fixed CIK cohort")
        require(
            r["tag"]
            in [
                "Assets",
                "Liabilities",
                "NetIncomeLoss",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
            ]
            and r["version"].startswith("us-gaap/"),
            "fixed standard tag cohort",
        )
        require(int(r["source_records"]) > 0, "positive source multiplicity")
        for field, blank in [
            ("segment_hash", "segment_nonblank"),
            ("coreg_hash", "coreg_nonblank"),
        ]:
            require(
                (r[blank] == "0" and r[field] == "")
                or (r[blank] == "1" and bool(re.fullmatch("[0-9a-f]{64}", r[field]))),
                "retained context identity",
            )
        require(
            r["value_state"] in ["KNOWN", "MISSING", "INVALID"],
            "explicit numeric state",
        )
        if r["value_state"] == "KNOWN":
            require(Fraction(r["value"]).denominator > 0, "known exact numeric value")
        else:
            require(r["value"] == "", "unavailable not zero")
        if r["state"] == "ELIGIBLE":
            key = tuple(
                r[k]
                for k in [
                    "adsh",
                    "tag",
                    "version",
                    "ddate",
                    "qtrs",
                    "uom",
                    "segment_hash",
                    "coreg_hash",
                ]
            )
            require(
                key not in seen and int(r["source_records"]) == 1,
                "unique complete eligible context",
            )
            seen.add(key)
            require(int(r["pre_rows"]) > 0, "source presentation presence")
        states[r["state"]] += int(r["source_records"])
        values[r["value_state"]] += int(r["source_records"])
    require(
        states == source["source_state_accounts"]
        and values == source["numeric_value_accounts"],
        "complete source accounts",
    )
    require(
        sum(states.values())
        == receipt["selected_fact_rows"]
        == source["selected_fact_rows"],
        "all selected source facts",
    )
    require(
        states["ELIGIBLE"]
        == receipt["eligible_fact_rows"]
        == source["eligible_fact_rows"],
        "eligible denominator",
    )
    require(len(rows) == source["projected_fact_cells"], "all projected cells")
    result = dict(
        status="PASS",
        finite_conditions=n,
        selected_fact_rows=sum(states.values()),
        eligible_fact_rows=states["ELIGIBLE"],
        scope="Every minimal native-bound fact,complete context and numeric-state account;not source truth or historical publication.",
    )
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    main()
