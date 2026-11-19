"""Figure for the README: mutation score against the test budget, requirement-based against random."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    r = json.loads((ROOT / "results/fret_metrics.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), dpi=130)
    for ax, case in zip(axes, ("LiquidMixer", "FSM")):
        b = r[case]["budget"]
        for key, c, lab in (("generated", "#1f5fa8", "requirement-based"), ("random", "#9aa7b5", "random, same steps")):
            per = sorted({x["per_req"] for x in b})
            xs = [np.mean([x["steps"] for x in b if x["per_req"] == p]) for p in per]
            ys = [np.mean([x[key] for x in b if x["per_req"] == p]) for p in per]
            ax.plot(xs, ys, "o-", color=c, label=lab)
        g = r[case]["generated"]
        ax.set_title(f"{case}: {g['mutants']} mutants of the implementation", fontsize=10.5)
        ax.set_xlabel("test steps"); ax.set_ylabel("mutants killed"); ax.set_ylim(0.7, 1.0)
        ax.axhline(1.0, color="k", lw=0.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    fig.suptitle("Real requirements (NASA FRET case studies): the surviving mutants are behaviours the requirements "
                 "do not constrain", fontsize=10.5)
    fig.tight_layout(); fig.savefig(ROOT / "results/figures/fig_fret_mutation.png"); plt.close(fig)


if __name__ == "__main__":
    main()
