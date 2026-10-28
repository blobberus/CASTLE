# CASTLE: solving the Castle Challenge two ways

The task (`Trial.txt`): split 100 soldiers over castles worth 1-5 points, in a
**head-to-head** game (Game 1) and a **four-player ranked** game (Game 2, paying
9/4/2/0). It was solved two independent ways, and the answers were then put
against each other.

## Final answer

| | Castle 1 | Castle 2 | Castle 3 | Castle 4 | Castle 5 |
|---|---|---|---|---|---|
| **Game 1** | **2** | **16** | **1** | **38** | **43** |
| **Game 2** | **1** | **37** | **0** | **62** | **0** |

How these do (an average applicant scores 7.5 in Game 1 and 3.75 in Game 2):

| | Probability model (Strategy 1) | Simulated 100-applicant field (Strategy 2) |
|---|---|---|
| Game 1 `2/16/1/38/43` | 8.57 expected (worst of 64 scenarios: 7.05) | 10.30; beats **every** applicant in 74% of 200 re-drawn fields |
| Game 2 `1/37/0/62/0` | 5.94 expected, 1st about 61% of the time | 7.99, 1st about 84% of the time; beats every applicant in 77% of fields |

**Suggested STRATEGY box text:**

> Game 1: Because my score is an average over every matchup, each castle is a
> separate bet worth its points times the share of opponents I outbid. I expected
> most applicants to use AI, and AI answers cluster on 7/13/20/27/33 or "one more
> than a round number" (21-25 on castle 3, 30-37 on castle 4, 33-42 on castle 5).
> Castle 3 was the most over-contested for its value, so I conceded it. I put just
> enough above the clusters on castles 4 and 5 (38/43), plus a cheap win on castle 2
> (16), which most entries starve. Game 2: Yes, my strategy changed. Against three
> opponents a castle needs the top bid of four, so spreading out wins nothing, and
> first place pays 9. Most players fight over castle 5 or the 3-4-5 block, so I took
> the two castles they under-defend, by margins few will match: 62 on castle 4 and 37
> on castle 2. That's 6 points, and the other castles (5, 3, 1) usually split between
> different opponents, so 6 usually finishes first.

## The two approaches

| | Strategy 1: probability rules | Strategy 2: simulated contestants |
|---|---|---|
| Folder | [`strategy1_probability/`](strategy1_probability/) | [`strategy2_simulation/`](strategy2_simulation/) |
| Idea | Treat the field as a probability distribution. Find the perfect (Nash) strategy, climb a round-by-round "I think that you think" ladder, then pick the move that's best on average over 64 (Game 1) / 36 (Game 2) possible fields. | Build 100 individual applicants: **30 real AI answers** (fresh Claude Haiku/Sonnet/Opus chats given the verbatim challenge), 20 AI-then-tweak users, 15 metastrategists, 35 by-hand solvers. Play both games exactly by the rules, re-draw the crowd 200 times, then find the best reply to the crowd. |
| Game 1 pick | 1/3/4/39/53 | 2/16/1/38/43 |
| Game 2 pick | 0/36/0/64/0 | 3/35/0/62/0 |
| Plain-English write-up | [EXPLAINED.md](strategy1_probability/EXPLAINED.md) | [EXPLAINED.md](strategy2_simulation/EXPLAINED.md) |
| How to continue it | [CLAUDE.md](strategy1_probability/CLAUDE.md) | [CLAUDE.md](strategy2_simulation/CLAUDE.md) |

### Head to head (`compare_strategies.py` → `results/comparison.json`)

Each pick was scored inside *both* models. Higher is better.

**Game 1** (average applicant = 7.5)

