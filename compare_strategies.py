"""Put the two strategies against each other and pick a final submission.

Strategy 1 models the field as a probability distribution (level-k / cognitive
hierarchy over a grid of hypotheses). Strategy 2 models it as 100 individual
contestants (30 real AI answers + 70 modelled people), re-drawn many times.
This script:
  1. scores every interesting allocation in BOTH models,
  2. searches for a consensus allocation that maximises the average of the two
     models (equal weight), and
  3. writes results/comparison.json for the top-level README.

Run after strategy1_probability/analysis.py and strategy2_simulation/run_simulation.py:
    python compare_strategies.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "shared"))
from castle import (all_allocations, fmt, game1_best_response, game1_scores, game1_tables,  # noqa: E402
                    game2_detail, game2_expected, neighbours, sample_triples)

OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)


def parse(s):
    return np.array([int(x) for x in s.split("/")])


def hill_climb(seeds, triples):
    finals = []
    for s in np.unique(np.array(seeds), axis=0):
        cur = np.asarray(s, dtype=np.int16)
        cur_v = game2_expected(cur[None], triples)[0]
        for _ in range(60):
            nb = neighbours(cur)
            v = game2_expected(nb, triples)
            j = int(np.argmax(v))
            if v[j] <= cur_v + 1e-9:
                break
            cur, cur_v = nb[j], v[j]
        finals.append(cur)
    return np.unique(np.array(finals), axis=0)


def main():
    rng = np.random.default_rng(99)
    s1 = json.loads((ROOT / "strategy1_probability/results/strategy1_results.json").read_text())
    s2 = json.loads((ROOT / "strategy2_simulation/results/simulation_results.json").read_text())
    m1 = np.load(ROOT / "strategy1_probability/results/model_fields.npz")
    m2 = np.load(ROOT / "strategy2_simulation/results/model_fields.npz")
    ai = json.loads((ROOT / "strategy2_simulation/contestants/ai_contestants.json").read_text(encoding="utf-8"))

    # ---- model 1 (probability) ----
    T1 = m1["g1_tables"]                                   # (H1, 5, 101)
    trip1 = m1["g2_triples"]                               # (H2, K, 3, 5)
    # ---- model 2 (simulation) ----
    F1, F2 = m2["g1_fields"], m2["g2_fields"]              # (R, 100, 5)
    S1c, S2c = m2["g1_scores"], m2["g2_payouts"]           # contestants' scores per replication
    T2 = np.array([game1_tables(f) for f in F1])           # (R, 5, 101)
    trip2 = np.array([sample_triples(f, 1500, rng) for f in F2])  # (R, 1500, 3, 5)

    def g1_eval(a):
        a = np.asarray(a)
        v1 = np.array([game1_scores(a, T) for T in T1])
        v2 = np.array([game1_scores(a, T) for T in T2])
        beat_all = np.mean([v > S1c[r].max() for r, v in enumerate(v2)])
        return {"alloc": fmt(a), "model1_mean": round(float(v1.mean()), 3), "model1_worst": round(float(v1.min()), 3),
                "model2_mean": round(float(v2.mean()), 3), "model2_worst": round(float(v2.min()), 3),
                "model2_beats_every_contestant": round(float(beat_all), 3),
                "average_of_models": round(float((v1.mean() + v2.mean()) / 2), 3)}

    def g2_eval(a):
        a = np.asarray(a)
        v1 = np.array([game2_expected(a[None], t)[0] for t in trip1])
        v2 = np.array([game2_expected(a[None], t)[0] for t in trip2])
        beat_all = np.mean([v > S2c[r].max() for r, v in enumerate(v2)])
        return {"alloc": fmt(a), "model1_mean": round(float(v1.mean()), 3), "model1_worst": round(float(v1.min()), 3),
                "model2_mean": round(float(v2.mean()), 3), "model2_worst": round(float(v2.min()), 3),
                "model2_beats_every_contestant": round(float(beat_all), 3),
                "average_of_models": round(float((v1.mean() + v2.mean()) / 2), 3)}

    # ---- consensus picks ----
    P_cons = 0.5 * T1.mean(axis=0) + 0.5 * T2.mean(axis=0)   # Game 1 is linear in the field
    g1_cons, _ = game1_best_response(P_cons)
    top_cons, top_sc = game1_best_response(P_cons, top=8)

    pool1 = trip1.reshape(-1, 3, 5)[rng.choice(trip1.shape[0] * trip1.shape[1], 12000, replace=False)]
    pool2 = trip2.reshape(-1, 3, 5)[rng.choice(trip2.shape[0] * trip2.shape[1], 12000, replace=False)]
    pooled = np.vstack([pool1, pool2])
    grid = all_allocations(step=5)
    coarse = game2_expected(grid, pooled)
    seeds = list(grid[np.argsort(-coarse)[:8]]) + [parse(s1["game2"]["pick"]),
                                                    parse(s2["entrant_101"]["game2"]["robust_best_response"]["alloc"])]
    finals = hill_climb(seeds, pooled)
    fresh = np.vstack([trip1.reshape(-1, 3, 5)[rng.choice(trip1.shape[0] * trip1.shape[1], 15000, replace=False)],
                       trip2.reshape(-1, 3, 5)[rng.choice(trip2.shape[0] * trip2.shape[1], 15000, replace=False)]])
    fin_v = game2_expected(finals, fresh)
    g2_cons = finals[int(np.argmax(fin_v))]

    # ---- candidates ----
    pop = json.loads((ROOT / "strategy2_simulation/contestants/population.json").read_text(encoding="utf-8"))
    best1 = max(pop, key=lambda p: p["game1_score"])
    best2 = max(pop, key=lambda p: p["game2_payout"])
    g1_c = {"consensus": g1_cons,
            "strategy1_pick": parse(s1["game1"]["pick"]),
            "strategy2_pick (101st entrant)": parse(s2["entrant_101"]["game1"]["robust_best_response"]["alloc"]),
            f"best simulated contestant ({best1['id']}, {best1['archetype']})": np.array(best1["game1"]),
            "textbook proportional": np.array([7, 13, 20, 27, 33]),
            "even split": np.full(5, 20),
            "two castles 0/0/0/50/50": np.array([0, 0, 0, 50, 50])}
    for r in ai:  # every distinct real-AI Game 1 answer
        g1_c.setdefault(f"AI answer {r['id']} ({r['model']})", np.array(r["game1"]))
    g2_c = {"consensus": g2_cons,
            "strategy1_pick": parse(s1["game2"]["pick"]),
            "strategy2_pick (101st entrant)": parse(s2["entrant_101"]["game2"]["robust_best_response"]["alloc"]),
            f"best simulated contestant ({best2['id']}, {best2['archetype']})": np.array(best2["game2"]),
            "textbook proportional": np.array([7, 13, 20, 27, 33]),
            "two castles 0/0/0/50/50": np.array([0, 0, 0, 50, 50]),
            "all in castle 5": np.array([0, 0, 0, 0, 100])}
    for r in ai:
        g2_c.setdefault(f"AI answer {r['id']} ({r['model']})", np.array(r["game2"]))

    def dedupe(cands):
        seen, out = set(), {}
        for k, v in cands.items():
            if fmt(v) not in seen:
                seen.add(fmt(v))
                out[k] = v
        return out

    flat1, flat2 = trip1.reshape(-1, 3, 5), trip2.reshape(-1, 3, 5)   # sample across ALL hypotheses / replications
    rows1 = sorted([{"name": k, **g1_eval(v)} for k, v in dedupe(g1_c).items()], key=lambda r: -r["average_of_models"])
    rows2 = sorted([{"name": k, **g2_eval(v)} for k, v in dedupe(g2_c).items()], key=lambda r: -r["average_of_models"])
    out = {
        "game1": {"consensus_pick": fmt(g1_cons), "consensus_top8": [{"alloc": fmt(a), "avg_score": round(float(s), 3)} for a, s in zip(top_cons, top_sc)],
                  "table": rows1},
        "game2": {"consensus_pick": fmt(g2_cons),
                  "consensus_finish_model1": game2_detail(g2_cons, flat1[rng.choice(len(flat1), 30000, replace=False)]),
                  "consensus_finish_model2": game2_detail(g2_cons, flat2[rng.choice(len(flat2), 30000, replace=False)]),
                  "table": rows2},
    }
    (OUT / "comparison.json").write_text(json.dumps(out, indent=2))
    for g, rows in (("GAME 1", rows1), ("GAME 2", rows2)):
        print(f"\n{g}  (model1 = probability model, model2 = simulated contestants)")
        print(f"{'allocation':<16}{'avg':>7}{'m1 mean':>9}{'m1 worst':>9}{'m2 mean':>9}{'m2 worst':>9}{'beats all':>10}  name")
        for r in rows[:14]:
            print(f"{r['alloc']:<16}{r['average_of_models']:>7}{r['model1_mean']:>9}{r['model1_worst']:>9}{r['model2_mean']:>9}"
                  f"{r['model2_worst']:>9}{r['model2_beats_every_contestant']:>10}  {r['name']}")
    print("\nFINAL  Game 1:", fmt(g1_cons), "  Game 2:", fmt(g2_cons))


if __name__ == "__main__":
    main()
