"""Shared matplotlib styling for the explainer charts (static PNGs for the markdown docs).

Palette: the first three slots of the reference categorical theme (blue, orange,
aqua) - the trio documented as distinguishable for colour-blind readers in every
pairing. Aqua is low-contrast on white, so every chart ships next to a table of
the same numbers in its explainer document.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]   # blue, orange, aqua
CATEGORY_COLOR = {"AI-assisted": SERIES[0], "Metastrategist": SERIES[1], "Human": SERIES[2]}


def setup():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
        "text.color": TEXT, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "grid.linestyle": "-",
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
    })


def hbar(ax, labels, values, colors, value_fmt="{:.2f}", xlabel=""):
    """Horizontal bars with thin marks and the value at each bar tip."""
    y = range(len(labels))
    ax.barh(list(y), values, height=0.55, color=colors, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    span = max(values) if len(values) else 1
    for yi, v in zip(y, values):
        ax.text(v + span * 0.01, yi, value_fmt.format(v), va="center", ha="left", color=TEXT_2, fontsize=9)
    ax.set_xlim(0, span * 1.15)
    ax.set_xlabel(xlabel)
