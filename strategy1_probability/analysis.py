"""Strategy 1: solve the Castle Challenge with probability rules and level-k reasoning.

No simulated contestants are used here. The field is modelled as a probability
distribution built from first principles, and every number is an expected value
under that distribution.

Pipeline (all output goes to results/):
  1. Game 1 theory   - closed-form equilibrium check + discrete equilibrium by fictitious play.
  2. Game 1 ladder   - round 0 (naive field) -> round k = best response to rounds < k.
  3. Game 1 pick     - Bayes-optimal allocation averaged over a grid of field hypotheses.
  4. Game 2 rules    - cost of winning a castle against the strongest of 3 opponents.
  5. Game 2 theory   - approximate equilibrium by multiplicative-weights self-play.
  6. Game 2 ladder + pick (Monte Carlo + hill climbing).
  7. Save the modelled fields to results/model_fields.npz so ../compare_strategies.py
     can test any allocation (including Strategy 2's picks) in this model.

Players who reason k rounds deep are modelled with a *quantal* (noisy) best
response: they choose allocations with probability proportional to
exp(expected score / temperature). Real people at the same depth of reasoning
land on many different near-best answers, not one identical allocation.

Run:  python analysis.py           (full run, about 12 minutes)
      python analysis.py --quick   (smaller samples for iterating, a few minutes)
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from castle import (VALUES, TOTAL, all_allocations, fmt, game1_best_response,  # noqa: E402
                    game1_equilibrium, game1_scores, game1_tables, game2_best_response,
                    game2_detail, game2_expected, jitter, neighbours, sample_triples)

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
ALL = all_allocations()
GRID5 = all_allocations(step=5)
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# --------------------------------------------------------------------------
# Field model: round 0 ("level 0") behaviour, written down before any data.
# Families are things a person (or an AI asked casually) submits without
# modelling anyone else. Weights are priors, varied in the hypothesis grid.
# --------------------------------------------------------------------------
G1_ANCHORS = [
    ((7, 13, 20, 27, 33), "proportional", 0.22),  # 100 * value / 15, rounded: the textbook answer
    ((6, 13, 20, 27, 34), "proportional", 0.04),
    ((7, 13, 20, 26, 34), "proportional", 0.04),
    ((10, 15, 20, 25, 30), "round", 0.10),        # 'increase by 5 each castle'
    ((5, 10, 20, 30, 35), "round", 0.08),
    ((5, 15, 20, 25, 35), "round", 0.04),
    ((20, 20, 20, 20, 20), "even", 0.10),
    ((0, 10, 20, 30, 40), "top_heavy", 0.10),
    ((0, 0, 20, 30, 50), "top_heavy", 0.05),
    ((0, 0, 33, 33, 34), "top_heavy", 0.06),      # 'win 3+4+5 = 12 points'
    ((0, 0, 0, 50, 50), "top_heavy", 0.04),
    (None, "random", 0.13),                       # unsure / arbitrary: uniform over all allocations
]
G1_VARIANTS = {
    "baseline": {},
    "ai_heavy": {"proportional": 2.0, "random": 0.5},
    "human_heavy": {"even": 2.0, "round": 1.5, "random": 2.0, "proportional": 0.5},
    "top_heavy": {"top_heavy": 2.5},
}
# Game 2 round 0: many people reuse their Game 1 numbers, the rest 'go big'.
G2_ANCHORS = [(a, "reuse", w * 0.45) for a, _, w in G1_ANCHORS] + [
    ((0, 0, 0, 50, 50), "concentrated", 0.10),
    ((0, 0, 33, 33, 34), "concentrated", 0.10),
    ((0, 0, 20, 30, 50), "concentrated", 0.08),
    ((0, 0, 0, 40, 60), "concentrated", 0.05),
    ((0, 0, 25, 35, 40), "concentrated", 0.05),
    ((0, 0, 0, 0, 100), "all_in", 0.04),
    ((0, 10, 20, 30, 40), "top_heavy", 0.08),
    (None, "random", 0.05),
]
G2_VARIANTS = {
    "baseline": {},
    "concentrated_heavy": {"concentrated": 2.0, "all_in": 2.0},
    "spread_heavy": {"reuse": 1.6, "concentrated": 0.6},
}
G1_TEMPS = (0.3, 0.8)   # points of Game 1 score; lower = sharper reasoning
G2_TEMPS = (0.3, 0.8)   # points of Game 2 payout


def ch_weights(tau, kmax):
    """Cognitive-hierarchy (Poisson) share of players reasoning k rounds deep, k=0..kmax."""
    f = np.array([math.exp(-tau) * tau ** k / math.factorial(k) for k in range(kmax + 1)])
    return f / f.sum()


def sample_round0(anchors, mult, n, lam, rng):
    allocs = [a for a, _, _ in anchors]
    w = np.array([w * mult.get(fam, 1.0) for _, fam, w in anchors])
    pick = rng.choice(len(anchors), size=n, p=w / w.sum())
    out = np.empty((n, 5), dtype=int)
    for r, k in enumerate(pick):
        out[r] = ALL[rng.integers(len(ALL))] if allocs[k] is None else jitter(allocs[k], rng, rng.poisson(lam))
    return out


def mixture(samples, shares):
    """Stack per-level samples and give each row weight share/len so levels hit their shares."""
    field = np.vstack(samples)
    w = np.concatenate([np.full(len(s), sh / len(s)) for s, sh in zip(samples, shares)])
    return field, w


def softmax_pick(scores, temp, n, rng):
    p = np.exp((scores - scores.max()) / temp)
    return rng.choice(len(scores), size=n, p=p / p.sum())


def quantal_g1(P, temp, n, rng):
    return ALL[softmax_pick(game1_scores(ALL, P), temp, n, rng)].astype(int)


def quantal_g2(u, temp, n, rng):
    """Noisy best response on the step-5 grid, then a little integer-level jitter."""
    return np.array([jitter(GRID5[i], rng, rng.poisson(2)) for i in softmax_pick(u, temp, n, rng)])


def diversity(sample):
    return {"unique_allocations": int(len(np.unique(sample, axis=0))), "mean_allocation": np.round(sample.mean(0), 1).tolist()}


# --------------------------------------------------------------------------
# 1. Game 1 theory
# --------------------------------------------------------------------------
def game1_theory(iters):
    log("Game 1 theory: closed-form check")
    caps = 2 * TOTAL * VALUES / VALUES.sum()            # equilibrium marginals are U[0, cap_i]
    def vs_equilibrium(a):
        a = np.asarray(a, float)
        return float((VALUES * np.minimum(1.0, a / caps)).sum())
    examples = {fmt(a): round(vs_equilibrium(a), 3) for a in
                [(7, 13, 20, 27, 33), (20, 20, 20, 20, 20), (0, 0, 0, 50, 50), (0, 0, 33, 33, 34),
                 (10, 15, 20, 25, 30), (0, 0, 0, 0, 100), (3, 14, 21, 28, 34)]}

    log(f"Game 1 theory: fictitious play, {iters} iterations")
    burn = game1_equilibrium(iters)
    _, br_val = game1_best_response(game1_tables(burn))
    log(f"   FP exploitability: best reply scores {br_val:.3f} vs the mixture (7.5 = unexploitable)")
    return {
        "closed_form": {
            "marginal_caps": np.round(caps, 2).tolist(),
            "marginal_means": np.round(caps / 2, 2).tolist(),
            "score_vs_equilibrium": examples,
        },
        "fictitious_play": {
            "iterations": iters,
            "best_reply_score_vs_mixture": round(br_val, 4),
            "mean_allocation": np.round(burn.mean(axis=0), 2).tolist(),
            "p99_allocation": np.percentile(burn, 99, axis=0).tolist(),
            "sample_support": [fmt(x) for x in burn[:: max(1, len(burn) // 12)][:12]],
        },
    }, burn


# --------------------------------------------------------------------------
# 2-3. Game 1 ladder and robust pick
# --------------------------------------------------------------------------
def game1_ladder(variant, tau, temp, n, rng, kmax=4):
    r0 = sample_round0(G1_ANCHORS, G1_VARIANTS[variant], n, 1.5, rng)
    levels, brs = [r0], []
    f = ch_weights(tau, kmax)
    for k in range(1, kmax + 1):
        belief, w = mixture(levels, f[:k] / f[:k].sum())
        P = game1_tables(belief, w)
        brs.append(game1_best_response(P)[0])
        levels.append(quantal_g1(P, temp, n // 2, rng))
    return levels, brs, f


def game1_analysis(eq_sample, n, rng):
    log("Game 1 ladder (baseline field, tau=1.5, temperature=0.3)")
    levels, brs, f = game1_ladder("baseline", 1.5, 0.3, n, rng)
    ladder = []
    for k, br in enumerate(brs, start=1):
        row = {"round": k, "best_move": fmt(br), "field_at_this_round": diversity(levels[k])}
        for j in range(k + 1):
            row[f"score_vs_round{j}"] = round(float(game1_scores(br, game1_tables(levels[j]))), 3)
        ladder.append(row)
    prop = np.array([7, 13, 20, 27, 33])
    beat_prop = game1_best_response(game1_tables(prop[None]))

    log("Game 1 robust pick over hypothesis grid")
    hyps, tables = [], []
    for variant in G1_VARIANTS:
        for tau in (0.5, 1.0, 1.5, 2.5):
            for temp in G1_TEMPS:
                lv, _, f = game1_ladder(variant, tau, temp, n, rng)
                for nash in (0.0, 0.15):
                    samples = lv + ([eq_sample[rng.integers(len(eq_sample), size=n)]] if nash else [])
                    shares = list(f * (1 - nash)) + ([nash] if nash else [])
                    tables.append(game1_tables(*mixture(samples, shares)))
                    hyps.append({"variant": variant, "tau": tau, "temperature": temp, "nash_share": nash})
    pooled = np.mean(tables, axis=0)                     # Game 1 is linear in the field
    pick, pick_val = game1_best_response(pooled)
    top, top_sc = game1_best_response(pooled, top=10)
    hyp_best = [game1_best_response(T) for T in tables]

    cands = {"robust_pick": pick, "proportional": prop, "even": np.full(5, 20),
             "round_linear": np.array([10, 15, 20, 25, 30]), "beat_proportional": beat_prop[0],
             **{f"ladder_round{k}": b for k, b in enumerate(brs, 1)},
             "top_heavy_3": np.array([0, 0, 33, 33, 34]), "two_castles": np.array([0, 0, 0, 50, 50]),
             "top_heavy_ladder": np.array([0, 10, 20, 30, 40])}
    rows = []
    for name, a in cands.items():
        sc = np.array([game1_scores(a, T) for T in tables])
        best = np.array([b[1] for b in hyp_best])
        rows.append({"name": name, "alloc": fmt(a), "mean": round(float(sc.mean()), 3),
                     "worst": round(float(sc.min()), 3), "best": round(float(sc.max()), 3),
                     "max_regret": round(float((best - sc).max()), 3)})
    rows.sort(key=lambda r: -r["mean"])
    per_hyp = [{**h, "pick_score": round(float(game1_scores(pick, T)), 3), "hyp_best": fmt(b[0]),
                "hyp_best_score": round(float(b[1]), 3)} for h, T, b in zip(hyps, tables, hyp_best)]
    log(f"   Game 1 pick {fmt(pick)} expected {pick_val:.3f}")
    return {
        "ladder_baseline": ladder,
        "beat_the_textbook_answer": {"textbook": fmt(prop), "counter": fmt(beat_prop[0]),
                                     "counter_score_vs_textbook": round(beat_prop[1], 3)},
        "n_hypotheses": len(hyps),
        "pick": fmt(pick), "pick_expected": round(pick_val, 3),
        "pick_win_prob_per_castle_pooled": [round(float(pooled[i, pick[i]] / VALUES[i]), 3) for i in range(5)],
        "top10_pooled": [{"alloc": fmt(a), "score": round(float(s), 3)} for a, s in zip(top, top_sc)],
        "comparison": rows,
        "per_hypothesis": per_hyp,
    }, np.array(tables)


# --------------------------------------------------------------------------
# 4. Game 2 probability rules
# --------------------------------------------------------------------------
def game2_rules(n, rng):
    log("Game 2 rules: cost of winning each castle vs 1 and vs 3 opponents")
    field = sample_round0(G2_ANCHORS, {}, n, 1.5, rng)
    out = []
    for i in range(5):
        x = field[:, i]
        row = {"castle": i + 1, "points": int(VALUES[i])}
        for p in (0.5, 0.8, 0.95):
            # strictly beat one opponent with prob p  <=>  F(s-1) >= p
            # strictly beat all three with prob p     <=>  F(s-1)^3 >= p
            for opp, need in ((1, p), (3, p ** (1 / 3))):
                row[f"soldiers_for_{int(p * 100)}pct_vs_{opp}"] = int(np.quantile(x, need, method="inverted_cdf") + 1)
        out.append(row)
    return out


# --------------------------------------------------------------------------
# 5. Game 2 approximate equilibrium (multiplicative weights on the step-5 grid)
# --------------------------------------------------------------------------
def game2_equilibrium(gens, k, rng, eta=0.3):
    log(f"Game 2 equilibrium: {gens} generations of multiplicative weights on the step-5 grid")
    G = GRID5
    w = np.full(len(G), 1.0 / len(G))
    avg = np.zeros(len(G))
    for t in range(gens):
        u = game2_expected(G, sample_triples(G, k, rng, w))
        w = w * np.exp(eta * (u - u @ w))
        w /= w.sum()
        if t >= gens // 4:
            avg += w
        if t % 25 == 0:
            log(f"   gen {t}: top strategy {fmt(G[np.argmax(w)])} weight {w.max():.3f}")
    avg /= avg.sum()
    order = np.argsort(-avg)
    br, br_val = game2_best_response(G, rng, weights=avg, k_coarse=1500, k_fine=4000, n_seeds=8)
    contested = (G >= 10).sum(axis=1)
    return {
        "generations": gens,
        "top_strategies": [{"alloc": fmt(G[i]), "weight": round(float(avg[i]), 4)} for i in order[:15]],
        "mean_allocation": np.round(avg @ G, 2).tolist(),
        "effective_support": round(float(1 / np.sum(avg ** 2)), 1),
        "share_by_castles_contested": {int(c): round(float(avg[contested == c].sum()), 3) for c in range(1, 6)},
        "best_reply": fmt(br[0]), "best_reply_payout": round(float(br_val[0]), 3),
    }, avg


# --------------------------------------------------------------------------
# 6. Game 2 ladder and robust pick
# --------------------------------------------------------------------------
def game2_analysis(eq_w, n, rng, quick):
    bk = dict(k_coarse=600, k_fine=1500, n_seeds=4) if quick else dict(k_coarse=1000, k_fine=3000, n_seeds=6)
    K = 800 if quick else 1500
    taus, kmax = (0.5, 1.5, 2.5), 3
    ladders = {}
    baseline_beliefs = None
    for variant in G2_VARIANTS:
        log(f"Game 2 ladders [{variant}]")
        r0 = sample_round0(G2_ANCHORS, G2_VARIANTS[variant], n, 2.0, rng)
        u1 = game2_expected(GRID5, sample_triples(r0, K, rng))
        for temp in G2_TEMPS:
            l1 = quantal_g2(u1, temp, n // 2, rng)
            for tau in taus:
                f = ch_weights(tau, kmax)
                levels, beliefs = [r0, l1], [(r0, None)]
                for k in range(2, kmax + 1):
                    belief = mixture(levels, f[:k] / f[:k].sum())
                    beliefs.append(belief)
                    u = game2_expected(GRID5, sample_triples(belief[0], K, rng, belief[1]))
                    levels.append(quantal_g2(u, temp, n // 2, rng))
                ladders[(variant, tau, temp)] = (levels, f)
                if (variant, tau, temp) == ("baseline", 1.5, 0.3):
                    baseline_beliefs = beliefs

    log("Game 2 ladder table (exact best response each round, baseline field)")
    levels, f = ladders[("baseline", 1.5, 0.3)]
    ladder_rows, ladder_brs = [], []
    for k, (bf, bw) in enumerate(baseline_beliefs, start=1):
        br = game2_best_response(bf, rng, weights=bw, **bk)[0][0]
        ladder_brs.append(br)
        row = {"round": k, "best_move": fmt(br), "field_at_this_round": diversity(levels[k])}
        for j in range(k + 1):
            row[f"payout_vs_round{j}"] = round(float(game2_expected(br[None], sample_triples(levels[j], 6000, rng))[0]), 3)
        ladder_rows.append(row)

    log("Game 2 robust pick: pooled hypotheses + hill climbing")
    hyps, fields = [], []
    for (variant, tau, temp), (levels, f) in ladders.items():
        for nash in (0.0, 0.15):
            samples = levels + ([GRID5[rng.choice(len(GRID5), size=n, p=eq_w)]] if nash else [])
            shares = list(f * (1 - nash)) + ([nash] if nash else [])
            fields.append(mixture(samples, shares))
            hyps.append({"variant": variant, "tau": tau, "temperature": temp, "nash_share": nash})
    per_h = 200 if quick else 300
    pooled = np.vstack([sample_triples(F, per_h, rng, w) for F, w in fields])
    coarse = game2_expected(GRID5, pooled)
    seeds = list(GRID5[np.argsort(-coarse)[:5 if quick else 8]]) + ladder_brs
    finals = []
    for s in np.unique(np.array(seeds), axis=0):
        cur = np.asarray(s, dtype=np.int16)
        cur_v = game2_expected(cur[None], pooled)[0]
        for _ in range(60):
            nb = neighbours(cur)
            v = game2_expected(nb, pooled)
            j = int(np.argmax(v))
            if v[j] <= cur_v + 1e-9:
                break
            cur, cur_v = nb[j], v[j]
        finals.append(cur)
    finals = np.unique(np.array(finals), axis=0)

    # fresh evaluation per hypothesis, independent of the triples used in the search
    K_eval = 1500 if quick else 4000
    evals = [sample_triples(F, K_eval, rng, w) for F, w in fields]
    named = {fmt(a): a for a in finals}
    for k, br in enumerate(ladder_brs, 1):
        named[f"ladder_round{k}"] = br
    for nm, a in {"two_castles_50_50": (0, 0, 0, 50, 50), "three_castles_33": (0, 0, 33, 33, 34),
                  "proportional": (7, 13, 20, 27, 33), "top_heavy_0_10_20_30_40": (0, 10, 20, 30, 40),
                  "all_in_castle5": (0, 0, 0, 0, 100), "castles_3_and_5": (0, 0, 37, 0, 63),
                  "castles_3_and_4": (0, 0, 40, 60, 0), "castles_1_to_3": (20, 28, 52, 0, 0)}.items():
        named[nm] = np.array(a)
    keys = list(named)
    C = np.array([named[k] for k in keys])
    M = np.array([game2_expected(C, E) for E in evals])                        # (H, C)
    mean = M.mean(axis=0)
    order = np.argsort(-mean)
    best_per_h = M.max(axis=1)
    rows = [{"name": keys[i], "alloc": fmt(named[keys[i]]), "mean_payout": round(float(mean[i]), 3),
             "worst": round(float(M[:, i].min()), 3), "best": round(float(M[:, i].max()), 3),
             "max_regret": round(float((best_per_h - M[:, i]).max()), 3)} for i in order]
    pick = named[keys[order[0]]]
    all_eval = np.vstack(evals)
    per_hyp = [{**h, "pick_payout": round(float(M[j, order[0]]), 3),
                "hyp_best_in_pool": fmt(named[keys[int(np.argmax(M[j]))]]),
                "hyp_best_payout": round(float(M[j].max()), 3)} for j, h in enumerate(hyps)]
    log(f"   Game 2 pick {fmt(pick)} mean payout {mean[order[0]]:.3f}")
    return {
        "ladder_baseline": ladder_rows,
        "n_hypotheses": len(hyps),
        "pick": fmt(pick), "pick_mean_payout": round(float(mean[order[0]]), 3),
        "pick_finish_profile": game2_detail(pick, all_eval),
        "comparison": rows[:30],
        "per_hypothesis": per_hyp,
    }, np.array(evals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    n = 1500 if args.quick else 3000

    out = {"seed": args.seed, "quick": args.quick}
    out["game1_theory"], eq1 = game1_theory(1500 if args.quick else 6000)
    out["game1"], g1_tables = game1_analysis(eq1, n, rng)
    out["game2_rules"] = game2_rules(20000, rng)
    out["game2_theory"], eq_w = game2_equilibrium(60 if args.quick else 240, 400 if args.quick else 600, rng)
    out["game2"], g2_triples = game2_analysis(eq_w, n, rng, args.quick)
    np.savez_compressed(RESULTS / ("model_fields_quick.npz" if args.quick else "model_fields.npz"),
                        g1_tables=g1_tables, g2_triples=g2_triples.astype(np.int16))
    out["runtime_s"] = round(time.time() - T0, 1)
    name = "strategy1_results_quick.json" if args.quick else "strategy1_results.json"
    (RESULTS / name).write_text(json.dumps(out, indent=2))
    log(f"wrote {RESULTS / name}")
    print(f"\nGAME 1 PICK: {out['game1']['pick']}   GAME 2 PICK: {out['game2']['pick']}")


if __name__ == "__main__":
    main()
