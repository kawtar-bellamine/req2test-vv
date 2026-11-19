"""Figures for the README, from results/metrics.json."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    m = json.loads((ROOT / "results/metrics.json").read_text())["mutation"]
    out = ROOT / "results/figures"
    fig, ax = plt.subplots(figsize=(8.6, 3.8), dpi=140)
    groups = [("designed_mutants", "30 designed bugs"), ("random_mutants", "200 random bugs")]
    for i, (k, lab) in enumerate(groups):
        n, g = m[k]["naive"], m[k]["generated"]
        b1 = ax.bar(i - 0.2, n["score"], 0.38, color="#9aa7b5", label="1 nominal test per requirement" if i == 0 else None)
        b2 = ax.bar(i + 0.2, g["score"], 0.38, color="#1f5fa8", label="generated suite" if i == 0 else None)
        ax.bar_label(b1, labels=[f"{n['killed']}/{n['total']}"], fontsize=9)
        ax.bar_label(b2, labels=[f"{g['killed']}/{g['total']}"], fontsize=9)
    ax.set_xticks([0, 1]); ax.set_xticklabels([g[1] for g in groups]); ax.set_ylim(0, 1.15)
    ax.set_ylabel("share of bugs caught"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Bugs caught on the software-in-the-loop bench", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "fig1_mutation.png"); plt.close(fig)

    c = m["random_by_technique"]
    items = sorted(((k.replace("without_", ""), v) for k, v in c.items()), key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(8.6, 3.4), dpi=140)
    b = ax.barh([f"without {k} tests" for k, _ in items], [v for _, v in items],
                color=["#e69138" if v < 0.95 else "#9aa7b5" for _, v in items])
    ax.bar_label(b, labels=[f"{v:.0%}" for _, v in items], fontsize=9, padding=3)
    ax.set_xlim(0, 1.1); ax.set_xlabel("share of the 200 random bugs still caught")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("What each technique brings (suite with one technique removed)", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "fig2_techniques.png"); plt.close(fig)


if __name__ == "__main__":
    main()
