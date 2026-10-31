"""Independently bind all actual SVG bars to complete financial-context group results."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0
    coordinates = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    rows = read("results/group_accounts.csv")
    levels = ["K0", "K1", "K2", "K3", "K4", "K5"]
    expected = {}
    for i, level in enumerate(levels):
        rr = [r for r in rows if r["level"] == level]
        for field in [
            "groups",
            "rows_beyond_one",
            "numeric_conflict",
            "numeric_disagreements",
        ]:
            value = len(rr) if field == "groups" else sum(int(r[field]) for r in rr)
            expected[(level, field)] = (value, i, 0.6)
        for j, field in enumerate(
            [
                "mixed_duration",
                "mixed_units",
                "mixed_taxonomy",
                "mixed_segment_coreg",
                "mixed_accession",
            ]
        ):
            expected[(level, field)] = (
                sum(int(r[field]) for r in rr),
                i + (j - 2) * 0.16,
                0.14,
            )
    summary = json.loads((ROOT / "results/summary.json").read_bytes())
    figures = json.loads((ROOT / "figures/manifest.json").read_bytes())
    seen = set()
    bindings = set()
    require(len(figures) == 3, "three declared figures")
    for fig in figures:
        tree = ET.fromstring((ROOT / "figures" / (fig["name"] + ".svg")).read_bytes())
        groups = {r.attrib.get("id"): r for r in tree.iter() if r.tag.endswith("g")}
        texts = [
            "".join(r.itertext()).strip() for r in tree.iter() if r.tag.endswith("text")
        ]
        for ext, digest in fig["asset_sha256"].items():
            require(
                hashlib.sha256(
                    (ROOT / "figures" / (fig["name"] + "." + ext)).read_bytes()
                ).hexdigest()
                == digest,
                "current asset SHA256",
            )
        for item in fig["artists"]:
            gid = item["gid"]
            require(gid not in seen, "unique SVG source bar")
            seen.add(gid)
            binding = (item["level"], item["field"])
            require(
                binding in expected and binding not in bindings,
                "complete unique source field/level",
            )
            bindings.add(binding)
            value, position, thickness = expected[binding]
            require(
                item["source_file"] == "results/summary.json"
                and item["field_path"] == ["by_key", item["level"], item["field"]],
                "actual nested source binding",
            )
            require(
                summary["by_key"][item["level"]][item["field"]] == value
                and abs(float(value) - item["value"]) < 1e-12,
                "independent complete group aggregate",
            )
            require(
                item["orientation"] == "horizontal"
                and abs(item["position"] - position) < 1e-12
                and item["thickness"] == thickness,
                "actual source position and scale",
            )
            if "label" in item:
                require(item["label"] in texts, "actual SVG numeric label")
            paths = [x for x in groups[gid].iter() if x.tag.endswith("path")]
            require(len(paths) == 1, "actual bar path")
            numbers = list(
                map(
                    float,
                    re.findall(
                        r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", paths[0].attrib["d"]
                    ),
                )
            )
            require(len(numbers) == 8, "four source-bar corners")
            xs = numbers[::2]
            ys = numbers[1::2]
            a = item["axis_points"]
            lo, hi = a["xlim"]
            bottom, top = a["ylim"]
            x = lambda v: a["left"] + (v - lo) / (hi - lo) * a["width"]
            y = lambda v: a["top"] + (top - v) / (top - bottom) * a["height"]
            if item["orientation"] == "vertical":
                expected_x = [
                    x(item["position"] - item["thickness"] / 2),
                    x(item["position"] + item["thickness"] / 2),
                ]
                expected_y = [y(0), y(float(value))]
            else:
                expected_x = [x(0), x(float(value))]
                expected_y = [
                    y(item["position"] - item["thickness"] / 2),
                    y(item["position"] + item["thickness"] / 2),
                ]
            for actual, target in [
                (min(xs), min(expected_x)),
                (max(xs), max(expected_x)),
                (min(ys), min(expected_y)),
                (max(ys), max(expected_y)),
            ]:
                require(abs(actual - target) < 0.02, "actual SVG source geometry")
                coordinates += 1
        require(
            all(any(level in text for text in texts) for level in levels),
            "all fixed key labels visible",
        )
    require(bindings == set(expected) and len(seen) == 54, "all54 complete source bars")
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        source_bound_artists=len(seen),
        svg_coordinate_conditions=coordinates,
        asset_hashes=9,
        scope="Actual54 source-bound SVG bars,216 corner coordinates,all six key levels,complete context categories and asset hashes;visual review separate,no restatement or accessibility certification.",
    )
    (ROOT / "figures/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
