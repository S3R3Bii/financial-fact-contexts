"""Reconstruct every group,member,case and naive winner with SQLite and Fraction."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    if name.endswith(".json"):
        return json.loads((ROOT / name).read_bytes())
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    conditions = 0

    def require(ok, label):
        nonlocal conditions
        assert ok, label
        conditions += 1

    allrows = read("data/facts.csv")
    facts = [
        dict(r, fact_id="F" + str(i + 1).zfill(4))
        for i, r in enumerate(allrows)
        if r["state"] == "ELIGIBLE"
    ]
    fields = [
        "fact_id",
        "cik",
        "adsh",
        "tag",
        "version",
        "ddate",
        "qtrs",
        "uom",
        "segment_hash",
        "coreg_hash",
        "accepted",
        "filed",
        "value",
        "value_state",
    ]
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE facts (" + ",".join(name + " TEXT" for name in fields) + ")"
    )
    db.executemany(
        "INSERT INTO facts VALUES (" + ",".join("?" for _ in fields) + ")",
        (tuple(r[k] for k in fields) for r in facts),
    )
    db.create_function(
        "exact_numeric", 1, lambda token: str(Fraction(token)) if token else None
    )
    specs = [
        ["cik", "tag", "ddate"],
        ["cik", "tag", "ddate", "qtrs"],
        ["cik", "tag", "ddate", "qtrs", "uom"],
        ["cik", "tag", "ddate", "qtrs", "uom", "version"],
        ["cik", "tag", "ddate", "qtrs", "uom", "version", "segment_hash", "coreg_hash"],
        [
            "cik",
            "tag",
            "ddate",
            "qtrs",
            "uom",
            "version",
            "segment_hash",
            "coreg_hash",
            "adsh",
        ],
    ]
    full = specs[-1]
    groups = read("results/group_accounts.csv")
    members = read("results/memberships.csv")
    cases = read("results/company_tag_keys.csv")
    sourcefacts = {r["fact_id"]: r for r in facts}
    expected_groups = {}
    expected_members = set()
    expected_repeated = []
    bykey = {}
    sumfields = [
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
    for index, spec in enumerate(specs):
        level = "K" + str(index)
        group_columns = ",".join(spec)
        result = db.execute(
            "SELECT "
            + group_columns
            + ",COUNT(*),SUM(value_state='KNOWN'),SUM(value_state='MISSING'),SUM(value_state='INVALID'),COUNT(DISTINCT CASE WHEN value_state='KNOWN' THEN exact_numeric(value) END),COUNT(DISTINCT qtrs),COUNT(DISTINCT uom),COUNT(DISTINCT version),COUNT(DISTINCT segment_hash||char(31)||coreg_hash),COUNT(DISTINCT adsh) FROM facts GROUP BY "
            + group_columns
            + " ORDER BY "
            + group_columns
        ).fetchall()
        for values in result:
            key = tuple(values[: len(spec)])
            nr, known, missing, invalid, distinct, nq, nu, nv, ns, na = values[
                len(spec) :
            ]
            selected = db.execute(
                "SELECT "
                + ",".join(fields)
                + " FROM facts WHERE "
                + " AND ".join(k + "=?" for k in spec)
                + " ORDER BY fact_id",
                key,
            ).fetchall()
            observations = [dict(zip(fields, row)) for row in selected]
            ordered = sorted(
                observations,
                key=lambda r: (r["accepted"], r["adsh"], tuple(r[k] for k in full)),
            )
            winner = ordered[-1]
            compared = known if winner["value_state"] == "KNOWN" else 0
            different = (
                sum(
                    Fraction(r["value"]) != Fraction(winner["value"])
                    for r in observations
                    if r["value_state"] == "KNOWN"
                )
                if compared
                else 0
            )
            latest = max((r["accepted"], r["adsh"]) for r in observations)
            contexts = {
                tuple(r[k] for k in full)
                for r in observations
                if (r["accepted"], r["adsh"]) == latest
            }
            gid = hashlib.sha256(
                json.dumps([level, list(key)], separators=(",", ":")).encode()
            ).hexdigest()
            row = dict(
                level=level,
                group_id=gid,
                cik=observations[0]["cik"],
                tag=observations[0]["tag"],
                key_json=json.dumps(list(key), separators=(",", ":")),
                source_records=nr,
                known_records=known,
                missing_records=missing,
                invalid_records=invalid,
                distinct_known_values=distinct,
                numeric_conflict=int(distinct > 1),
                rows_beyond_one=nr - 1,
                mixed_duration=int(nq > 1),
                mixed_units=int(nu > 1),
                mixed_taxonomy=int(nv > 1),
                mixed_segment_coreg=int(ns > 1),
                mixed_accession=int(na > 1),
                numeric_disagreements=different,
                compared_known_records=compared,
                unknown_comparison_records=nr - compared,
                latest_accession_contexts=len(contexts),
                conservative_abstain=int(len(contexts) > 1),
                winner_fact=winner["fact_id"],
            )
            require(gid not in expected_groups, "unique complete group identity")
            expected_groups[gid] = row
            for r in observations:
                expected_members.add(
                    (
                        level,
                        gid,
                        r["fact_id"],
                        str(int(r["fact_id"] == winner["fact_id"])),
                    )
                )
            if level == "K4" and na > 1:
                for r in sorted(
                    observations, key=lambda r: (r["accepted"], r["adsh"], r["fact_id"])
                ):
                    expected_repeated.append(
                        dict(
                            group_id=gid,
                            fact_id=r["fact_id"],
                            cik=r["cik"],
                            tag=r["tag"],
                            adsh=r["adsh"],
                            filed=r["filed"],
                            accepted=r["accepted"],
                            value_state=r["value_state"],
                            value=sourcefacts[r["fact_id"]]["value"],
                        )
                    )
        rr = [r for r in expected_groups.values() if r["level"] == level]
        bykey[level] = dict(
            groups=len(rr), **{k: sum(r[k] for r in rr) for k in sumfields}
        )
        require(
            bykey[level]["source_records"] == len(facts), "all facts at every key level"
        )
        if index:
            require(
                bykey[level]["rows_beyond_one"]
                <= bykey["K" + str(index - 1)]["rows_beyond_one"],
                "nested-key retained-row monotonicity",
            )
    require(len(groups) == len(expected_groups), "complete group count")
    seen = set()
    for row in groups:
        require(row["group_id"] not in seen, "unique exported group")
        seen.add(row["group_id"])
        expected = expected_groups[row["group_id"]]
        require(
            row == {k: str(v) for k, v in expected.items()},
            "complete SQL/Fraction group account and naive winner",
        )
    actual_members = [
        tuple(r[k] for k in ["level", "group_id", "fact_id", "is_naive_winner"])
        for r in members
    ]
    require(
        len(actual_members) == len(set(actual_members))
        and set(actual_members) == expected_members,
        "all exact memberships and winner markers",
    )
    require(
        len(members) == len(facts) * 6, "complete six-level membership conservation"
    )
    expected_casekeys = [
        (c, t, "K" + str(i))
        for i in range(6)
        for c in ["104169", "320193", "789019"]
        for t in [
            "Assets",
            "Liabilities",
            "NetIncomeLoss",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ]
    ]
    require(
        [(r["cik"], r["tag"], r["level"]) for r in cases] == expected_casekeys,
        "all108 fixed company/tag/key cells",
    )
    for row in cases:
        rr = [
            r
            for r in expected_groups.values()
            if all(r[k] == row[k] for k in ["cik", "tag", "level"])
        ]
        expected = dict(
            cik=row["cik"],
            tag=row["tag"],
            level=row["level"],
            groups=str(len(rr)),
            **{k: str(sum(r[k] for r in rr)) for k in sumfields}
        )
        require(row == expected, "complete company/tag/key source accounts")
    require(
        read("results/repeated_contexts.csv") == expected_repeated,
        "all repeated-context observations including empty result",
    )
    summary = read("results/summary.json")
    source = read("data/source_accounts.json")
    expected = dict(
        selected_accessions=source["selected_accessions"],
        source_fact_rows=source["selected_fact_rows"],
        eligible_facts=len(facts),
        fixed_company_tag_cases=18,
        company_tag_key_cases=108,
        key_levels=6,
        group_accounts=len(expected_groups),
        memberships=len(expected_members),
        repeated_context_observations=len(expected_repeated),
        by_key=bykey,
        original_historical_restatement_leakage_study="UNEXECUTED",
    )
    for key, value in expected.items():
        require(summary[key] == value, ("complete summary", key))
    requests = read("data/exercise_inputs.json")
    examples = read("results/exercise.json")
    require(
        [r["request"] for r in examples] == requests and len(examples) == 7,
        "all fixed requests",
    )
    required = [
        "cik",
        "adsh",
        "tag",
        "version",
        "ddate",
        "qtrs",
        "uom",
        "segment_hash",
        "coreg_hash",
    ]
    for example in examples:
        request = example["request"]
        response = example["response"]
        if request["purpose"] != "current_fact":
            require(response["status"] == "REJECTED", "unsupported inference rejected")
        elif any(k not in request for k in required):
            require(response["status"] == "ABSTAIN", "incomplete context abstains")
        else:
            found = [
                r
                for r in allrows
                if r["state"] == "ELIGIBLE"
                and all(r[k] == request[k] for k in required)
            ]
            require(
                len(found) == 1 and response["status"] == "ACCEPTED_QUALIFIED",
                "unique current context",
            )
            require(
                response["value"] == found[0]["value"]
                and response["uom"] == found[0]["uom"]
                and response["qtrs"] == found[0]["qtrs"],
                "actual qualified numeric/context response",
            )
            require(
                response["source_truth"]
                == response["original_time_availability"]
                == response["formal_restatement"]
                == "UNESTABLISHED",
                "source/time/restatement unknowns",
            )
    receipt = dict(
        status="PASS",
        finite_conditions=conditions,
        complete_groups=len(groups),
        complete_memberships=len(members),
        company_tag_key_cases=108,
        repeated_context_observations=len(expected_repeated),
        examples=7,
        method="Independent SQLite grouping/distinct counts and memberships,Fraction values,direct deterministic winner and context reconstruction;no production imports",
        scope="Complete current-source relational-key and authored overwrite accounting;not a verified restatement or historical model-leakage assessment.",
    )
    (ROOT / "results/independent_check.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
