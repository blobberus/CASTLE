# Strategy 2: simulate 100 contestants, then play them against each other

Every contestant receives the same prompt (`../Trial.txt`) and decides on their
own. Variance comes from *how* they approach it. The user's assumption is that
most applicants use AI, so 65 of the 100 are AI-influenced.

## Current results (seed 7, full run, 200 replications)

- 101st-entrant picks: Game 1 **2/16/1/38/43** (10.30 average, 1st of 101 in 89% of
  replications) and Game 2 **3/35/0/62/0** (8.06, 1st in 80%). Both stay well above
  average across all 10 sensitivity mixes.
- Winning archetype: `meta_ai_sampler` (won 179/200 Game 1 and 152/200 Game 2
  tournaments). All top-4 archetypes in both games are metastrategists.
- Raw AI answers rank about 49th (Game 1) and 52nd (Game 2) of 100. Opus beats Sonnet
  and Haiku by far in Game 2 (5.90 vs 2.33 / 2.54). Haiku gave 7/13/20/27/33 in 7 of 10.
- Strongest trends: concentration (+0.84 / +0.81 Spearman with score), number of
  castles with 10+ soldiers (-0.77 / -0.69), round numbers (-0.46 / -0.39).

## Files

| File | What it does |
|---|---|
| `contestants/ai_contestants.json` | The **30 real AI contestants**: fresh Claude subagents, full replies included. Committed; don't regenerate casually. |
| `collect_ai_contestants.py` | One-off harvester that pulled those answers out of the Claude Code subagent transcripts. |
| `population.py` | Builds the 100 contestants. Each archetype is a `gen_<name>(rng, ai)` function returning `(game1, game2, reasoning)`. |
| `run_simulation.py` | Full pipeline: tournament, breakdowns, trends, replications, AI-share sensitivity, 101st-entrant best response. `--quick` for iterating. |
| `make_charts.py` | Renders `results/fig_*.png`. |
| `contestants/population.json` | The baseline 100 with allocations, reasoning, STRATEGY text and their scores. |
| `results/simulation_results.json` | All analysis outputs. |
| `results/leaderboard.csv` | Baseline leaderboard (both games, combined rank). |
| `results/model_fields.npz` | Every replication's field, used by `../compare_strategies.py`. |
| `EXPLAINED.md` | Plain-English write-up. Keep it in sync with results. |

## How the 30 AI contestants were made

- 5 prompt framings x 3 models (haiku, sonnet, opus) x 2 replicates (different small
  wording). The framings are `verbatim` (paste only), `optimal` ("what's optimal?"),
  `quick` ("3 minutes, just numbers"), `field_aware` ("others use AI too, beat them")
  and `game_theory` ("use Blotto/Nash"). The exact prompt each contestant received
  is stored verbatim in its record's `prompt_sent` field, and its whole reply is in
  `full_reply`.
- Each was told to act as a normal chat assistant, use no tools, and end with a JSON
  block.
- **Why 30:** with n=30 independent samples, any answer-style that at least 10% of AI
  replies would produce shows up with 95% probability (0.9^30 < 0.05).
- **Contamination lesson.** The first attempt used the Workflow tool, which relays the
  *user's* original request to every subagent. The "contestants" saw the whole
  project brief and one started building the project. That run was discarded and
  redone with plain `Agent` calls (prompt only), and the transcripts were checked for
  the leak. If you regenerate, use the Agent tool and check for leaks the same way.
- Limitation: only Claude models. Real applicants also use ChatGPT, Gemini and others.
  To add them, append records with the same schema (`id`, `framing`, `model`, `game1`,
  `game2`, `strategy_text`, `reasoning_summary`) and bump `ai_verbatim` in `BASE_MIX`.

## Population (`BASE_MIX` in population.py)

| Group | Count | Archetypes |
|---|---|---|
| AI-assisted | 50 | `ai_verbatim` 30 (real), `ai_round` 7, `ai_gut` 7, `ai_plus1` 6 |
| Metastrategists | 15 | `meta_level2`, `meta_simulator`, `meta_ai_sampler`, `meta_equilibrium`, `meta_contrarian` (3 each) |
| Humans (no AI) | 35 | proportional 7, round 5, even 4, top-heavy 5, all-in 3, plus-one 4, random 4, underdog 3 |

Each modelled contestant gets its own RNG stream, so they decide independently.
Metastrategists best-respond to their **own belief** about the field, never the real
field. That is the point: they can be wrong.

## Pipeline (`run_simulation.py`)

1. Baseline population (seed 7) gives `contestants/population.json`.
2. Game 1 exact round robin, then the Game 2 tournament (20,000 reshuffles of 25
   groups). Finishes count ties as the better place.
3. Breakdowns by category, archetype, AI model and AI framing.
4. Spearman trends between allocation features and score.
5. 200 replications: AI answers bootstrapped, modelled people re-decide (expensive
   metastrategists come from a precomputed library), 2,000 Game 2 reshuffles each.
6. The 101st entrant: exact DP best response for Game 1, and Game 2 hill climbing on
   pooled triples from all replications. Each is evaluated per replication (mean,
   rank-1 rate).
7. Sensitivity, 60 replications per setting, two sweeps via `mix_with_shares()`:
   AI-assisted vs human seats with metastrategists fixed at 15, and metastrategist
   seats 0/5/15/30/50. Each setting reports the top archetypes and how the
   101st-entrant picks fare. Don't scale *all* non-AI groups together: that silently
   deletes the metastrategists. An earlier version did this and drew a misleading
   "top-heavy humans win" conclusion.

## Gotchas

- Game 2 mean payout over everyone is always 3.75, and Game 1 average is 7.5. Use
  these as sanity checks after any rules change.
- The 101st-entrant Game 2 rank compares its expected payout with contestants'
  tournament payouts. That is approximate, because the contestants didn't face the
  entrant.
- The robust best response is robust *to this generative model*, not to reality.
  `../compare_strategies.py` checks it against Strategy 1's independent model too.

## Ideas for continuing

- Add non-Claude AI answers (ChatGPT, Gemini) and see whether the AI cluster moves.
- Let metastrategists react to *each other* (an arms race of level-3 simulators).
- Calibrate the human archetype weights from published Blotto experiment data, or
  from real submissions if the organisers publish them.
