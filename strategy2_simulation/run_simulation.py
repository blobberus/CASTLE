"""Strategy 2 driver: build the contestants (100 by default), play both games, analyse, write results/.

Steps
  1. Build the baseline population (30 real AI answers + 70 modelled contestants),
     each contestant deciding independently  -> contestants/population.json
  2. Game 1 round robin (exact) and Game 2 tournament (20,000 reshuffles of 25 groups)
  3. Breakdown by category / archetype / AI model / AI prompt framing
  4. Trend analysis: which allocation features go with high scores
  5. Replications: independent re-draws of the population (AI answers bootstrapped,
     modelled contestants re-decided) to separate luck from strategy
  6. The extra (N+1th) entrant: best response to the simulated fields (one field and robust)
  7. Sensitivity: two sweeps - AI users vs humans (metastrategists fixed at 15), and
     the number of metastrategists (0-50% of seats) - with the extra-entrant picks tested in each
  8. Save every replication's field to results/model_fields.npz so ../compare_strategies.py
     can test any allocation (including Strategy 1's picks) in this model

Run:  python run_simulation.py           (full, about 4 minutes)
      python run_simulation.py --players 500 --ai-file ../model3_simulation_500/contestants/ai_contestants.json \n             --out ../model3_simulation_500      (model 3: same model, 500 players)
      python run_simulation.py --quick   (fewer replications, for iterating)
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from castle import (all_allocations, fmt, game1_best_response, game1_round_robin,  # noqa: E402
                    game1_scores, game1_tables, game2_best_response, game2_detail, game2_expected,
                    game2_tournament, neighbours, sample_triples)
from population import (BASE_MIX, CATEGORY, DESCRIPTION, build_meta_library, build_population,  # noqa: E402
                        load_ai, scaled_mix)

RESULTS = HERE / "results"          # re-pointed by --out in main()
CONTESTANTS = HERE / "contestants"
T0 = time.time()
GRID5 = all_allocations(step=5)


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def play(people, rng, shuffles):
    g1 = np.array([p["game1"] for p in people])
    g2 = np.array([p["game2"] for p in people])
    s1, _ = game1_round_robin(g1)
    s2, place, pts = game2_tournament(g2, shuffles, rng)
    return s1, s2, place, pts


def ranks(x):
    """1 = best. Ties get the same (best) rank."""
    order = (-np.asarray(x)).argsort(kind="stable")
    r = np.empty(len(x), dtype=int)
    r[order] = np.arange(1, len(x) + 1)
    return r


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


def features(a):
    a = np.asarray(a)
    return {
        "castle1": a[0], "castle2": a[1], "castle3": a[2], "castle4": a[3], "castle5": a[4],
        "castles_with_10plus": int((a >= 10).sum()),
        "soldiers_on_4_and_5": int(a[3] + a[4]),
        "concentration_hhi": float(((a / 100) ** 2).sum()),
        "round_number_piles": int(((a % 5 == 0) & (a > 0)).sum()),
        "largest_pile": int(a.max()),
        "skips_castle5": int(a[4] <= 5),
    }


def group_summary(people, s1, s2, place, key):
    out = {}
    r1, r2 = ranks(s1), ranks(s2)
    for g in sorted({p.get(key) for p in people if p.get(key) is not None}):
        idx = [i for i, p in enumerate(people) if p.get(key) == g]
        out[g] = {"n": len(idx),
                  "game1_mean": round(float(s1[idx].mean()), 3), "game1_best": round(float(s1[idx].max()), 3),
                  "game1_mean_rank": round(float(r1[idx].mean()), 1),
                  "game2_mean": round(float(s2[idx].mean()), 3), "game2_best": round(float(s2[idx].max()), 3),
                  "game2_mean_rank": round(float(r2[idx].mean()), 1),
                  "game2_p_first": round(float(place[idx, 0].mean()), 3)}
    return out


def entrant_game1(alloc, field):
    """Score and rank of an extra (N+1th) entrant in a Game 1 round robin."""
    pop = np.vstack([field, np.asarray(alloc)[None]])
    s, _ = game1_round_robin(pop)
    return float(s[-1]), int(ranks(s)[-1])


def entrant_game2(alloc, field, contestant_payouts, rng, K=3000):
    v = float(game2_expected(np.asarray(alloc)[None], sample_triples(field, K, rng))[0])
    return v, int(1 + (contestant_payouts > v).sum())


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


def mix_with_shares(ai_frac=50 / 85, meta_seats=15, n=100):
    """Re-weight BASE_MIX for n seats: `meta_seats` metastrategists, `ai_frac` of the rest AI-assisted.

    Seats inside each group keep BASE_MIX proportions (largest-remainder rounding).
    """
    groups = {g: [k for k in BASE_MIX if CATEGORY[k] == g] for g in ("AI-assisted", "Metastrategist", "Human")}
    rest = n - meta_seats
    totals = {"Metastrategist": meta_seats, "AI-assisted": int(round(ai_frac * rest))}
    totals["Human"] = rest - totals["AI-assisted"]
    mix = {}
    for g, keys in groups.items():
        base = sum(BASE_MIX[k] for k in keys)
        raw = {k: BASE_MIX[k] / base * totals[g] for k in keys}
        part = {k: int(np.floor(v)) for k, v in raw.items()}
        for k in sorted(raw, key=lambda k: -(raw[k] - part[k]))[: totals[g] - sum(part.values())]:
            part[k] += 1
        mix |= part
    return mix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--players", type=int, default=100)
    ap.add_argument("--ai-file", default=None, help="real AI answers (default contestants/ai_contestants.json)")
    ap.add_argument("--out", default=None, help="folder for contestants/ and results/ (default: this folder)")
    args = ap.parse_args()
    global RESULTS, CONTESTANTS
    if args.out:
        RESULTS, CONTESTANTS = Path(args.out) / "results", Path(args.out) / "contestants"
    RESULTS.mkdir(parents=True, exist_ok=True)
    CONTESTANTS.mkdir(parents=True, exist_ok=True)
    N = args.players
    mix = scaled_mix(N)
    nxt = f"{N + 1}"
    rng = np.random.default_rng(args.seed)
    Q = args.quick
    n_rep = 40 if Q else 200
    n_sens = 15 if Q else 60
    shuffles = 4000 if Q else 20000
    ai = load_ai(args.ai_file)

    # 1. baseline population -------------------------------------------------
    log("Building baseline population (each contestant decides independently)")
    people = build_population(args.seed, mix=mix, ai=ai, ai_mode="fixed")
    (CONTESTANTS / "population.json").write_text(json.dumps(people, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2-3. tournaments and breakdowns----------------------------------------------------
    log(f"Playing Game 1 round robin and Game 2 ({shuffles} reshuffles)")
    s1, s2, place, pts = play(people, rng, shuffles)
    r1, r2 = ranks(s1), ranks(s2)
    combined = ranks(-(r1 + r2))  # lower rank-sum is better
    for i, p in enumerate(people):
        p.update({"game1_score": round(float(s1[i]), 3), "game1_rank": int(r1[i]),
                  "game2_payout": round(float(s2[i]), 3), "game2_rank": int(r2[i]),
                  "game2_p_first": round(float(place[i, 0]), 3), "game2_p_second": round(float(place[i, 1]), 3),
                  "game2_mean_castle_points": round(float(pts[i]), 3), "combined_rank": int(combined[i])})
    cols = ["game1_rank", "game2_rank", "combined_rank", "id", "archetype", "category", "model", "framing",
            "game1", "game1_score", "game2", "game2_payout", "game2_p_first", "game2_p_second", "reasoning"]
    with open(RESULTS / "leaderboard.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in sorted(people, key=lambda p: p["combined_rank"]):
            w.writerow([fmt(p[c]) if c in ("game1", "game2") else p.get(c, "") for c in cols])

    def top(key, n=10, rev=True):
        return [{k: (fmt(p[k]) if k in ("game1", "game2") else p.get(k)) for k in
                 ("id", "archetype", "model", "framing", "game1", "game1_score", "game2", "game2_payout",
                  "game2_p_first", "reasoning")} for p in sorted(people, key=lambda p: -p[key] if rev else p[key])[:n]]

    out = {"seed": args.seed, "quick": Q, "players": N, "mix": mix, "descriptions": DESCRIPTION,
           "baseline": {"game1_top10": top("game1_score"), "game2_top10": top("game2_payout"),
                        "game1_bottom5": top("game1_score", 5, rev=False), "game2_bottom5": top("game2_payout", 5, rev=False),
                        "by_category": group_summary(people, s1, s2, place, "category"),
                        "by_archetype": group_summary(people, s1, s2, place, "archetype"),
                        "ai_by_model": group_summary(people, s1, s2, place, "model"),
                        "ai_by_framing": group_summary(people, s1, s2, place, "framing")}}

    # 4. trends -----------------------------------------------------------------
    log("Trend analysis")
    trends = {}
    for game, scores in (("game1", s1), ("game2", s2)):
        F = [features(p[game]) for p in people]
        trends[game] = {f: round(spearman([x[f] for x in F], scores), 3) for f in F[0]}
    out["baseline"]["trend_spearman"] = trends
    g1_allocs = [fmt(p["game1"]) for p in people]
    g2_allocs = [fmt(p["game2"]) for p in people]
    out["baseline"]["most_common_game1"] = sorted({a: g1_allocs.count(a) for a in g1_allocs}.items(), key=lambda x: -x[1])[:8]
    out["baseline"]["most_common_game2"] = sorted({a: g2_allocs.count(a) for a in g2_allocs}.items(), key=lambda x: -x[1])[:8]
    out["baseline"]["field_mean_game1"] = np.round(np.mean([p["game1"] for p in people], axis=0), 2).tolist()
    out["baseline"]["field_mean_game2"] = np.round(np.mean([p["game2"] for p in people], axis=0), 2).tolist()

    # 5. replications -----------------------------------------------------------
    log("Precomputing metastrategist library for replications")
    per_type = 6 if Q else max(12, 3 * max(mix[k] for k in ("meta_level2", "meta_simulator", "meta_ai_sampler")))
    lib = build_meta_library(args.seed + 1, per_type=per_type, ai=ai)
    log(f"Running {n_rep} independent replications")
    arch_stats = {a: {"g1": [], "g2": [], "g1_rank": [], "g2_rank": [], "g1_top": 0, "g2_top": 0, "n": 0} for a in BASE_MIX}
    ai_answer_stats = {r["id"]: {"g1": [], "g2": []} for r in ai}
    winners = {"game1": [], "game2": []}
    rep_fields = []
    for rep in range(n_rep):
        pop = build_population(10_000 + rep, mix=mix, ai=ai, ai_mode="bootstrap", meta_library=lib)
        a1, a2, pl, _ = play(pop, rng, 2000)
        q1, q2 = ranks(a1), ranks(a2)
        rep_fields.append((np.array([p["game1"] for p in pop]), np.array([p["game2"] for p in pop]), a1, a2))
        winners["game1"].append((pop[int(np.argmax(a1))]["archetype"], fmt(pop[int(np.argmax(a1))]["game1"])))
        winners["game2"].append((pop[int(np.argmax(a2))]["archetype"], fmt(pop[int(np.argmax(a2))]["game2"])))
        for i, p in enumerate(pop):
            st = arch_stats[p["archetype"]]
            st["g1"].append(a1[i]); st["g2"].append(a2[i]); st["g1_rank"].append(q1[i]); st["g2_rank"].append(q2[i])
            st["g1_top"] += int(q1[i] <= 10); st["g2_top"] += int(q2[i] <= 10); st["n"] += 1
            if p.get("source_ai_id"):
                ai_answer_stats[p["source_ai_id"]]["g1"].append(a1[i])
                ai_answer_stats[p["source_ai_id"]]["g2"].append(a2[i])
    out["replications"] = {
        "n": n_rep,
        "by_archetype": {a: {"game1_mean": round(float(np.mean(s["g1"])), 3), "game1_mean_rank": round(float(np.mean(s["g1_rank"])), 1),
                             "game1_top10_rate": round(s["g1_top"] / max(s["n"], 1), 3),
                             "game2_mean": round(float(np.mean(s["g2"])), 3), "game2_mean_rank": round(float(np.mean(s["g2_rank"])), 1),
                             "game2_top10_rate": round(s["g2_top"] / max(s["n"], 1), 3)} for a, s in arch_stats.items() if s["n"]},
        "ai_answers": sorted([{"id": k, "game1": fmt(next(r["game1"] for r in ai if r["id"] == k)),
                               "game2": fmt(next(r["game2"] for r in ai if r["id"] == k)),
                               "game1_mean": round(float(np.mean(v["g1"])), 3), "game2_mean": round(float(np.mean(v["g2"])), 3),
                               "appearances": len(v["g1"])} for k, v in ai_answer_stats.items() if v["g1"]],
                             key=lambda r: -(r["game1_mean"] / 15 + r["game2_mean"] / 9)),
        "winner_archetypes": {g: sorted({a: [w[0] for w in winners[g]].count(a) for a, _ in winners[g]}.items(), key=lambda x: -x[1])
                              for g in winners},
        "winner_allocations": {g: sorted({a: [w[1] for w in winners[g]].count(a) for _, a in winners[g]}.items(), key=lambda x: -x[1])[:10]
                               for g in winners},
    }

    # 6. the extra (N+1th) entrant ------------------------------------------------
    log(f"Best response to the simulated fields (entrant #{nxt})")
    base1 = np.array([p["game1"] for p in people])
    base2 = np.array([p["game2"] for p in people])
    br1_single, v1 = game1_best_response(game1_tables(base1))
    pooled_tables = np.mean([game1_tables(f1) for f1, _, _, _ in rep_fields], axis=0)
    br1_robust, _ = game1_best_response(pooled_tables)
    br2_single = game2_best_response(base2, rng, k_coarse=1500, k_fine=5000, n_seeds=10,
                                     extra_seeds=[p["game2"] for p in sorted(people, key=lambda p: -p["game2_payout"])[:5]])[0][0]
    per_rep = 120 if Q else 150
    pooled_trip = np.vstack([sample_triples(f2, per_rep, rng) for _, f2, _, _ in rep_fields])
    coarse = game2_expected(GRID5, pooled_trip)
    seeds = list(GRID5[np.argsort(-coarse)[:6]]) + [br2_single] + [p["game2"] for p in sorted(people, key=lambda p: -p["game2_payout"])[:4]]
    finals = hill_climb(seeds, pooled_trip)
    check = game2_expected(finals, np.vstack([sample_triples(f2, 400, rng) for _, f2, _, _ in rep_fields]))
    br2_robust = finals[int(np.argmax(check))]

    def evaluate1(a):
        base_score, base_rank = entrant_game1(a, base1)
        reps = [entrant_game1(a, f1) for f1, _, _, _ in rep_fields]
        return {"alloc": fmt(a), "baseline_score": round(base_score, 3), f"baseline_rank_of_{nxt}": base_rank,
                "replication_mean": round(float(np.mean([x[0] for x in reps])), 3),
                "replication_rank1_rate": round(float(np.mean([x[1] == 1 for x in reps])), 3),
                "replication_top5_rate": round(float(np.mean([x[1] <= 5 for x in reps])), 3)}

    def evaluate2(a):
        base_v, base_rank = entrant_game2(a, base2, s2, rng)
        reps = [entrant_game2(a, f2, c2, rng, K=1500) for _, f2, _, c2 in rep_fields]
        return {"alloc": fmt(a), "baseline_payout": round(base_v, 3), f"baseline_rank_of_{nxt}": base_rank,
                "baseline_finish": game2_detail(a, sample_triples(base2, 8000, rng)),
                "replication_mean": round(float(np.mean([x[0] for x in reps])), 3),
                "replication_rank1_rate": round(float(np.mean([x[1] == 1 for x in reps])), 3),
                "replication_top5_rate": round(float(np.mean([x[1] <= 5 for x in reps])), 3)}

    best_g1_contestant = max(people, key=lambda p: p["game1_score"])
    best_g2_contestant = max(people, key=lambda p: p["game2_payout"])
    out[f"entrant_{nxt}"] = {
        "game1": {"best_response_to_baseline": evaluate1(br1_single), "robust_best_response": evaluate1(br1_robust),
                  "baseline_winner_" + best_g1_contestant["id"]: evaluate1(best_g1_contestant["game1"])},
        "game2": {"best_response_to_baseline": evaluate2(br2_single), "robust_best_response": evaluate2(br2_robust),
                  "baseline_winner_" + best_g2_contestant["id"]: evaluate2(best_g2_contestant["game2"])},
    }

    # 7. sensitivity: who wins when the population mix changes? -------------------
    sens, sens_fields = {}, {}
    sweeps = [("ai_vs_human", {"ai_frac": f, "meta_seats": round(15 * N / 100)}) for f in (0.2, 0.4, 50 / 85, 0.8, 1.0)] +              [("meta_share", {"meta_seats": round(m * N / 100)}) for m in (0, 5, 15, 30, 50)]
    for sweep, kw in sweeps:
        smix = mix_with_shares(n=N, **kw)
        label = f"{sweep}:" + (f"ai={sum(v for k, v in smix.items() if CATEGORY[k] == 'AI-assisted')}"
                               f",meta={sum(v for k, v in smix.items() if CATEGORY[k] == 'Metastrategist')}"
                               f",human={sum(v for k, v in smix.items() if CATEGORY[k] == 'Human')}")
        log(f"Sensitivity {label}")
        acc = {a: {"g1": [], "g2": []} for a in smix if smix[a]}
        e1, e2, w1, w2, f1s, f2s = [], [], [], [], [], []
        for rep in range(n_sens):
            pop = build_population(50_000 + len(sens) * 1000 + rep, mix=smix, ai=ai, ai_mode="bootstrap", meta_library=lib)
            a1, a2, _, _ = play(pop, rng, 1500)
            f1, f2 = np.array([q["game1"] for q in pop]), np.array([q["game2"] for q in pop])
            f1s.append(f1); f2s.append(f2)
            for i, q in enumerate(pop):
                acc[q["archetype"]]["g1"].append(a1[i]); acc[q["archetype"]]["g2"].append(a2[i])
            v1 = float(game1_scores(br1_robust, game1_tables(f1)))
            v2 = float(game2_expected(np.asarray(br2_robust)[None], sample_triples(f2, 1500, rng))[0])
            e1.append(v1); e2.append(v2); w1.append(v1 > a1.max()); w2.append(v2 > a2.max())
        best1 = sorted(((a, np.mean(v["g1"])) for a, v in acc.items()), key=lambda x: -x[1])
        best2 = sorted(((a, np.mean(v["g2"])) for a, v in acc.items()), key=lambda x: -x[1])
        sens[label] = {"mix": smix,
                       "game1_top3": [(a, round(float(v), 3)) for a, v in best1[:3]],
                       "game2_top3": [(a, round(float(v), 3)) for a, v in best2[:3]],
                       "game1_all": {a: round(float(v), 3) for a, v in best1},
                       "game2_all": {a: round(float(v), 3) for a, v in best2},
                       "robust_pick_game1": {"alloc": fmt(br1_robust), "mean": round(float(np.mean(e1)), 3), "beats_everyone_rate": round(float(np.mean(w1)), 3)},
                       "robust_pick_game2": {"alloc": fmt(br2_robust), "mean": round(float(np.mean(e2)), 3), "beats_everyone_rate": round(float(np.mean(w2)), 3)}}
        sens_fields[label] = (np.array(f1s), np.array(f2s))
    out["sensitivity"] = sens
    np.savez_compressed(RESULTS / ("model_fields_quick.npz" if Q else "model_fields.npz"),
                        g1_fields=np.array([f[0] for f in rep_fields]), g2_fields=np.array([f[1] for f in rep_fields]),
                        g1_scores=np.array([f[2] for f in rep_fields]), g2_payouts=np.array([f[3] for f in rep_fields]),
                        baseline_g1=base1, baseline_g2=base2, baseline_g1_scores=s1, baseline_g2_payouts=s2,
                        sens_labels=np.array(list(sens_fields)),
                        **{f"sens{i}_g1": v[0] for i, v in enumerate(sens_fields.values())},
                        **{f"sens{i}_g2": v[1] for i, v in enumerate(sens_fields.values())})
    out["runtime_s"] = round(time.time() - T0, 1)
    name = "simulation_results_quick.json" if Q else "simulation_results.json"
    (RESULTS / name).write_text(json.dumps(out, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    with open(CONTESTANTS / "population.json", "w", encoding="utf-8") as fh:
        json.dump(people, fh, indent=2, ensure_ascii=False)
    log(f"wrote {RESULTS / name}")
    print("\nGAME 1 robust entrant #" + nxt + ":", fmt(br1_robust), "| GAME 2 robust entrant #" + nxt + ":", fmt(br2_robust))


if __name__ == "__main__":
    main()
