"""Build the 100-contestant population for Strategy 2.

Every contestant is handed the same prompt (Trial.txt) and solves it on their
own. Variance comes from *how* they approach it, mirroring an applicant pool
in which most people use AI:

  AI-assisted (50)
    30  ai_verbatim     real Claude subagents (haiku/sonnet/opus x 5 prompt styles x 2),
                        answer submitted exactly as the AI gave it (contestants/ai_contestants.json)
     7  ai_round        asked an AI, then rounded its numbers to multiples of 5
     7  ai_gut          asked an AI, then moved a handful of soldiers to the castle that 'felt' key
     6  ai_plus1        asked an AI, then added +1 on round-number castles to win ties
  Metastrategists (15) - reason explicitly about the other applicants
     3  meta_level2     assume the field is proportional/AI-ish, compute the exact best response
     3  meta_simulator  imagine their own population, simulate it, best-respond (like this project)
     3  meta_ai_sampler ask the AI 5-10 times to see what AI users will submit, then best-respond
     3  meta_equilibrium play a random draw from the Blotto Nash equilibrium in both games
     3  meta_contrarian predict the crowd fights over castles 4-5 and build around skipping one
  Humans without AI (35)
     7  human_proportional  soldiers proportional to points, rounded by hand
     5  human_round         'nice' round-number ladders
     4  human_even          20 everywhere or nearly
     5  human_top_heavy     drop the cheap castles, stack 3-5 or 4-5
     3  human_all_in        everything on one or two castles
     4  human_plus1         'everyone does X, I'll do X+1'
     4  human_random        low effort / arbitrary
     3  human_underdog      fight for the castles they think others ignore

The 65% AI-influenced share follows the user's assumption that most applicants
use AI. run_simulation.py varies the mix for sensitivity analysis.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from castle import (VALUES, all_allocations, fix_total, fmt, game1_best_response,  # noqa: E402
                    game1_equilibrium, game1_tables, game2_best_response, jitter, round_to)

AI_PATH = HERE / "contestants" / "ai_contestants.json"

BASE_MIX = {
    "ai_verbatim": 30, "ai_round": 7, "ai_gut": 7, "ai_plus1": 6,
    "meta_level2": 3, "meta_simulator": 3, "meta_ai_sampler": 3, "meta_equilibrium": 3, "meta_contrarian": 3,
    "human_proportional": 7, "human_round": 5, "human_even": 4, "human_top_heavy": 5,
    "human_all_in": 3, "human_plus1": 4, "human_random": 4, "human_underdog": 3,
}
CATEGORY = {k: ("AI-assisted" if k.startswith("ai_") else "Metastrategist" if k.startswith("meta_") else "Human")
            for k in BASE_MIX}
DESCRIPTION = {
    "ai_verbatim": "Pasted the prompt into an AI chatbot and submitted its answer unchanged.",
    "ai_round": "Asked an AI, then rounded the numbers to multiples of 5 because they looked cleaner.",
    "ai_gut": "Asked an AI, then moved a few soldiers onto the castle that felt most important.",
    "ai_plus1": "Asked an AI, then bumped round-number castles by +1 to win ties.",
    "meta_level2": "Assumed most entries are proportional or AI '+1' answers and computed the exact best response.",
    "meta_simulator": "Imagined a population of applicants, simulated both games, and best-responded to it.",
    "meta_ai_sampler": "Asked the AI several times to see what AI users would submit, then best-responded to that.",
    "meta_equilibrium": "Played a random draw from the Colonel Blotto Nash equilibrium (unexploitable on average).",
    "meta_contrarian": "Predicted the crowd would fight over castles 4-5 and built around skipping one of them.",
    "human_proportional": "Split soldiers in proportion to castle points, rounding by hand.",
    "human_round": "Used a tidy round-number ladder.",
    "human_even": "Put about 20 on every castle.",
    "human_top_heavy": "Ignored the cheap castles and stacked the valuable ones.",
    "human_all_in": "Bet everything on one or two castles.",
    "human_plus1": "Guessed what most people do and added one soldier to beat it.",
    "human_random": "Low effort: typed numbers that roughly added up.",
    "human_underdog": "Fought for the cheap castles everyone else ignores.",
}

_A = all_allocations()
_EQ = None


def eq_sample():
    global _EQ
    if _EQ is None:
        _EQ = game1_equilibrium(4000)
    return _EQ


def load_ai():
    return json.loads(AI_PATH.read_text(encoding="utf-8"))


def move(a, src, dst, k):
    a = np.array(a, dtype=int)
    k = min(k, a[src])
    a[src] -= k
    a[dst] += k
    return a


def plus1(a, rng):
    """Add +1 to castles holding a multiple of 5 (>0), funding it from the smallest non-zero pile."""
    a = np.array(a, dtype=int)
    for i in range(4, 1, -1):
        if a[i] > 0 and a[i] % 5 == 0:
            donors = [j for j in np.argsort(a) if a[j] > 0 and j != i and not (a[j] % 5 == 0 and j > 1)]
            if not donors:
                donors = [j for j in np.argsort(a) if a[j] > 1 and j != i]
            if donors:
                a = move(a, donors[0], i, 1)
    return a


def value_split(subset, gamma, rng, token_max=0):
    """Spread 100 over a castle subset with weight value**gamma (+ optional tokens elsewhere)."""
    a = np.zeros(5)
    tokens = 0
    for i in range(5):
        if i not in subset and token_max:
            t = rng.integers(0, token_max + 1)
            a[i] = t
            tokens += t
    w = VALUES[list(subset)] ** gamma
    a[list(subset)] = w / w.sum() * (100 - tokens)
    return fix_total(np.floor(a))


# --------------------------------------------------------------------------
# Archetype generators: each returns (game1, game2, reasoning)
# --------------------------------------------------------------------------
def gen_ai_round(rng, ai):
    b = ai[rng.integers(len(ai))]
    return (round_to(b["game1"], 5), round_to(b["game2"], 5),
            f"AI ({b['model']}) suggested {fmt(b['game1'])} and {fmt(b['game2'])}; I rounded to 5s.")


def gen_ai_gut(rng, ai):
    b = ai[rng.integers(len(ai))]
    out = []
    for g in (b["game1"], b["game2"]):
        a = np.array(g)
        dst = rng.choice([4, 3, 2], p=[0.6, 0.25, 0.15])
        src = rng.choice([i for i in range(5) if i != dst and a[i] > 0] or [int(np.argmax(a))])
        out.append(move(a, src, dst, int(rng.integers(3, 11))))
    return out[0], out[1], f"AI ({b['model']}) suggested {fmt(b['game1'])}; I trusted my gut and moved a few soldiers."


def gen_ai_plus1(rng, ai):
    b = ai[rng.integers(len(ai))]
    return (plus1(b["game1"], rng), plus1(b["game2"], rng),
            f"AI ({b['model']}) suggested {fmt(b['game1'])}; I added +1 to round numbers to win ties.")


def _guess_field(rng, kind):
    """A metastrategist's *belief* about the field (their own guess, not the real population)."""
    menu_g1 = [(7, 13, 20, 27, 33), (10, 15, 20, 25, 30), (20, 20, 20, 20, 20), (0, 10, 20, 30, 40),
               (0, 0, 33, 33, 34), (1, 2, 21, 31, 45), (2, 12, 22, 28, 36), (0, 0, 20, 30, 50), (5, 10, 20, 30, 35)]
    menu_g2 = [(0, 0, 33, 33, 34), (0, 0, 0, 50, 50), (0, 0, 20, 30, 50), (0, 0, 0, 45, 55), (0, 0, 35, 0, 65),
               (0, 10, 20, 30, 40), (7, 13, 20, 27, 33), (0, 0, 0, 0, 100), (0, 0, 25, 35, 40)]
    if kind == "level2":   # mostly proportional / AI-ish
        w1 = np.array([5, 2, 2, 2, 1.5, 2, 2, 1, 1.5]) * rng.uniform(0.5, 1.5, 9)
        w2 = np.array([3, 3, 2, 1, 1, 1.5, 1.5, 0.5, 1.5]) * rng.uniform(0.5, 1.5, 9)
    else:                  # simulator: a personal random mix of everything
        w1 = rng.dirichlet(np.ones(9))
        w2 = rng.dirichlet(np.ones(9))
    def build(menu, w):
        pick = rng.choice(len(menu), size=600, p=w / w.sum())
        rows = [jitter(menu[k], rng, rng.poisson(2)) for k in pick]
        n_rand = int(rng.uniform(0.05, 0.2) * 600)
        rows += list(_A[rng.integers(len(_A), size=n_rand)])
        return np.array(rows)
    return build(menu_g1, w1), build(menu_g2, w2)


