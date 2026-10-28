"""Charts for the Strategy 2 explainer. Reads results/ and contestants/population.json."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from chart_style import CATEGORY_COLOR, SERIES, TEXT_2, hbar, plt, setup  # noqa: E402

RES = HERE / "results"


def main():
    setup()
    r = json.loads((RES / "simulation_results.json").read_text())
    people = json.loads((HERE / "contestants" / "population.json").read_text(encoding="utf-8"))

    # 1. every contestant: Game 1 score vs Game 2 payout, by category
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for cat, col in CATEGORY_COLOR.items():
        pts = [p for p in people if p["category"] == cat]
        ax.scatter([p["game1_score"] for p in pts], [p["game2_payout"] for p in pts], s=46, color=col,
                   edgecolor="#fcfcfb", linewidth=2, zorder=3, label=f"{cat} ({len(pts)})")
    for p in sorted(people, key=lambda p: p["combined_rank"])[:4]:
        ax.annotate(f"{p['id']} {p['archetype']}", (p["game1_score"], p["game2_payout"]), xytext=(6, 4),
                    textcoords="offset points", fontsize=8, color=TEXT_2)
    ax.axvline(7.5, color="#c9c8c2", linewidth=1, zorder=1)
    ax.axhline(3.75, color="#c9c8c2", linewidth=1, zorder=1)
    ax.text(7.55, ax.get_ylim()[1] * 0.98, "average (7.5)", fontsize=8, color=TEXT_2, va="top")
    ax.text(ax.get_xlim()[0] + 0.1, 3.8, "average (3.75)", fontsize=8, color=TEXT_2)
    ax.set_xlabel("Game 1 score (average points per matchup, out of 15)")
    ax.set_ylabel("Game 2 payout (average, out of 9)")
    ax.set_title("All 100 contestants: Game 1 vs Game 2")
    ax.set_xlim(right=ax.get_xlim()[1] + 1.2)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.13), ncol=3)
    fig.tight_layout()
    fig.savefig(RES / "fig_contestants_scatter.png", dpi=150)
    plt.close(fig)

    # 2. archetype averages across replications (small multiples, one per game)
    arch = r["replications"]["by_archetype"]
    cat = {p["archetype"]: p["category"] for p in people}
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5))
    for ax, key, title, fmt in ((axes[0], "game1_mean", "Game 1: average score by strategy type", "{:.2f}"),
                                (axes[1], "game2_mean", "Game 2: average payout by strategy type", "{:.2f}")):
        rows = sorted(arch.items(), key=lambda kv: -kv[1][key])
        hbar(ax, [k for k, _ in rows], [v[key] for _, v in rows], [CATEGORY_COLOR[cat[k]] for k, _ in rows], fmt)
        ax.set_title(title)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CATEGORY_COLOR.values()]
    fig.legend(handles, list(CATEGORY_COLOR), loc="lower center", ncol=3)
    fig.suptitle(f"Averaged over {r['replications']['n']} independent re-draws of the population", x=0.01,
                 ha="left", fontsize=9, color=TEXT_2)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(RES / "fig_archetypes.png", dpi=150)
    plt.close(fig)

    # 3. AI answers by model (the 30 real agents, baseline run)
    by_model = r["baseline"]["ai_by_model"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 2.8))
    models = [m for m in ("haiku", "sonnet", "opus") if m in by_model]
    for ax, key, title in ((axes[0], "game1_mean", "Game 1 average score"), (axes[1], "game2_mean", "Game 2 average payout")):
        hbar(ax, models, [by_model[m][key] for m in models], [SERIES[0]] * len(models))
        ax.set_title(title)
    fig.suptitle("Real AI contestants by model (10 answers each)", x=0.01, ha="left", fontsize=9, color=TEXT_2)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(RES / "fig_ai_models.png", dpi=150)
    plt.close(fig)
    print("charts written to", RES)


if __name__ == "__main__":
    main()
