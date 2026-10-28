"""Put the two strategies against each other and pick a final submission.

Model 1 (Strategy 1) treats the field as a probability distribution (level-k /
cognitive hierarchy over a grid of hypotheses). Model 2 (Strategy 2) builds it
from 100 individual contestants (30 real AI answers + 70 modelled people),
re-drawn many times. Model 3 is the same simulation rerun independently with
500 contestants (150 fresh AI answers + 350 modelled people), if present.
This script:
  1. scores every interesting allocation in every model,
  2. searches for a consensus allocation that maximises the average of models 1
     and 2 (the original final answer) and, separately, of all three models,
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
    m3_dir = ROOT / "model3_simulation_500"
    has3 = (m3_dir / "results/model_fields.npz").exists()
    if has3:
        s3 = json.loads((m3_dir / "results/simulation_results.json").read_text())
        m3 = np.load(m3_dir / "results/model_fields.npz")
        ai3 = json.loads((m3_dir / "contestants/ai_contestants.json").read_text(encoding="utf-8"))
        e3 = next(v for k, v in s3.items() if k.startswith("entrant_"))

    # ---- model 1 (probability) ----
    T1 = m1["g1_tables"]                                   # (H1, 5, 101)
    trip1 = m1["g2_triples"]                               # (H2, K, 3, 5)
    # ---- model 2 (simulation) ----
    F1, F2 = m2["g1_fields"], m2["g2_fields"]              # (R, 100, 5)
    S1c, S2c = m2["g1_scores"], m2["g2_payouts"]           # contestants' scores per replication
    T2 = np.array([game1_tables(f) for f in F1])           # (R, 5, 101)
    trip2 = np.array([sample_triples(f, 1500, rng) for f in F2])  # (R, 1500, 3, 5)
    # ---- model 3 (500-contestant simulation) ----
    if has3:
        S1c3, S2c3 = m3["g1_scores"], m3["g2_payouts"]
        T3 = np.array([game1_tables(f) for f in m3["g1_fields"]])
        rng3 = np.random.default_rng(1003)   # separate stream: adding model 3 leaves models 1-2 results unchanged
        trip3 = np.array([sample_triples(f, 1500, rng3) for f in m3["g2_fields"]])

    def add_m3(row, v3, contestants):
        if has3:
            beat = np.mean([v > contestants[r].max() for r, v in enumerate(v3)])
            row.update({"model3_mean": round(float(v3.mean()), 3), "model3_worst": round(float(v3.min()), 3),
                        "model3_beats_every_contestant": round(float(beat), 3),
                        "average_of_3_models": round(float((row["model1_mean"] + row["model2_mean"] + v3.mean()) / 3), 3)})
        return row

    def g1_eval(a):
        a = np.asarray(a)
        v1 = np.array([game1_scores(a, T) for T in T1])
        v2 = np.array([game1_scores(a, T) for T in T2])
        beat_all = np.mean([v > S1c[r].max() for r, v in enumerate(v2)])
        row = {"alloc": fmt(a), "model1_mean": round(float(v1.mean()), 3), "model1_worst": round(float(v1.min()), 3),
               "model2_mean": round(float(v2.mean()), 3), "model2_worst": round(float(v2.min()), 3),
               "model2_beats_every_contestant": round(float(beat_all), 3),
               "average_of_models": round(float((v1.mean() + v2.mean()) / 2), 3)}
        return add_m3(row, np.array([game1_scores(a, T) for T in T3]) if has3 else None, S1c3 if has3 else None)

    def g2_eval(a):
        a = np.asarray(a)
        v1 = np.array([game2_expected(a[None], t)[0] for t in trip1])
        v2 = np.array([game2_expected(a[None], t)[0] for t in trip2])
        beat_all = np.mean([v > S2c[r].max() for r, v in enumerate(v2)])
        row = {"alloc": fmt(a), "model1_mean": round(float(v1.mean()), 3), "model1_worst": round(float(v1.min()), 3),
               "model2_mean": round(float(v2.mean()), 3), "model2_worst": round(float(v2.min()), 3),
               "model2_beats_every_contestant": round(float(beat_all), 3),
               "average_of_models": round(float((v1.mean() + v2.mean()) / 2), 3)}
        return add_m3(row, np.array([game2_expected(a[None], t)[0] for t in trip3]) if has3 else None, S2c3 if has3 else None)

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

    if has3:   # same procedure, all three models weighted equally
        P3 = (T1.mean(axis=0) + T2.mean(axis=0) + T3.mean(axis=0)) / 3
        g1_cons3, _ = game1_best_response(P3)
        pool3 = trip3.reshape(-1, 3, 5)[rng3.choice(trip3.shape[0] * trip3.shape[1], 12000, replace=False)]
        pooled3 = np.vstack([pool1, pool2, pool3])
        coarse3 = game2_expected(grid, pooled3)
        seeds3 = list(grid[np.argsort(-coarse3)[:8]]) + [g2_cons, parse(e3["game2"]["robust_best_response"]["alloc"])]
        finals3 = hill_climb(seeds3, pooled3)
        fresh3 = np.vstack([fresh, trip3.reshape(-1, 3, 5)[rng3.choice(trip3.shape[0] * trip3.shape[1], 15000, replace=False)]])
        g2_cons3 = finals3[int(np.argmax(game2_expected(finals3, fresh3)))]

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
    if has3:
        g1_c["model3_pick (501st entrant)"] = parse(e3["game1"]["robust_best_response"]["alloc"])
        g1_c["3-model consensus"] = g1_cons3
    for r in ai:  # every distinct real-AI Game 1 answer
        g1_c.setdefault(f"AI answer {r['id']} ({r['model']})", np.array(r["game1"]))
    g2_c = {"consensus": g2_cons,
            "strategy1_pick": parse(s1["game2"]["pick"]),
            "strategy2_pick (101st entrant)": parse(s2["entrant_101"]["game2"]["robust_best_response"]["alloc"]),
            f"best simulated contestant ({best2['id']}, {best2['archetype']})": np.array(best2["game2"]),
            "textbook proportional": np.array([7, 13, 20, 27, 33]),
            "two castles 0/0/0/50/50": np.array([0, 0, 0, 50, 50]),
            "all in castle 5": np.array([0, 0, 0, 0, 100])}
    if has3:
        g2_c["model3_pick (501st entrant)"] = parse(e3["game2"]["robust_best_response"]["alloc"])
        g2_c["3-model consensus"] = g2_cons3
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
    if has3:
        flat3 = trip3.reshape(-1, 3, 5)
        out["game1"]["consensus_3_models"] = fmt(g1_cons3)
        out["game2"]["consensus_3_models"] = fmt(g2_cons3)
        out["game2"]["consensus_finish_model3"] = game2_detail(g2_cons, flat3[rng3.choice(len(flat3), 30000, replace=False)])
        out["game1"]["best_m3_ai_answers"] = sorted([{"name": f"M3 AI {r['id']} ({r['model']})", **g1_eval(np.array(r["game1"]))}
                                                     for r in ai3], key=lambda r: -r["model3_mean"])[:5]
        out["game2"]["best_m3_ai_answers"] = sorted([{"name": f"M3 AI {r['id']} ({r['model']})", **g2_eval(np.array(r["game2"]))}
                                                     for r in ai3], key=lambda r: -r["model3_mean"])[:5]
    (OUT / "comparison.json").write_text(json.dumps(out, indent=2))
    for g, rows in (("GAME 1", rows1), ("GAME 2", rows2)):
        print(f"\n{g}  (m1 = probability model, m2 = 100-contestant sim, m3 = 500-contestant sim)")
        print(f"{'allocation':<16}{'avg12':>7}{'m1':>7}{'m2':>7}{'m2 all':>8}{'m3':>7}{'m3 all':>8}  name")
        for r in rows[:16]:
            print(f"{r['alloc']:<16}{r['average_of_models']:>7}{r['model1_mean']:>7}{r['model2_mean']:>7}"
                  f"{r['model2_beats_every_contestant']:>8}{r.get('model3_mean', ''):>7}{r.get('model3_beats_every_contestant', ''):>8}  {r['name']}")
    print("\nFINAL (models 1+2)  Game 1:", fmt(g1_cons), "  Game 2:", fmt(g2_cons))
    if has3:
        print("CONSENSUS (models 1+2+3)  Game 1:", fmt(g1_cons3), "  Game 2:", fmt(g2_cons3))


if __name__ == "__main__":
    main()