def _meta_best(rng, kind):
    f1, f2 = _guess_field(rng, kind)
    g1, _ = game1_best_response(game1_tables(f1))
    br, _ = game2_best_response(f2, rng, k_coarse=500, k_fine=1200, n_seeds=3)
    return g1, br[0]


def gen_meta_level2(rng, ai):
    g1, g2 = _meta_best(rng, "level2")
    return g1, g2, "Assumed mostly proportional / AI-style entries and computed the exact best response to that guess."


def gen_meta_simulator(rng, ai):
    g1, g2 = _meta_best(rng, "simulator")
    return g1, g2, "Built my own imagined field of applicant types, simulated both games, submitted the best responses."


def gen_meta_ai_sampler(rng, ai):
    """Query the AI k times (k independent AI answers), add a guessed share of humans, best-respond."""
    k = int(rng.integers(5, 11))
    seen = [ai[i] for i in rng.choice(len(ai), size=k, replace=False)]
    human_share = rng.uniform(0.2, 0.45)
    h1, h2 = _guess_field(rng, "level2")
    n_ai = 60 * k
    n_h = int(n_ai * human_share / (1 - human_share))
    f1 = np.vstack([np.array([jitter(s["game1"], rng, rng.poisson(1)) for s in seen for _ in range(60)]), h1[:n_h]])
    f2 = np.vstack([np.array([jitter(s["game2"], rng, rng.poisson(1)) for s in seen for _ in range(60)]), h2[:n_h]])
    g1, _ = game1_best_response(game1_tables(f1))
    br, _ = game2_best_response(f2, rng, k_coarse=500, k_fine=1200, n_seeds=3)
    return g1, br[0], (f"Asked the AI {k} times to see what AI users will submit, assumed ~{int(human_share * 100)}% "
                       f"non-AI entries, and best-responded to that field.")


