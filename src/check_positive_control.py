"""Check the additional positive control directly against native-bound source fields."""

from pathlib import Path
import csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as f:
        facts = list(csv.DictReader(f))
    actual = json.loads((ROOT / "results/positive_control.json").read_bytes())
    request = json.loads((ROOT / "data/positive_control_input.json").read_bytes())
    require(
        actual["scope"] == "POST_ANALYSIS_POSITIVE_CONTROL"
        and actual["original_seven_requests_changed"] is False,
        "honest timing and scope",
    )
    require(actual["request"] == request, "one exact fixed additive request")
    fields = [
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
    selected = [r for r in facts if all(r[k] == request[k] for k in fields)]
    require(
        len(selected) == 1
        and selected[0]["state"] == "ELIGIBLE"
        and selected[0]["source_records"] == "1"
        and selected[0]["value_state"] == "KNOWN",
        "unique native-bound current context",
    )
    r = selected[0]
    response = actual["response"]
    require(response["status"] == "ACCEPTED_QUALIFIED", "successful qualified lookup")
    for key in ["value", "uom", "qtrs", "adsh"]:
        require(response[key] == r[key], "actual source value/context")
    require(
        response["source_truth"]
        == response["original_time_availability"]
        == response["formal_restatement"]
        == "UNESTABLISHED",
        "material unknowns retained",
    )
    original = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    require(
        len(original) == 7
        and original[0]["version"] == "us-gaap/2026"
        and request["version"] == "us-gaap/2025",
        "original mistaken assumption retained and correction separate",
    )
    current = json.loads((ROOT / "PLAN_FREEZE.json").read_bytes())
    oldpath = ROOT / current["original_comparison_freeze"]
    old = json.loads(oldpath.read_bytes())
    require(
        hashlib.sha256(oldpath.read_bytes()).hexdigest()
        == current["original_freeze_sha256"],
        "preserved original freeze",
    )
    require(
        [k for k in old["hashes"] if old["hashes"][k] != current["hashes"][k]]
        == ["src/check_analysis.py"],
        "only disclosed checker dependency changed",
    )
    require(
        hashlib.sha256(
            (ROOT / "HISTORY/check_analysis_original.py").read_bytes()
        ).hexdigest()
        == old["hashes"]["src/check_analysis.py"],
        "preserved failed checker bytes",
    )
    for key in [
        "src/analyze.py",
        "src/metrics.py",
        "src/exercise.py",
        "data/exercise_inputs.json",
        "data/facts.csv",
    ]:
        require(
            old["hashes"][key]
            == current["hashes"][key]
            == hashlib.sha256((ROOT / key).read_bytes()).hexdigest(),
            "unchanged source,production formulas and original requests",
        )
    initial = json.loads((ROOT / "HISTORY/initial_result_sha256.json").read_bytes())
    require(len(initial) == 6, "all six initial primary outputs retained")
    for name, digest in initial.items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "unchanged initial result bytes",
        )
    result = dict(
        status="PASS",
        finite_conditions=n,
        positive_controls=1,
        scope="One explicitly post-analysis positive lookup;original seven inputs and production/source unchanged;not a new confirmatory research result.",
    )
    (ROOT / "results/positive_control_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
