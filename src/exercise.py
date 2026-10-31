"""Require a complete current financial context; abstain from unsupported interpretations."""

from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
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


def answer(request, facts):
    if not isinstance(request, dict) or request.get("purpose") != "current_fact":
        return dict(
            status="REJECTED",
            reason="No restatement,original-time,exact fiscal-date,forecast-accuracy or investment inference",
        )
    if not all(k in request and isinstance(request[k], str) for k in REQUIRED):
        return dict(
            status="ABSTAIN",
            reason="Complete source context required;short latest-value keys may collapse different quantities",
        )
    found = [
        r
        for r in facts
        if all(r[k] == request[k] for k in REQUIRED) and r["state"] == "ELIGIBLE"
    ]
    if len(found) != 1 or int(found[0]["source_records"]) != 1:
        return dict(
            status="ABSTAIN",
            reason="A unique eligible complete current context is unavailable",
        )
    r = found[0]
    if r["value_state"] != "KNOWN":
        return dict(
            status="UNAVAILABLE",
            reason="Missing or invalid source numeric value is not zero",
        )
    return dict(
        status="ACCEPTED_QUALIFIED",
        value=r["value"],
        uom=r["uom"],
        qtrs=r["qtrs"],
        adsh=r["adsh"],
        source_truth="UNESTABLISHED",
        original_time_availability="UNESTABLISHED",
        formal_restatement="UNESTABLISHED",
        qualification="One current SEC extract fact;rounded period/duration fields and full context retained;not a production or investment service",
    )


def run(out):
    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as f:
        facts = list(csv.DictReader(f))
    requests = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    result = [dict(request=r, response=answer(r, facts)) for r in requests]
    (out / "exercise.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(
        json.dumps(
            dict(
                examples=len(result),
                accepted=sum(
                    r["response"]["status"] == "ACCEPTED_QUALIFIED" for r in result
                ),
                abstained=sum(r["response"]["status"] == "ABSTAIN" for r in result),
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    run(p.parse_args().out)