def gen_meta_equilibrium(rng, ai):
    eq = eq_sample()
    return (eq[rng.integers(len(eq))], eq[rng.integers(len(eq))],
            "Played a random draw from the Blotto Nash equilibrium in both games so nobody can exploit me on average.")


def gen_meta_contrarian(rng, ai):
    g1_sets = [((0, 1, 2, 3), "skip castle 5"), ((1, 2, 4), "skip castles 1 and 4"), ((0, 1, 2, 3), "skip castle 5")]
    g2_sets = [((0, 1, 2), "lock castles 1-3"), ((2, 4), "castles 3+5"), ((2, 3), "castles 3+4"),
               ((1, 2, 3), "castles 2-4")]
    s1, why1 = g1_sets[rng.integers(len(g1_sets))]
    s2, why2 = g2_sets[rng.integers(len(g2_sets))]
    g1 = jitter(value_split(s1, rng.uniform(0.6, 1.2), rng, token_max=4), rng, rng.poisson(1))
    g2 = jitter(value_split(s2, rng.uniform(0.6, 1.4), rng), rng, rng.poisson(1))
    return g1, g2, f"The crowd will overspend on castles 4-5, so Game 1: {why1}; Game 2: {why2}."


def gen_human_proportional(rng, ai):
    exact = 100 * VALUES / 15
    style = rng.integers(3)
    g1 = fix_total(np.round(exact) if style == 0 else np.floor(exact) if style == 1 else np.ceil(exact) - [0, 0, 0, 1, 2])
    g1 = jitter(g1, rng, rng.poisson(1))
    g2 = g1 if rng.random() < 0.5 else move(move(g1, 0, 4, int(rng.integers(3, 8))), 1, 3, int(rng.integers(3, 10)))
    return g1, g2, "Points-proportional split; for Game 2 I either kept it or leaned harder on the top castles."


