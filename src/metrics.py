"""Relational context accounting; numeric disagreement is not a restatement verdict."""

from collections import defaultdict
from fractions import Fraction
import hashlib, json

BASE = ["cik", "tag", "ddate"]
ADDED = [
    [],
    ["qtrs"],
    ["qtrs", "uom"],
    ["qtrs", "uom", "version"],
    ["qtrs", "uom", "version", "segment_hash", "coreg_hash"],
    ["qtrs", "uom", "version", "segment_hash", "coreg_hash", "adsh"],
]
KEYS = {"K" + str(i): BASE + extra for i, extra in enumerate(ADDED)}
FULL = KEYS["K5"]


def group_id(level, key):
    return hashlib.sha256(
        json.dumps([level, list(key)], separators=(",", ":")).encode()
    ).hexdigest()


def groups(rows, fields):
    result = defaultdict(list)
    for row in rows:
        result[tuple(row[k] for k in fields)].append(row)
    return dict(sorted(result.items()))


def account(level, key, rows):
    assert rows and all(
        r["state"] == "ELIGIBLE" and int(r["source_records"]) == 1 for r in rows
    )

    def rank(row):
        return (row["accepted"], row["adsh"], tuple(row[k] for k in FULL))

    winner = max(rows, key=rank)
    known = [r for r in rows if r["value_state"] == "KNOWN"]
    distinct = {Fraction(r["value"]) for r in known}
    compared = len(known) if winner["value_state"] == "KNOWN" else 0
    disagreements = (
        sum(Fraction(r["value"]) != Fraction(winner["value"]) for r in known)
        if compared
        else 0
    )
    latest = max((r["accepted"], r["adsh"]) for r in rows)
    latest_contexts = {
        tuple(r[k] for k in FULL) for r in rows if (r["accepted"], r["adsh"]) == latest
    }
    return dict(
        level=level,
        group_id=group_id(level, key),
        cik=rows[0]["cik"],
        tag=rows[0]["tag"],
        key_json=json.dumps(list(key), separators=(",", ":")),
        source_records=len(rows),
        known_records=len(known),
        missing_records=sum(r["value_state"] == "MISSING" for r in rows),
        invalid_records=sum(r["value_state"] == "INVALID" for r in rows),
        distinct_known_values=len(distinct),
        numeric_conflict=int(len(distinct) > 1),
        rows_beyond_one=len(rows) - 1,
        mixed_duration=int(len({r["qtrs"] for r in rows}) > 1),
        mixed_units=int(len({r["uom"] for r in rows}) > 1),
        mixed_taxonomy=int(len({r["version"] for r in rows}) > 1),
        mixed_segment_coreg=int(
            len({(r["segment_hash"], r["coreg_hash"]) for r in rows}) > 1
        ),
        mixed_accession=int(len({r["adsh"] for r in rows}) > 1),
        numeric_disagreements=disagreements,
        compared_known_records=compared,
        unknown_comparison_records=len(rows) - compared,
        latest_accession_contexts=len(latest_contexts),
        conservative_abstain=int(len(latest_contexts) > 1),
        winner_fact=winner["fact_id"],
    )
