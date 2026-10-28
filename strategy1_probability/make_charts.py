"""Charts for the Strategy 1 explainer. Reads results/strategy1_results.json."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from chart_style import SERIES, SURFACE, TEXT_2, hbar, plt, setup  # noqa: E402

RES = HERE / "results"


def main():
    setup()
    r = json.loads((RES / "strategy1_results.json").read_text())

    # 1. Game 2: soldiers needed for an 80% chance of winning a castle, vs 1 and vs 3 opponents
    rules = r["game2_rules"]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(rules))
    one = [row["soldiers_for_80pct_vs_1"] for row in rules]
    three = [row["soldiers_for_80pct_vs_3"] for row in rules]
    ax.barh(y - 0.17, one, height=0.32, color=SERIES[0], edgecolor=SURFACE, linewidth=2, label="vs 1 opponent (Game 1)", zorder=3)
    ax.barh(y + 0.17, three, height=0.32, color=SERIES[1], edgecolor=SURFACE, linewidth=2, label="vs 3 opponents (Game 2)", zorder=3)
    for yi, a, b in zip(y, one, three):
        ax.text(a + 0.8, yi - 0.17, str(a), va="center", fontsize=8, color=TEXT_2)
        ax.text(b + 0.8, yi + 0.17, str(b), va="center", fontsize=8, color=TEXT_2)
    ax.set_yticks(y)
    ax.set_yticklabels([f"Castle {row['castle']} ({row['points']} pt)" for row in rules])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Soldiers needed for an 80% chance to win the castle outright")
    ax.set_title("Why Game 2 punishes spreading out")
    ax.set_xlim(0, max(three) * 1.1)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2)
    fig.tight_layout()
    fig.savefig(RES / "fig_game2_cost_to_win.png", dpi=150)
    plt.close(fig)

    # 2. Candidate allocations under the probability model, one panel per game
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, rows, key, title in ((axes[0], r["game1"]["comparison"], "mean", "Game 1: expected score (of 15)"),
                                 (axes[1], r["game2"]["comparison"][:12], "mean_payout", "Game 2: expected payout (of 9)")):
        pick = r["game1"]["pick"] if ax is axes[0] else r["game2"]["pick"]
        labels = [f"{row['alloc']}  ({row['name']})" if row["name"] != row["alloc"] else row["alloc"] for row in rows]
        colors = [SERIES[1] if row["alloc"] == pick else SERIES[0] for row in rows]
        hbar(ax, labels, [row[key] for row in rows], colors)
        ax.set_title(title)
    fig.suptitle("Orange = the recommended pick. Averaged over every field hypothesis in the model.",
                 x=0.01, ha="left", fontsize=9, color=TEXT_2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(RES / "fig_candidates.png", dpi=150)
    plt.close(fig)
    print("charts written to", RES)


if __name__ == "__main__":
    main()
