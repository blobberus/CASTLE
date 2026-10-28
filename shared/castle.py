"""Castle Challenge engine shared by both strategy folders.

Rules (from Trial.txt):
  * 100 soldiers, 5 castles worth 1..5 points, whole numbers summing to 100.
  * Game 1 (head to head): each pair of applicants fights castle by castle;
    more soldiers wins the castle's points, a tie splits them. Score = average
    points over all matchups.
  * Game 2 (four-way): random groups of 4. Each castle goes to the player(s)
    with the most soldiers (ties split). Players are ranked by castle points
    and paid 9 / 4 / 2 / 0 by finish; tied players split the payouts of the
    places they occupy. Groups are reshuffled thousands of times.

Allocations are integer arrays of shape (..., 5), castle 1 first.
Game 2 castle points are kept as integers scaled by 12 so that 2-, 3- and
4-way splits stay exact (12 is divisible by 1, 2, 3 and 4).
"""
from functools import lru_cache

import numpy as np

VALUES = np.array([1, 2, 3, 4, 5])
TOTAL = 100
N_CASTLES = 5
PAYOUTS = np.array([9.0, 4.0, 2.0, 0.0])
SCALE = 12  # Game 2 point scale (see module docstring)
VALUES12 = VALUES * SCALE


# --------------------------------------------------------------------------
# Allocation space
# --------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _compositions(n, k):
    if k == 1:
        return np.array([[n]], dtype=np.int16)
    blocks = []
    for first in range(n + 1):
        sub = _compositions(n - first, k - 1)
        blocks.append(np.column_stack([np.full(len(sub), first, dtype=np.int16), sub]))
    return np.vstack(blocks)


