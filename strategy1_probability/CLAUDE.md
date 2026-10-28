# Strategy 1: probability rules and level-k reasoning

Solve the Castle Challenge (`../Trial.txt`) analytically. There are no individual
simulated contestants here (that's Strategy 2). The field is a probability
distribution written down from first principles, and every number is an expected
value under that distribution.

## Current results (seed 2026, full run)

- Game 1 pick **1/3/4/39/53**: 8.88 expected over 64 hypotheses (worst 7.38).
  The ladder settles on "concede castles 1-3, stack 4 and 5 at about 40/53".
- Game 2 pick **0/36/0/64/0**: 5.96 expected over 36 hypotheses (worst 5.14),
  1st about 60%. The Game 2 ladder cycles (3+4, then 1-2-3, then 5+1, ...).
- The textbook 7/13/20/27/33 loses 14-1 to 3/14/21/28/34, and averages 6.47 / 2.11.
- The final submission (root `README.md`, from `../compare_strategies.py`) keeps the
  Game 2 idea and takes Strategy 2's Game 1 numbers (2/16/1/38/43), which score 8.57
  in this model.

## Files

| File | What it does |
|---|---|
| `analysis.py` | The whole pipeline. `python analysis.py` (full, about 12 min) or `--quick` (about 4 min). |
| `make_charts.py` | Renders `results/fig_*.png` from `results/strategy1_results.json`. |
| `EXPLAINED.md` | Plain-English write-up for a non-technical reader. Keep it in sync when results change. |
| `results/strategy1_results.json` | All outputs (keys listed below). |
| `results/model_fields.npz` | The modelled fields (Game 1 score tables per hypothesis, Game 2 opponent triples per hypothesis). `../compare_strategies.py` uses it to test any allocation in this model. |
| `results/run_log.txt` | Log of the last full run. |

The scoring rules live in `../shared/castle.py` and are shared with Strategy 2.
They are tested against brute-force reference implementations. If you change
them, re-run the checks described in the root `README.md`.

## Pipeline (sections of `analysis.py`)

1. **Game 1 theory.** The closed-form continuous equilibrium has castle i's marginal
   uniform on `[0, 2*100*v_i/15]` = `[0, 13.3 v_i]`. That gives the key identity: *any*
   allocation with `s_i <= 13.3 v_i` for every castle scores exactly 7.5 against the
   equilibrium. The discrete equilibrium is approximated by fictitious play
   (`castle.game1_equilibrium`), and its exploitability is reported.
2. **Game 1 ladder.** Round 0 is a mixture of naive anchors (`G1_ANCHORS`: proportional
   7/13/20/27/33, round ladders, even 20s, top-heavy, uniform random). Round k is a
   *quantal* best response to the cognitive-hierarchy mix of rounds 0..k-1
   (Poisson tau). The exact best response at each round is reported as "the most
   winning move" for that round.
3. **Game 1 pick.** 64 hypotheses: 4 round-0 variants x tau {0.5, 1, 1.5, 2.5} x
   temperature {0.3, 0.8} x Nash-player share {0, 15%}. Game 1 expected score is
   linear in the field, so the Bayes-optimal pick is the exact DP best response to
   the *average* of the per-hypothesis score tables.
4. **Game 2 rules.** Soldiers needed to beat 1 versus 3 opponents. Uses `F(s)^3`,
   the probability that all three opponents send fewer soldiers.
5. **Game 2 theory.** Multiplicative-weights (Hedge) self-play on the step-5 grid
   (10,626 strategies). It is an approximation, and `best_reply_payout` above 3.75
   measures how far from equilibrium it still is.
6. **Game 2 ladder and pick.** Same cognitive-hierarchy structure with quantal
   responses on the step-5 grid plus integer jitter: 3 variants x 3 tau x 2
   temperatures x 2 Nash shares = 36 hypotheses. The pick comes from hill climbing on
   pooled opponent triples (equal count per hypothesis, so the mean equals the
   hypothesis average), then a fresh independent evaluation per hypothesis.

## Lessons learned (don't repeat these mistakes)

- **Never model a reasoning level as one exact best response plus small jitter.** The
  first version did this. Each level became a monoculture, the next level farmed it,
  and Game 2 payouts reached about 7.7/9, which is not believable. Quantal (softmax)
  responses fixed it, because people at the same depth of thinking give a spread of
  near-best answers. The temperature is the knob, so keep it in the hypothesis grid.
- Game 2 searches must use **common random numbers**: the same opponent triples for
  every candidate. Otherwise Monte Carlo noise picks the winner. Always re-score the
  final candidates on *fresh* triples (winner's curse).
- Hedge on the 4-player game does not fully converge. Report exploitability and don't
  call the result "the" equilibrium.

## Results keys (`strategy1_results.json`)

`game1_theory` (closed form, fictitious play) · `game1.ladder_baseline` ·
`game1.beat_the_textbook_answer` · `game1.pick` · `game1.comparison` ·
`game1.per_hypothesis` · `game2_rules` · `game2_theory` · `game2.ladder_baseline` ·
`game2.pick` · `game2.pick_finish_profile` · `game2.comparison` · `game2.per_hypothesis`.

## Ideas for continuing

- Replace the round-0 priors with real data. Once actual applicant submissions or
  survey answers exist, fit the anchor weights to them and re-run. The pick is only
  as good as those priors.
- Fit tau and the temperature by maximum likelihood to Strategy 2's 30 real AI answers
  (`../strategy2_simulation/contestants/ai_contestants.json`) to calibrate the AI share
  of the field.
- Compute a more exact Game 2 equilibrium (double oracle with the hill-climbing best
  response, or a decaying Hedge step size) and compare the pick's exploitability.
- If the organisers combine both games into one ranking, add a joint objective.