def gen_human_round(rng, ai):
    t1 = [(10, 15, 20, 25, 30), (0, 10, 20, 30, 40), (5, 10, 20, 30, 35), (5, 15, 20, 25, 35), (10, 10, 20, 30, 30)]
    t2 = [(0, 0, 20, 30, 50), (0, 0, 30, 30, 40), (0, 10, 20, 30, 40), (0, 0, 25, 35, 40)]
    g1 = np.array(t1[rng.integers(len(t1))])
    g2 = g1 if rng.random() < 0.4 else np.array(t2[rng.integers(len(t2))])
    return g1, g2, "Round numbers that climb with castle value."


def gen_human_even(rng, ai):
    g1 = np.full(5, 20) if rng.random() < 0.6 else jitter(np.full(5, 20), rng, rng.integers(1, 4))
    g2 = g1 if rng.random() < 0.5 else np.array([0, 0, 33, 33, 34])
    return g1, g2, "Even split so I'm competitive everywhere."


def gen_human_top_heavy(rng, ai):
    t1 = [(0, 0, 33, 33, 34), (0, 0, 20, 30, 50), (0, 0, 25, 35, 40), (0, 5, 15, 30, 50), (0, 0, 30, 30, 40)]
    t2 = [(0, 0, 0, 50, 50), (0, 0, 0, 40, 60), (0, 0, 33, 33, 34), (0, 0, 20, 30, 50)]
    g1 = jitter(t1[rng.integers(len(t1))], rng, rng.poisson(0.7))
    g2 = jitter(t2[rng.integers(len(t2))], rng, rng.poisson(0.7))
    return g1, g2, "Castles 1-2 aren't worth fighting for; stack the big ones."


def gen_human_all_in(rng, ai):
    t1 = [(0, 0, 0, 50, 50), (0, 0, 0, 0, 100), (0, 0, 0, 45, 55)]
    t2 = [(0, 0, 0, 0, 100), (0, 0, 0, 50, 50), (0, 0, 0, 40, 60)]
    return (np.array(t1[rng.integers(len(t1))]), np.array(t2[rng.integers(len(t2))]),
            "Go big or go home: guarantee the most valuable castles.")


def gen_human_plus1(rng, ai):
    base = [np.array([7, 13, 20, 27, 33]), np.full(5, 20), np.array([10, 15, 20, 25, 30])][rng.integers(3)]
    g1 = base.copy()
    g1[1:] += 1
    g1[0] = 0
    g1[4] += 100 - g1.sum()   # spare soldiers go to the 5-point castle
    g2 = [np.array([0, 0, 34, 32, 34]), np.array([0, 0, 0, 49, 51]), np.array([1, 1, 32, 32, 34]), g1][rng.integers(4)]
    return jitter(g1, rng, rng.poisson(0.5)), g2, f"Most people will play {fmt(base)}, so I went one above it where it counts."


