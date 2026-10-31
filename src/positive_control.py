"""Run one separately labeled post-analysis positive lookup control."""

from pathlib import Path
import argparse, csv, json
from exercise import answer

ROOT = Path(__file__).resolve().parents[1]


def main(out):
    with (ROOT / "data/facts.csv").open(encoding="utf-8", newline="") as f:
        facts = list(csv.DictReader(f))
    request = json.loads((ROOT / "data/positive_control_input.json").read_bytes())
    result = dict(
        scope="POST_ANALYSIS_POSITIVE_CONTROL",
        original_seven_requests_changed=False,
        request=request,
        response=answer(request, facts),
    )
    data = (json.dumps(result, indent=2) + "\n").encode()
    if out != (ROOT / "results"):
        assert not out.exists()
        out.mkdir(parents=True)
        assert data == (ROOT / "results/positive_control.json").read_bytes()
    else:
        assert not (out / "positive_control.json").exists()
    (out / "positive_control.json").write_bytes(data)
    print("POST_ANALYSIS_POSITIVE_CONTROL", result["response"]["status"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results")
    main(p.parse_args().out)