| Allocation | In model 1 | In model 2 | Beats every applicant (model 2) |
|---|---|---|---|
| **2/16/1/38/43 (final; = Strategy 2's pick)** | 8.57 | **10.30** | **74%** |
| 1/3/4/39/53 (Strategy 1's pick) | **8.88** | 9.71 | 0.5% |
| 1/1/23/33/42 (best simulated applicant) | 8.34 | 10.03 | 12% |
| 1/3/22/32/42 (best real AI answer, Opus) | 8.24 | 9.72 | 0% |
| 7/13/20/27/33 (the "textbook optimal") | 6.47 | 5.46 | 0% |
| 20/20/20/20/20 | 6.11 | 4.55 | 0% |

**Game 2** (average applicant = 3.75)

| Allocation | In model 1 | In model 2 | Beats every applicant (model 2) |
|---|---|---|---|
| **1/37/0/62/0 (final, consensus)** | 5.94 | 7.99 | 77% |
| 0/36/0/64/0 (Strategy 1's pick) | **5.96** | 7.93 | 72% |
| 3/35/0/62/0 (Strategy 2's pick) | 5.71 | **8.05** | **81%** |
| 21/28/51/0/0 (best real AI answer, Opus) | 5.21 | 6.92 | 1% |
| 0/0/0/0/100 (all on castle 5) | 5.12 | 5.57 | 0% |
| 7/13/20/27/33 | 2.11 | 1.56 | 0% |

- **Game 2: the strategies agree.** They worked independently, one with no simulated
  people at all, and both landed on *castle 2 + castle 4, about 36/63*. The three
  versions are statistically tied, and the consensus is their average.
- **Game 1: the strategies agree on the shape**: concede castle 3, stack castles 4 and
  5. They differ on castle 2. The final pick is Strategy 2's: it costs only 0.31
  points in Strategy 1's model, but Strategy 1's pick almost never tops the realistic
  AI-heavy crowd.

## Critical findings

1. **The "optimal" answer everyone quotes, 7/13/20/27/33, is a trap.** It's the
   *average* of the perfect random strategy, not the strategy. It loses 14-1 to
   3/14/21/28/34 and finishes in the bottom quarter in both models.
2. **The perfect (Nash) strategy only guarantees average.** Against it, every sensible
   allocation scores exactly 7.5. Real points come from exploiting how real people play.
3. **Most applicants using AI makes the field predictable.** Haiku gave the textbook
   answer 7/10 times. Sonnet and Opus mostly bid "one more than a round number" on
   castles 3-5. That over-fights castle 3 and leaves castle 2 cheap, which is exactly
   what the final picks exploit.
4. **Pasting the prompt into an AI and submitting the answer is a mid-table result**
   (about 49th of 100 in Game 1, 52nd in Game 2). Which AI matters: Opus averaged
   5.90 in Game 2, against 2.3-2.5 for Sonnet and Haiku.
5. **Metastrategy wins.** Every top strategy type thinks about the *other* players.
   The best one was to ask the AI several times to see what AI users will submit,
   then counter it.
6. **Concentrate and avoid round numbers.** These were the strongest predictors of a
   high score in both games. Spreading out is the most reliable way to lose.
7. **Game 2 is rock-paper-scissors.** Every popular plan has a counter (3+4 beats
   "go big on 5", 1-2-3 beats 3+4, 5+1 beats 1-2-3, ...). The robust move takes the
   castles the popular plans under-defend, by margins nobody else bothers with.

## Repository layout

```
Trial.txt                      the challenge
README.md                      this file (final answer + comparison)
compare_strategies.py          scores every pick in both models, finds the consensus
results/comparison.json        output of compare_strategies.py
shared/castle.py               exact game rules + best-response search (used by both)
shared/chart_style.py          chart styling
strategy1_probability/         Strategy 1: analysis.py, EXPLAINED.md, CLAUDE.md, results/
strategy2_simulation/          Strategy 2: population.py, run_simulation.py,
                               contestants/ (30 real AI answers + the 100), EXPLAINED.md, CLAUDE.md, results/
```

## Reproduce

Requires Python 3.11+ with `numpy` and `matplotlib`.

```bash
python strategy1_probability/analysis.py        # ~12 min   (--quick for ~4 min)
python strategy2_simulation/run_simulation.py   # ~4 min    (--quick for ~1 min)
python compare_strategies.py                    # ~1.5 min
python strategy1_probability/make_charts.py
python strategy2_simulation/make_charts.py
```

All runs are seeded, so the numbers above reproduce exactly. The scoring engine was
checked against brute-force reference implementations:

- 3,000 random four-player groups matched exactly.
- The Game 1 knapsack matched an exhaustive search over all 4,598,126 allocations.
- Every simulated group pays out exactly 15 points in total.

## Caveats

Nobody can see the real applicant pool. The 30 AI answers are real but come only
from Claude models. Real applicants also use ChatGPT, Gemini and others. The other
70 applicants and Strategy 1's field priors are informed models, not data. Both
picks stayed well above average in every variation tested (different AI shares,
0-50 metastrategists, 64 probability scenarios), but none of this is a guarantee.