def all_allocations(step=1, total=TOTAL):
    """Every allocation whose entries are multiples of `step` (step=1: 4,598,126 rows)."""
    return (_compositions(total // step, N_CASTLES) * step).astype(np.int16)


def validate(alloc):
    a = np.asarray(alloc)
    return a.shape[-1] == N_CASTLES and (a >= 0).all() and (a.sum(axis=-1) == TOTAL).all()


def fix_total(alloc):
    """Force a (possibly sloppy) allocation to sum to 100 by adjusting the largest castle.

    Mirrors what a real form does: you cannot submit 99 or 101 soldiers, so the
    applicant nudges their biggest pile until the counter reads 100/100.
    """
    a = np.array(alloc, dtype=int).clip(0)
    diff = TOTAL - a.sum()
    a[int(np.argmax(a))] += diff
    if a.min() < 0:  # pathological input: fall back to proportional rescale
        a = np.floor(np.array(alloc, float).clip(0) / max(sum(alloc), 1) * TOTAL).astype(int)
        a[int(np.argmax(a))] += TOTAL - a.sum()
    return a


# --------------------------------------------------------------------------
# Game 1: head to head (separable, so everything is exact)
# --------------------------------------------------------------------------
def game1_points(a, b):
    """Points `a` earns against `b` in one matchup (broadcasts over leading axes)."""
    a, b = np.asarray(a), np.asarray(b)
    return (VALUES * ((a > b) + 0.5 * (a == b))).sum(axis=-1)


def game1_tables(field, weights=None):
    """P[i, s] = expected points from castle i when sending s soldiers vs one field draw.

    Because the Game 1 score is a sum over castles, a candidate's expected score
    against the whole field is simply sum_i P[i, s_i].
    """
    field = np.asarray(field)
    w = np.ones(len(field)) if weights is None else np.asarray(weights, float)
    w = w / w.sum()
    P = np.zeros((N_CASTLES, TOTAL + 1))
    for i in range(N_CASTLES):
        pmf = np.bincount(field[:, i], weights=w, minlength=TOTAL + 1)[: TOTAL + 1]
        below = np.concatenate([[0.0], np.cumsum(pmf)[:-1]])
        P[i] = VALUES[i] * (below + 0.5 * pmf)
    return P


def game1_scores(cands, P):
    cands = np.asarray(cands)
    return P[np.arange(N_CASTLES), cands].sum(axis=-1)


def game1_best_response(P, top=1, cands=None):
    """Exact best response(s) to a field summarised by tables P.

    top=1 uses a knapsack DP (instant). top>1 scores every allocation (or the
    supplied candidate set) and returns the `top` best as (allocs, scores).
    """
    if top == 1 and cands is None:
        best = P[0].copy()             # best[t]: best value using castles seen so far with t soldiers
        choice = [np.arange(TOTAL + 1)]
        for i in range(1, N_CASTLES):
            # M[t, s] = best[t - s] + P[i, s] for s <= t
            t = np.arange(TOTAL + 1)[:, None]
            s = np.arange(TOTAL + 1)[None, :]
            M = np.where(s <= t, best[np.clip(t - s, 0, None)] + P[i][s], -np.inf)
            pick = M.argmax(axis=1)
            best = M[np.arange(TOTAL + 1), pick]
            choice.append(pick)
        alloc = np.zeros(N_CASTLES, dtype=int)
        t = TOTAL
        for i in range(N_CASTLES - 1, 0, -1):
            alloc[i] = choice[i][t]
            t -= alloc[i]
        alloc[0] = t
        return alloc, float(best[TOTAL])
    cands = all_allocations() if cands is None else np.asarray(cands)
    sc = game1_scores(cands, P)
    idx = np.argpartition(-sc, min(top, len(sc) - 1))[:top]
    idx = idx[np.argsort(-sc[idx])]
    return cands[idx], sc[idx]


def game1_equilibrium(iters=6000, start=(7, 13, 20, 27, 33)):
    """Approximate Game 1 Nash equilibrium by fictitious play.

    Each iteration best-responds (exactly, via the DP) to the empirical mix of
    all previous iterations. Returns the post-burn-in iterates; sampling a row
    uniformly is a draw from the approximate equilibrium.
    """
    counts = np.zeros((N_CASTLES, TOTAL + 1))
    cur = np.asarray(start)
    history = []
    for _ in range(iters):
        counts[np.arange(N_CASTLES), cur] += 1
        history.append(cur)
        pmf = counts / counts[0].sum()
        below = np.concatenate([np.zeros((N_CASTLES, 1)), np.cumsum(pmf, axis=1)[:, :-1]], axis=1)
        cur, _ = game1_best_response(VALUES[:, None] * (below + 0.5 * pmf))
    history = np.array(history)
    return history[len(history) // 5:]


def game1_round_robin(pop):
    """Average Game 1 score of each player against every *other* player."""
    pop = np.asarray(pop)
    M = game1_points(pop[:, None, :], pop[None, :, :])
    np.fill_diagonal(M, 0.0)
    return M.sum(axis=1) / (len(pop) - 1), M


# --------------------------------------------------------------------------
# Game 2: four-way battle
# --------------------------------------------------------------------------
def _payout_table():
    """T[g, e] = payout for a player with g opponents strictly ahead and e tied with them."""
    T = np.zeros((4, 4))
    for g in range(4):
        for e in range(4 - g):
            T[g, e] = PAYOUTS[g : g + e + 1].mean()
    return T


PAYOUT_TABLE = _payout_table()


def group_points12(groups):
    """Castle points (x12) for every member of every group. groups: (..., 4, 5) -> (..., 4)."""
    groups = np.asarray(groups)
    m = groups.max(axis=-2, keepdims=True)
    at_max = groups == m
    n_max = at_max.sum(axis=-2, keepdims=True)
    return (at_max * (VALUES12 // n_max)).sum(axis=-1)


def group_payouts(groups):
    """Rank payouts (9/4/2/0 with tie splitting) for each member. (..., 4, 5) -> (..., 4)."""
    pts = group_points12(groups)
    ahead = (pts[..., None, :] > pts[..., :, None]).sum(axis=-1)
    tied = (pts[..., None, :] == pts[..., :, None]).sum(axis=-1) - 1
    return PAYOUT_TABLE[ahead, tied]


def game2_expected(cands, opp_triples, batch=None):
    """Mean Game 2 payout of each candidate against a fixed sample of opponent triples.

    cands: (n, 5); opp_triples: (K, 3, 5). Using the same triples for every
    candidate (common random numbers) makes comparisons between candidates far
    less noisy than independent sampling would.
    """
    cands = np.asarray(cands, dtype=np.int16)
    opp = np.asarray(opp_triples, dtype=np.int16)
    K = len(opp)
    if batch is None:
        batch = max(1, int(4e6 // (K * 20)))
    out = np.empty(len(cands))
    opp_max = opp.max(axis=1)                                   # (K, 5)
    opp_atmax = opp == opp_max[:, None, :]                      # (K, 3, 5)
    opp_nmax = opp_atmax.sum(axis=1)                            # (K, 5)
    for lo in range(0, len(cands), batch):
        c = cands[lo : lo + batch][:, None, :]                  # (b, 1, 5)
        mx = np.maximum(c, opp_max[None])                       # (b, K, 5)
        me_top = c == mx
        opp_top = opp_atmax[None] & (opp_max[None] == mx)[:, :, None, :]   # (b, K, 3, 5)
        n_top = me_top + opp_top.sum(axis=2)                    # (b, K, 5)
        share = VALUES12 // n_top
        me_pts = (me_top * share).sum(axis=-1)                  # (b, K)
        opp_pts = (opp_top * share[:, :, None, :]).sum(axis=-1) # (b, K, 3)
        ahead = (opp_pts > me_pts[..., None]).sum(axis=-1)
        tied = (opp_pts == me_pts[..., None]).sum(axis=-1)
        out[lo : lo + batch] = PAYOUT_TABLE[ahead, tied].mean(axis=1)
    return out


def game2_detail(cand, opp_triples):
    """Finish profile of one allocation against opponent triples (ties for a place count as that place)."""
    opp = np.asarray(opp_triples)
    groups = np.concatenate([np.broadcast_to(np.asarray(cand), (len(opp), 1, N_CASTLES)), opp], axis=1)
    pts = group_points12(groups) / SCALE
    ahead = (pts[:, 1:] > pts[:, [0]]).sum(axis=1)
    return {"mean_payout": round(float(group_payouts(groups)[:, 0].mean()), 3),
            "p_first": round(float((ahead == 0).mean()), 3),
            "p_top2": round(float((ahead <= 1).mean()), 3),
            "p_last": round(float((ahead == 3).mean()), 3),
            "mean_castle_points": round(float(pts[:, 0].mean()), 3)}


def sample_triples(field, K, rng, weights=None):
    """K independent groups of 3 opponents drawn (with replacement) from a field."""
    field = np.asarray(field)
    p = None if weights is None else np.asarray(weights, float) / np.sum(weights)
    idx = rng.choice(len(field), size=(K, 3), p=p)
    return field[idx]


def game2_tournament(pop, n_shuffles, rng):
    """Simulate the real Game 2 format: shuffle everyone into groups of 4, many times.

    Returns (mean payout per player, P(1st/2nd/3rd/4th) per player, mean castle points).
    Players left over when len(pop) is not a multiple of 4 sit out that shuffle.
    """
    pop = np.asarray(pop)
    N = len(pop)
    G = N // 4
    total = np.zeros(N)
    games = np.zeros(N)
    place = np.zeros((N, 4))
    pts_sum = np.zeros(N)
    chunk = max(1, 200_000 // max(G, 1))
    done = 0
    while done < n_shuffles:
        s = min(chunk, n_shuffles - done)
        perms = np.argsort(rng.random((s, N)), axis=1)[:, : G * 4].reshape(s, G, 4)
        groups = pop[perms]                                     # (s, G, 4, 5)
        pay = group_payouts(groups)
        pts = group_points12(groups) / SCALE
        ahead = (pts[..., None, :] > pts[..., :, None]).sum(axis=-1)
        flat = perms.ravel()
        np.add.at(total, flat, pay.ravel())
        np.add.at(games, flat, 1)
        np.add.at(pts_sum, flat, pts.ravel())
        np.add.at(place, (flat, ahead.ravel()), 1)   # finish counted by players strictly ahead
        done += s
    games = np.maximum(games, 1)
    return total / games, place / games[:, None], pts_sum / games


# --------------------------------------------------------------------------
# Game 2 best-response search
# --------------------------------------------------------------------------
def neighbours(alloc, deltas=(1, 2, 3, 5, 8)):
    """All allocations reachable by moving d soldiers from one castle to another."""
    a = np.asarray(alloc, dtype=np.int16)
    out = []
    for d in deltas:
        for i in range(N_CASTLES):
            if a[i] < d:
                continue
            for j in range(N_CASTLES):
                if i != j:
                    b = a.copy()
                    b[i] -= d
                    b[j] += d
                    out.append(b)
    return np.unique(np.array(out), axis=0)


def game2_best_response(field, rng, weights=None, k_coarse=1500, k_fine=6000,
                        n_seeds=12, extra_seeds=None, coarse_step=5, verbose=False):
    """Approximate best response to a field in Game 2.

    1. Score the whole step-5 grid (10,626 allocations) against k_coarse triples.
    2. Hill-climb from the best n_seeds (plus any extra seeds) with 1/2/3/5/8
       soldier moves, using k_fine common triples, until no move improves.
    3. Return candidates ranked by a fresh, independent evaluation so the
       reported score is not inflated by the search's own noise.
    """
    grid = all_allocations(step=coarse_step)
    coarse = game2_expected(grid, sample_triples(field, k_coarse, rng, weights))
    seeds = list(grid[np.argsort(-coarse)[:n_seeds]])
    if extra_seeds is not None:
        seeds += [np.asarray(s, dtype=np.int16) for s in extra_seeds]
    fine_opp = sample_triples(field, k_fine, rng, weights)
    finals = []
    for s in seeds:
        cur = np.asarray(s, dtype=np.int16)
        cur_v = game2_expected(cur[None], fine_opp)[0]
        for _ in range(60):
            nb = neighbours(cur)
            v = game2_expected(nb, fine_opp)
            j = int(np.argmax(v))
            if v[j] <= cur_v + 1e-9:
                break
            cur, cur_v = nb[j], v[j]
        finals.append(cur)
    finals = np.unique(np.array(finals), axis=0)
    check = game2_expected(finals, sample_triples(field, 4 * k_fine, rng, weights))
    order = np.argsort(-check)
    if verbose:
        for i in order[:5]:
            print("   ", finals[i].tolist(), round(float(check[i]), 3))
    return finals[order], check[order]


# --------------------------------------------------------------------------
# Helpers for modelling imperfect players
# --------------------------------------------------------------------------
def jitter(alloc, rng, moves):
    """Move `moves` single soldiers between random castles (human/AI imprecision)."""
    a = np.array(alloc, dtype=int)
    for _ in range(int(moves)):
        src = rng.choice(np.flatnonzero(a > 0))
        dst = rng.integers(N_CASTLES - 1)
        dst += dst >= src
        a[src] -= 1
        a[dst] += 1
    return a


def round_to(alloc, base):
    """Round to multiples of `base` and repair the total (the 'nice numbers' habit)."""
    a = np.round(np.asarray(alloc, float) / base).astype(int) * base
    return fix_total(a)


def fmt(alloc):
    return "/".join(str(int(x)) for x in alloc)
