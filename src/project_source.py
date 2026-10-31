"""Project a fixed complete financial-fact cohort, retaining context and missingness."""

from pathlib import Path
from zipfile import ZipFile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import Counter
import argparse, csv, hashlib, io, json, re

ROOT = Path(__file__).resolve().parents[1]
CIKS = {"320193": "Apple", "789019": "Microsoft", "104169": "Walmart"}
TAGS = [
    "Assets",
    "Liabilities",
    "NetIncomeLoss",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
FIELDS = [
    "cik",
    "adsh",
    "form",
    "filed",
    "accepted",
    "subperiod",
    "fy",
    "fp",
    "fye",
    "prevrpt",
    "tag",
    "version",
    "ddate",
    "qtrs",
    "uom",
    "segment_hash",
    "segment_nonblank",
    "coreg_hash",
    "coreg_nonblank",
    "value",
    "value_state",
    "state",
    "pre_rows",
    "source_records",
]
FULL = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segment_hash", "coreg_hash"]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest() if value else ""


def date(value):
    try:
        parsed = datetime.strptime(value, "%Y%m%d")
        return value if len(value) == 8 and parsed.strftime("%Y%m%d") == value else None
    except ValueError:
        return None


def accepted(value):
    try:
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?", value
        ):
            return None
        parsed = datetime.strptime(
            value, "%Y-%m-%d %H:%M:%S.%f" if "." in value else "%Y-%m-%d %H:%M:%S"
        )
        return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


def integer(value):
    try:
        n = Decimal(value)
        return int(n) if n.is_finite() and n == n.to_integral_value() else None
    except InvalidOperation:
        return None


def numeric(value):
    if value == "":
        return "MISSING", ""
    try:
        n = Decimal(value)
        return ("KNOWN", format(n, "f")) if n.is_finite() else ("INVALID", "")
    except InvalidOperation:
        return "INVALID", ""


def rows(zipfile, name):
    with zipfile.open(name) as stream:
        reader = csv.DictReader(
            io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""),
            delimiter="\t",
            strict=True,
        )
        for row in reader:
            assert None not in row and all(v is not None for v in row.values()), (
                "native shape",
                name,
            )
            yield row


def full_identity(row):
    q = integer(row["qtrs"])
    return tuple(
        str(q) if k == "qtrs" and q is not None else row[k]
        for k in ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg"]
    )


def project(num, sub, sub_duplicates, tag_keys, pre_counts, duplicate_keys):
    adsh = num["adsh"]
    sm = sub[adsh]
    rawyear = sm["cik"].lstrip("0") or "0"
    state = "ELIGIBLE"
    q = integer(num["qtrs"])
    dt = date(num["ddate"])
    acc = accepted(sm["accepted"])
    if not (
        re.fullmatch(r"\d{10}-\d{2}-\d{6}", adsh)
        and num["tag"]
        and num["version"]
        and dt
        and q is not None
        and q >= 0
        and num["uom"]
    ):
        state = "INVALID_FULL_IDENTITY"
    elif adsh in sub_duplicates or not (
        date(sm["filed"]) and date(sm["period"]) and acc
    ):
        state = "SUB_IDENTITY_OR_DATE_UNAVAILABLE"
    elif (num["tag"], num["version"]) not in tag_keys:
        state = "MISSING_TAG_IDENTITY"
    elif pre_counts[(adsh, num["tag"], num["version"])] == 0:
        state = "MISSING_PRE_PRESENCE"
    full = full_identity(num)
    if state == "ELIGIBLE" and full in duplicate_keys:
        state = "DUPLICATE_FULL_IDENTITY"
    value_state, value = numeric(num["value"])
    output = dict(
        cik=rawyear,
        adsh=adsh,
        form=sm["form"],
        filed=sm["filed"],
        accepted=acc or sm["accepted"],
        subperiod=sm["period"],
        fy=sm["fy"],
        fp=sm["fp"],
        fye=sm["fye"],
        prevrpt=sm["prevrpt"],
        tag=num["tag"],
        version=num["version"],
        ddate=num["ddate"],
        qtrs=str(q) if q is not None else num["qtrs"],
        uom=num["uom"],
        segment_hash=digest(num["segments"]),
        segment_nonblank=str(int(bool(num["segments"]))),
        coreg_hash=digest(num["coreg"]),
        coreg_nonblank=str(int(bool(num["coreg"]))),
        value=value,
        value_state=value_state,
        state=state,
        pre_rows=str(pre_counts[(adsh, num["tag"], num["version"])]),
    )
    return output


