"""Render every declared key level and all omitted-context accounts."""

from pathlib import Path
import hashlib, json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ["K0", "K1", "K2", "K3", "K4", "K5"]
LABELS = [
    "K0  Company / tag / end",
    "K1  + duration",
    "K2  + unit",
    "K3  + taxonomy",
    "K4  + segment / coreg",
    "K5  + accession",
]


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "financial-fact-contexts",
        }
    )
    summary = json.loads((ROOT / "results/summary.json").read_bytes())
    source = summary["by_key"]
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    manifest = []
    palette = ["#177f83", "#d18a22", "#5d59b1", "#bc5262", "#657182"]

    def bar(ax, level, field, position, thickness, color):
        value = source[level][field]
        patch = ax.barh(position, value, height=thickness, color=color)[0]
        gid = "source-" + str(len(manifest)) + "-" + str(len(items))
        patch.set_gid(gid)
        label = format(value, ",")
        ax.annotate(
            label,
            (value, position),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
        items.append(
            (
                dict(
                    gid=gid,
                    level=level,
                    field=field,
                    source_file="results/summary.json",
                    field_path=["by_key", level, field],
                    value=float(value),
                    position=position,
                    thickness=thickness,
                    orientation="horizontal",
                    label=label,
                ),
                ax,
            )
        )

    def finish(fig, name):
        fig.canvas.draw()
        width, height = fig.get_size_inches() * 72
        for item, ax in items:
            box = ax.get_position()
            item["axis_points"] = dict(
                left=float(box.x0 * width),
                top=float((1 - box.y1) * height),
                width=float(box.width * width),
                height=float(box.height * height),
                xlim=list(map(float, ax.get_xlim())),
                ylim=list(map(float, ax.get_ylim())),
            )
        for ext in ["png", "svg", "pdf"]:
            metadata = (
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None} if ext == "pdf" else None
            )
            fig.savefig(
                folder / (name + "." + ext),
                dpi=160,
                facecolor="white",
                metadata=metadata,
            )
        p = folder / (name + ".svg")
        p.write_bytes(
            (
                "\n".join(
                    x.rstrip() for x in p.read_text(encoding="utf-8").splitlines()
                )
                + "\n"
            ).encode()
        )
        manifest.append(
            dict(
                name=name,
                artists=[r for r, ax in items],
                asset_sha256={
                    ext: hashlib.sha256(
                        (folder / (name + "." + ext)).read_bytes()
                    ).hexdigest()
                    for ext in ["png", "svg", "pdf"]
                },
            )
        )
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.73, bottom=0.15, wspace=0.5)
    fig.suptitle(
        "A short financial key drops distinct source contexts",
        x=0.06,
        ha="left",
        y=0.98,
        fontsize=16,
    )
    fig.text(
        0.06,
        0.9,
        format(summary["eligible_facts"], ",")
        + " source facts stay fixed; all six declared key specifications are retained",
        fontsize=11,
    )
    items = []
    for j, field in enumerate(["groups", "rows_beyond_one"]):
        ax = axes[j]
        for i, level in enumerate(LEVELS):
            bar(ax, level, field, i, 0.6, palette[j])
        ax.set_yticks(range(6), LABELS if j == 0 else LEVELS)
        ax.invert_yaxis()
        ax.set_xlim(0, summary["eligible_facts"] * 1.18)
        ax.set_xlabel("Current source count")
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
    axes[0].set_title("Groups retained by the key", loc="left", fontsize=11, pad=18)
    axes[1].set_title(
        "Extra contexts a one-row join would drop", loc="left", fontsize=11, pad=18
    )
    fig.text(
        0.06,
        0.035,
        "K4 matches the full key in this cohort because each company has one selected accession; accession remains part of source identity.",
        fontsize=9,
    )
    finish(fig, "key_retention")
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.subplots_adjust(left=0.25, right=0.94, top=0.72, bottom=0.15)
    fig.suptitle(
        "Duration and segment context explain the observed collisions",
        x=0.06,
        ha="left",
        y=0.98,
        fontsize=15,
    )
    fig.text(
        0.06,
        0.91,
        "Counts refer to groups mixing each field; all zero categories remain visible",
        fontsize=11,
    )
    items = []
    fields = [
        "mixed_duration",
        "mixed_units",
        "mixed_taxonomy",
        "mixed_segment_coreg",
        "mixed_accession",
    ]
    names = ["Duration", "Unit", "Taxonomy", "Segment / coreg", "Accession"]
    for i, level in enumerate(LEVELS):
        for j, field in enumerate(fields):
            bar(ax, level, field, i + (j - 2) * 0.16, 0.14, palette[j])
    ax.set_yticks(range(6), LABELS)
    ax.invert_yaxis()
    ax.set_xlim(
        0, max(source[level][field] for level in LEVELS for field in fields) * 1.25
    )
    ax.set_xlabel("Groups mixing more than one distinct source context")
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    fig.legend(
        handles=[Patch(color=c, label=n) for c, n in zip(palette, names)],
        loc="center",
        bbox_to_anchor=(0.57, 0.82),
        ncol=5,
        frameon=False,
        fontsize=10,
    )
    fig.text(
        0.06,
        0.035,
        "No unit, taxonomy or accession mixtures occur within the fixed base groups here; the source still requires those fields.",
        fontsize=9,
    )
    finish(fig, "context_collisions")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.73, bottom=0.15, wspace=0.5)
    fig.suptitle(
        "Different numeric values can describe different quantities",
        x=0.06,
        ha="left",
        y=0.98,
        fontsize=15,
    )
    fig.text(
        0.06,
        0.9,
        "Authored naive-winner simulation; different durations or dimensions do not establish a formal restatement",
        fontsize=11,
    )
    items = []
    for j, field in enumerate(["numeric_conflict", "numeric_disagreements"]):
        ax = axes[j]
        for i, level in enumerate(LEVELS):
            bar(ax, level, field, i, 0.6, palette[j])
        ax.set_yticks(range(6), LABELS if j == 0 else LEVELS)
        ax.invert_yaxis()
        ax.set_xlim(0, max(source[level][field] for level in LEVELS) * 1.25)
        ax.set_xlabel("Current source count")
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
    axes[0].set_title(
        "Groups with different numeric values", loc="left", fontsize=11, pad=18
    )
    axes[1].set_title(
        "Facts differing from the authored winner", loc="left", fontsize=11, pad=18
    )
    fig.text(
        0.06,
        0.035,
        "Conflicting-group count need not fall at every step: adding duration can split one mixed group into several conflicting groups.",
        fontsize=9,
    )
    finish(fig, "numeric_disagreement")
    (folder / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print("THREE_SOURCE_BOUND_FIGURES", sum(len(r["artists"]) for r in manifest))


if __name__ == "__main__":
    main()
