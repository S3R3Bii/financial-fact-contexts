"""Independently reconcile all native controls and every projected fact with pandas C and SQLite."""

from pathlib import Path
from zipfile import ZipFile
from datetime import date, datetime
from fractions import Fraction
from collections import Counter
import argparse, csv, hashlib, json, re, sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main(path):
    conditions = 0

    def require(ok, label):
        nonlocal conditions
        assert ok, label
        conditions += 1

    capture = json.loads((ROOT / "data/capture_receipt.json").read_bytes())
    require(path.stat().st_size == capture["bytes"], "native archive size")
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == capture["sha256"],
        "native archive identity",
    )
    z = ZipFile(path)
    require(z.testzip() is None, "all native CRCs")
    controls = {r["name"]: r for r in capture["members"]}
    require(set(z.namelist()) == set(controls), "complete native member inventory")
    for info in z.infolist():
        h = hashlib.sha256()
        with z.open(info) as stream:
            for block in iter(lambda: stream.read(2**20), b""):
                h.update(block)
        require(
            info.file_size == controls[info.filename]["bytes"]
            and h.hexdigest() == controls[info.filename]["sha256"],
            "native member bytes",
        )
    kwargs = dict(
        sep="\t", dtype=str, keep_default_na=False, engine="c", encoding="utf-8-sig"
    )
    suball = pd.read_csv(z.open("sub.txt"), **kwargs)
    require(
        suball.columns.tolist() == controls["sub.txt"]["columns"], "SUB native headers"
    )
    ciks = {"320193", "789019", "104169"}
    tags = {
        "Assets",
        "Liabilities",
        "NetIncomeLoss",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    }
    chosen = suball[
        suball.cik.str.lstrip("0").isin(ciks)
        & suball.form.isin(["10-K", "10-Q", "10-K/A", "10-Q/A"])
    ]
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE sub (adsh TEXT)")
    db.executemany("INSERT INTO sub VALUES (?)", ((v,) for v in chosen.adsh))
    sub_duplicates = {
        r[0] for r in db.execute("SELECT adsh FROM sub GROUP BY adsh HAVING count(*)>1")
    }
    require(not sub_duplicates, "unique selected SUB identity for this source")
    sub = {r["adsh"]: r for r in chosen.to_dict("records")}
    tf = pd.read_csv(z.open("tag.txt"), **kwargs)
    require(tf.columns.tolist() == controls["tag.txt"]["columns"], "TAG native headers")
    tag_selected = tf[tf.tag.isin(tags) & tf.version.str.startswith("us-gaap/")]
    tag_counts = Counter(zip(tag_selected.tag, tag_selected.version))
    require(all(n == 1 for n in tag_counts.values()), "unique selected TAG identity")
    pre = Counter()
    pre_count = 0
    for frame in pd.read_csv(z.open("pre.txt"), chunksize=50000, **kwargs):
        require(
            frame.columns.tolist() == controls["pre.txt"]["columns"],
            "PRE chunk headers",
        )
        pre_count += len(frame)
        selected = frame[frame.adsh.isin(sub) & frame.tag.isin(tags)]
        pre.update(zip(selected.adsh, selected.tag, selected.version))
    selected_rows = []
    num_count = accession_rows = 0
    for frame in pd.read_csv(z.open("num.txt"), chunksize=50000, **kwargs):
        require(
            frame.columns.tolist() == controls["num.txt"]["columns"],
            "NUM chunk headers",
        )
        num_count += len(frame)
        within = frame[frame.adsh.isin(sub)]
        accession_rows += len(within)
        selected_rows.extend(
            within[
                within.tag.isin(tags) & within.version.str.startswith("us-gaap/")
            ].to_dict("records")
        )

    def fractional(token):
        try:
            return Fraction(token)
        except (ValueError, ZeroDivisionError):
            return None

    def whole(token):
        f = fractional(token)
        return f.numerator if f is not None and f.denominator == 1 else None

    def valid_date(token):
        try:
            d = date(int(token[:4]), int(token[4:6]), int(token[6:]))
            return len(token) == 8 and token.isascii() and token.isdigit()
        except (ValueError, TypeError):
            return False

    def timestamp(token):
        base, dot, frac = token.partition(".")
        if len(base) != 19:
            return None
        try:
            datetime.strptime(base, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        if dot and (
            not frac.isascii() or not frac.isdigit() or not 1 <= len(frac) <= 6
        ):
            return None
        return base + "." + (frac if dot else "").ljust(6, "0")

    def context(r):
        q = whole(r["qtrs"])
        return tuple(
            str(q) if k == "qtrs" and q is not None else r[k]
            for k in [
                "adsh",
                "tag",
                "version",
                "ddate",
                "qtrs",
                "uom",
                "segments",
                "coreg",
            ]
        )

    db.execute("CREATE TABLE facts (identity TEXT)")
    db.executemany(
        "INSERT INTO facts VALUES (?)",
        ((json.dumps(context(r), separators=(",", ":")),) for r in selected_rows),
    )
    duplicates = {
        tuple(json.loads(r[0]))
        for r in db.execute(
            "SELECT identity FROM facts GROUP BY identity HAVING count(*)>1"
        )
    }
    fields = [
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
    ]
    expected = Counter()
    states = Counter()
    numeric = Counter()
    for r in selected_rows:
        sm = sub[r["adsh"]]
        q = whole(r["qtrs"])
        acc = timestamp(sm["accepted"])
        identity_ok = (
            bool(re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", r["adsh"]))
            and bool(r["tag"] and r["version"] and r["uom"])
            and valid_date(r["ddate"])
            and q is not None
            and q >= 0
        )
        state = "ELIGIBLE"
        if not identity_ok:
            state = "INVALID_FULL_IDENTITY"
        elif not (valid_date(sm["filed"]) and valid_date(sm["period"]) and acc):
            state = "SUB_IDENTITY_OR_DATE_UNAVAILABLE"
        elif (r["tag"], r["version"]) not in tag_counts:
            state = "MISSING_TAG_IDENTITY"
        elif pre[(r["adsh"], r["tag"], r["version"])] == 0:
            state = "MISSING_PRE_PRESENCE"
        elif context(r) in duplicates:
            state = "DUPLICATE_FULL_IDENTITY"
        f = fractional(r["value"]) if r["value"] else None
        value_state = (
            "MISSING" if r["value"] == "" else "KNOWN" if f is not None else "INVALID"
        )
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest() if text else ""
        values = [
            sm["cik"].lstrip("0") or "0",
            r["adsh"],
            sm["form"],
            sm["filed"],
            acc or sm["accepted"],
            sm["period"],
            sm["fy"],
            sm["fp"],
            sm["fye"],
            sm["prevrpt"],
            r["tag"],
            r["version"],
            r["ddate"],
            str(q) if q is not None else r["qtrs"],
            r["uom"],
            sha(r["segments"]),
            str(int(bool(r["segments"]))),
            sha(r["coreg"]),
            str(int(bool(r["coreg"]))),
            str(f) if value_state == "KNOWN" else "",
            value_state,
            state,
            str(pre[(r["adsh"], r["tag"], r["version"])]),
        ]
        expected[tuple(values)] += 1
        states[state] += 1
        numeric[value_state] += 1
    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        saved = list(reader)
        require(reader.fieldnames == fields + ["source_records"], "minimal fact schema")
    require(len(saved) == len(expected), "complete projection cell set")
    for r in saved:
        key = tuple(
            (
                str(Fraction(r[k]))
                if k == "value" and r["value_state"] == "KNOWN"
                else r[k]
            )
            for k in fields
        )
        require(
            expected.pop(key, None) == int(r["source_records"]),
            "all fact context,metadata,value and multiplicity fields",
        )
    require(not expected, "no omitted native fact")
    with (ROOT / "data/submissions.csv").open(encoding="utf-8", newline="") as stream:
        saved_sub = list(csv.DictReader(stream))
    require(len(saved_sub) == len(sub), "all source submissions")
    for r in saved_sub:
        sm = sub[r["adsh"]]
        expected_sub = dict(
            cik=sm["cik"].lstrip("0") or "0",
            adsh=sm["adsh"],
            form=sm["form"],
            filed=sm["filed"],
            accepted=timestamp(sm["accepted"]) or sm["accepted"],
            subperiod=sm["period"],
            fy=sm["fy"],
            fp=sm["fp"],
            fye=sm["fye"],
            prevrpt=sm["prevrpt"],
            native_sub_records="1",
        )
        require(r == expected_sub, "complete native submission metadata")
    source = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    expected_counts = {
        "sub.txt": len(suball),
        "tag.txt": len(tf),
        "pre.txt": pre_count,
        "num.txt": num_count,
    }
    require(
        source["native_rows"] == expected_counts,
        "all four independent native row totals",
    )
    require(
        source["selected_accessions"] == len(sub)
        and source["selected_accession_num_rows"] == accession_rows,
        "complete selected accession rows",
    )
    require(
        source["selected_fact_rows"] == len(selected_rows)
        and source["projected_fact_cells"] == len(saved),
        "complete six-tag cohort",
    )
    require(
        source["source_state_accounts"] == dict(sorted(states.items()))
        and source["numeric_value_accounts"] == dict(sorted(numeric.items())),
        "complete source and missingness accounts",
    )
    require(
        source["duplicate_sub_keys"] == 0
        and source["duplicate_full_fact_keys"] == len(duplicates),
        "complete duplicate accounts",
    )
    require(
        source["eligible_fact_rows"] == states["ELIGIBLE"]
        and sum(states.values()) == len(selected_rows),
        "complete disjoint source states",
    )
    for cik in ciks:
        require(
            source["company_submission_counts"][cik]
            == sum(sm["cik"].lstrip("0") == cik for sm in sub.values()),
            "all fixed company submission counts",
        )
        require(
            source["company_fact_counts"][cik]
            == sum(
                sm["cik"].lstrip("0") == cik
                for sm in [sub[r["adsh"]] for r in selected_rows]
            ),
            "all fixed company fact counts",
        )
    result = dict(
        status="PASS",
        finite_conditions=conditions,
        native_rows=expected_counts,
        selected_fact_rows=len(selected_rows),
        eligible_fact_rows=states["ELIGIBLE"],
        pandas=pd.__version__,
        native_sha256=capture["sha256"],
        hashes={
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in [
                "data/facts.csv",
                "data/submissions.csv",
                "data/source_accounts.json",
                "data/capture_receipt.json",
            ]
        },
        method="Independent pandas C chunks,Fraction values,SQLite complete key multiplicities,independent timestamp/date parsing and all native/metadata/projection controls;no production imports",
        scope="Current submitted face-financial facts,not source truth,verified restatements or original historical availability.",
    )
    (ROOT / "data/native_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    main(p.parse_args().archive)