def main(path):
    receipt = json.loads((ROOT / "data/capture_receipt.json").read_bytes())
    assert (
        path.stat().st_size == receipt["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"]
    )
    zipfile = ZipFile(path)
    assert zipfile.testzip() is None
    counts = {}
    suball = Counter()
    sub = {}
    sub_dup = set()
    count = 0
    for r in rows(zipfile, "sub.txt"):
        count += 1
        cik = r["cik"].lstrip("0") or "0"
        if cik in CIKS and r["form"] in FORMS:
            suball[r["adsh"]] += 1
            if r["adsh"] in sub:
                sub_dup.add(r["adsh"])
            else:
                sub[r["adsh"]] = r
    counts["sub.txt"] = count
    tag_keys = set()
    count = 0
    for r in rows(zipfile, "tag.txt"):
        count += 1
        if r["tag"] in TAGS and r["version"].startswith("us-gaap/"):
            tag_keys.add((r["tag"], r["version"]))
    counts["tag.txt"] = count
    pre = Counter()
    count = 0
    for r in rows(zipfile, "pre.txt"):
        count += 1
        if r["adsh"] in sub and r["tag"] in TAGS:
            pre[(r["adsh"], r["tag"], r["version"])] += 1
    counts["pre.txt"] = count
    selected = []
    count = 0
    selected_accession_rows = 0
    for r in rows(zipfile, "num.txt"):
        count += 1
        if r["adsh"] not in sub:
            continue
        selected_accession_rows += 1
        if r["tag"] in TAGS and r["version"].startswith("us-gaap/"):
            selected.append(r)
    counts["num.txt"] = count
    fullcounts = Counter(full_identity(r) for r in selected)
    duplicate_keys = {k for k, n in fullcounts.items() if n > 1}
    projected = Counter()
    states = Counter()
    value_states = Counter()
    for r in selected:
        item = project(r, sub, sub_dup, tag_keys, pre, duplicate_keys)
        states[item["state"]] += 1
        value_states[item["value_state"]] += 1
        projected[tuple(item[k] for k in FIELDS[:-1])] += 1
    output = []
    for key, multiplicity in sorted(projected.items()):
        item = dict(zip(FIELDS[:-1], key))
        item["source_records"] = str(multiplicity)
        output.append(item)
    with (ROOT / "data/facts.csv").open("w", encoding="utf-8", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(output)
    sf = [
        "cik",
        "adsh",
        "form",
        "filed",
        "accepted",
        "subperiod",
        "fy",
        "fp",
        "fye",
        "prevrpt",
        "native_sub_records",
    ]
    with (ROOT / "data/submissions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        w = csv.DictWriter(stream, fieldnames=sf, lineterminator="\n")
        w.writeheader()
        for adsh, r in sorted(sub.items()):
            w.writerow(
                dict(
                    zip(
                        sf,
                        [
                            r["cik"].lstrip("0") or "0",
                            adsh,
                            r["form"],
                            r["filed"],
                            accepted(r["accepted"]) or r["accepted"],
                            r["period"],
                            r["fy"],
                            r["fp"],
                            r["fye"],
                            r["prevrpt"],
                            suball[adsh],
                        ],
                    )
                )
            )
    summary = dict(
        native_rows=counts,
        selected_accessions=len(sub),
        selected_accession_num_rows=selected_accession_rows,
        selected_fact_rows=len(selected),
        projected_fact_cells=len(output),
        eligible_fact_rows=states["ELIGIBLE"],
        source_state_accounts=dict(sorted(states.items())),
        numeric_value_accounts=dict(sorted(value_states.items())),
        duplicate_sub_keys=len(sub_dup),
        duplicate_full_fact_keys=len(duplicate_keys),
        company_submission_counts={
            cik: sum(r["cik"].lstrip("0") == cik for r in sub.values()) for cik in CIKS
        },
        company_fact_counts={
            cik: sum(int(r["source_records"]) for r in output if r["cik"] == cik)
            for cik in CIKS
        },
        source_sha256=receipt["sha256"],
        scope="Current reprocessed face-financial facts,complete fixed cohort and context;not source truth,verified restatements,exact fiscal boundaries or original-time availability.",
    )
    (ROOT / "data/source_accounts.json").write_bytes(
        (json.dumps(summary, indent=2) + "\n").encode()
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    main(p.parse_args().archive)