def gen_human_random(rng, ai):
    out = []
    for _ in range(2):
        a = rng.dirichlet(np.full(5, 2.0)) * 100
        a = round_to(a, 5) if rng.random() < 0.6 else fix_total(np.round(a))
        out.append(a)
    return out[0], out[1], "Didn't overthink it."


def gen_human_underdog(rng, ai):
    t1 = [(15, 20, 20, 20, 25), (10, 20, 30, 40, 0), (12, 18, 25, 25, 20)]
    t2 = [(25, 25, 50, 0, 0), (20, 30, 50, 0, 0), (10, 20, 30, 40, 0)]
    return (jitter(t1[rng.integers(len(t1))], rng, rng.poisson(1)),
            jitter(t2[rng.integers(len(t2))], rng, rng.poisson(1)),
            "Everyone will fight over the big castles; I'll take what they leave.")


GENERATORS = {k: globals()[f"gen_{k}"] for k in BASE_MIX if k != "ai_verbatim"}


def strategy_text(archetype, g1, g2):
    changed = "kept the same idea" if fmt(g1) == fmt(g2) else "changed my allocation"
    return (f"{DESCRIPTION[archetype]} Game 1: {fmt(g1)}. Game 2: {fmt(g2)}; I {changed} because only "
            f"finishing position counts in the four-way game.")


def build_population(seed, mix=None, ai=None, ai_mode="fixed", meta_library=None):
    """Return a list of contestant dicts.

    ai_mode="fixed": the 30 real AI answers are used once each (the baseline run).
    ai_mode="bootstrap": AI-verbatim slots are filled by resampling AI answers
    with replacement (used for replications and mixes with a different AI share).
    meta_library: optional {archetype: [(g1, g2, reasoning), ...]} of precomputed
    metastrategist outputs, so replications don't redo their expensive searches.
    """
    rng = np.random.default_rng(seed)
    mix = mix or BASE_MIX
    ai = ai or load_ai()
    people = []
    n_ai = mix.get("ai_verbatim", 0)
    if ai_mode == "fixed" and n_ai == len(ai):
        ai_rows = ai
    else:
        ai_rows = [ai[i] for i in rng.integers(len(ai), size=n_ai)]
    for k, r in enumerate(ai_rows):
        people.append({"id": f"P{len(people) + 1:03d}", "source_ai_id": r["id"], "archetype": "ai_verbatim",
                       "category": CATEGORY["ai_verbatim"], "model": r["model"], "framing": r["framing"],
                       "game1": list(map(int, r["game1"])), "game2": list(map(int, r["game2"])),
                       "reasoning": r["reasoning_summary"], "strategy_text": r["strategy_text"]})
    for arch, count in mix.items():
        if arch == "ai_verbatim":
            continue
        for _ in range(count):
            sub = np.random.default_rng(rng.integers(2**63))   # each contestant thinks independently
            if meta_library and arch in meta_library:
                lib = meta_library[arch]
                g1, g2, why = lib[sub.integers(len(lib))]
            else:
                g1, g2, why = GENERATORS[arch](sub, ai)
            g1, g2 = fix_total(g1), fix_total(g2)
            people.append({"id": f"P{len(people) + 1:03d}", "archetype": arch, "category": CATEGORY[arch],
                           "game1": list(map(int, g1)), "game2": list(map(int, g2)), "reasoning": why,
                           "strategy_text": strategy_text(arch, g1, g2)})
    return people


def build_meta_library(seed, per_type=12, ai=None):
    """Precompute many independent metastrategist decisions for fast replications."""
    rng = np.random.default_rng(seed)
    ai = ai or load_ai()
    lib = {}
    for arch in ("meta_level2", "meta_simulator", "meta_ai_sampler"):
        lib[arch] = []
        for _ in range(per_type):
            sub = np.random.default_rng(rng.integers(2**63))
            g1, g2, why = GENERATORS[arch](sub, ai)
            lib[arch].append((list(map(int, g1)), list(map(int, g2)), why))
    return lib
