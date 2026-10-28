# CASTLE: solving the Castle Challenge two ways (plus a 500-player rerun)

The task (`Trial.txt`): split 100 soldiers over castles worth 1-5 points, in a
**head-to-head** game (Game 1) and a **four-player ranked** game (Game 2, paying
9/4/2/0). It was solved two independent ways, and the answers were then put
against each other. Strategy 2's simulation was then rerun from scratch with
500 applicants instead of 100 ([Model 3](#model-3-the-simulation-rerun-with-500-applicants)).

## Final answer

| | Castle 1 | Castle 2 | Castle 3 | Castle 4 | Castle 5 |
|---|---|---|---|---|---|
| **Game 1** | **2** | **16** | **1** | **38** | **43** |
| **Game 2** | **1** | **37** | **0** | **62** | **0** |

How these do (an average applicant scores 7.5 in Game 1 and 3.75 in Game 2):

| | Probability model (Strategy 1) | Simulated 100-applicant field (Strategy 2) | Simulated 500-applicant field (Model 3) |
|---|---|---|---|
| Game 1 `2/16/1/38/43` | 8.57 expected (worst of 64 scenarios: 7.05) | 10.30; beats **every** applicant in 74% of 200 re-drawn fields | 10.41; beats **every** applicant in 94.5% of 200 re-drawn fields |
| Game 2 `1/37/0/62/0` | 5.94 expected, 1st about 61% of the time | 7.99, 1st about 84% of the time; beats every applicant in 77% of fields | 7.52, 1st about 76% of the time; beats every applicant in 25.5% of fields |

Model 3 confirms the Game 1 answer: its own pick, `3/16/1/37/43`, is one soldier
away. In Game 2 it prefers a different shape, `7/25/0/0/68` (castles 1+2+5). The
final answer stays because it is the best when all three models are averaged
(7.15 against 6.78; [details](#head-to-head-compare_strategiespy--resultscomparisonjson)).
The three-model consensus, `1/36/0/63/0`, is one soldier away and statistically tied
(7.154 against 7.152).

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

## The approaches

| | Strategy 1: probability rules | Strategy 2: simulated contestants | Model 3: Strategy 2 rerun at 5x scale |
|---|---|---|---|
| Folder | [`strategy1_probability/`](strategy1_probability/) | [`strategy2_simulation/`](strategy2_simulation/) | [`model3_simulation_500/`](model3_simulation_500/) |
| Idea | Treat the field as a probability distribution. Find the perfect (Nash) strategy, climb a round-by-round "I think that you think" ladder, then pick the move that's best on average over 64 (Game 1) / 36 (Game 2) possible fields. | Build 100 individual applicants: **30 real AI answers** (fresh Claude Haiku/Sonnet/Opus chats given the verbatim challenge), 20 AI-then-tweak users, 15 metastrategists, 35 by-hand solvers. Play both games exactly by the rules, re-draw the crowd 200 times, then find the best reply to the crowd. | The same simulation rebuilt from scratch with **500 applicants**: **150 new real AI answers** (50 each from Haiku, Sonnet and Opus), 100 AI-then-tweak users, 75 metastrategists, 175 by-hand solvers. No answers or results from Strategy 2 are reused. |
| Game 1 pick | 1/3/4/39/53 | 2/16/1/38/43 | 3/16/1/37/43 |
| Game 2 pick | 0/36/0/64/0 | 3/35/0/62/0 | 7/25/0/0/68 |
| Plain-English write-up | [EXPLAINED.md](strategy1_probability/EXPLAINED.md) | [EXPLAINED.md](strategy2_simulation/EXPLAINED.md) | [Model 3 section below](#model-3-the-simulation-rerun-with-500-applicants) |
| How to continue it | [CLAUDE.md](strategy1_probability/CLAUDE.md) | [CLAUDE.md](strategy2_simulation/CLAUDE.md) | [CLAUDE.md](model3_simulation_500/CLAUDE.md) |

### Head to head (`compare_strategies.py` → `results/comparison.json`)

Each pick was scored inside *every* model. Higher is better.

**Game 1** (average applicant = 7.5)

| Allocation | In model 1 | In model 2 | Beats every applicant (model 2) | In model 3 | Beats every applicant (model 3) |
|---|---|---|---|---|---|
| **2/16/1/38/43 (final; = Strategy 2's pick)** | 8.57 | **10.30** | **74%** | 10.41 | 94.5% |
| 3/16/1/37/43 (model 3's pick) | 8.53 | 10.29 | 72% | **10.43** | **99.5%** |
| 1/3/4/39/53 (Strategy 1's pick) | **8.88** | 9.71 | 0.5% | 9.72 | 0% |
| 1/1/23/33/42 (best simulated applicant in model 2; also 2 Opus answers in model 3) | 8.34 | 10.03 | 12% | 9.99 | 0% |
| 1/21/1/36/41 (best real AI answer in model 3, Opus) | 8.27 | 9.88 | 1.5% | 10.09 | 0% |
| 1/3/22/32/42 (best real AI answer in model 2, Opus) | 8.24 | 9.72 | 0% | 9.71 | 0% |
| 7/13/20/27/33 (the "textbook optimal") | 6.47 | 5.46 | 0% | 5.54 | 0% |
| 20/20/20/20/20 | 6.11 | 4.55 | 0% | 4.49 | 0% |

**Game 2** (average applicant = 3.75)

| Allocation | In model 1 | In model 2 | Beats every applicant (model 2) | In model 3 | Beats every applicant (model 3) |
|---|---|---|---|---|---|
| **1/37/0/62/0 (final, consensus of models 1+2)** | 5.94 | 7.99 | 77% | 7.52 | 25.5% |
| 1/36/0/63/0 (consensus of all three models) | 5.92 | 7.99 | 77% | 7.56 | 32.5% |
| 0/36/0/64/0 (Strategy 1's pick) | **5.96** | 7.93 | 72% | 7.55 | 30% |
| 3/35/0/62/0 (Strategy 2's pick) | 5.71 | **8.05** | **81%** | 7.55 | 30% |
| 7/25/0/0/68 (model 3's pick) | 4.94 | 7.69 | 40% | **7.71** | **66.5%** |
| 12/21/0/0/67 (best real AI answer in model 3, Opus) | 4.96 | 7.39 | 12% | 7.58 | 23.5% |
| 21/28/51/0/0 (best real AI answer in model 2, Opus) | 5.21 | 6.92 | 1% | 7.44 | 6% |
| 0/0/0/0/100 (all on castle 5) | 5.12 | 5.57 | 0% | 5.65 | 0% |
| 7/13/20/27/33 | 2.11 | 1.56 | 0% | 1.55 | 0% |

- **Game 1: all three models agree.** They all concede castle 3 and stack castles 4
  and 5. Strategy 1 differs on castle 2. The final pick is Strategy 2's. It costs only
  0.31 points in Strategy 1's model, but Strategy 1's pick almost never tops the
  realistic AI-heavy crowd. Model 3, built from 150 brand-new AI answers, lands one
  soldier away, and the final pick beats all 500 applicants in 94.5% of its fields.
- **Game 2: Strategies 1 and 2 agree, and model 3 dissents.** The first two worked
  independently, one with no simulated people at all, and both landed on *castle 2 +
  castle 4, about 36/63*. Model 3 prefers *castles 1 + 2 + 5*, because its crowd
  holds many more "castle 3 + castle 5" bets: 34 of its 150 AI answers (all Opus) put
  59-66 on castle 5, against 4 of 30 in model 2. 68 on castle 5 beats every one of
  them, and they leave castles 1 and 2 open. Inside model 3 the gap is small (7.71
  against 7.52, and the final pick still finishes 1st in about 76% of its groups).
  Model 1 rates the 1+2+5 shape poorly, though (4.94 against 5.94). Averaged over all
  three models the castle 2+4 shape still wins: 7.15 against 6.78.

## Model 3: the simulation rerun with 500 applicants

This is Strategy 2's simulation rerun from scratch: the same game engine, the same 10
prompts and the same applicant types, but 5x the people and all-new AI answers.
Nothing from the 100-applicant run (its AI answers, its results or its picks) was
an input. The metrics below are the same ones reported for Strategy 2 in its
[EXPLAINED.md](strategy2_simulation/EXPLAINED.md). Model 2's value is in brackets
where it helps.

### 1. Who the 500 applicants are

| Group | How many | Who they are |
|---|---|---|
| **Real AI answers** | 150 (30) | **150 fresh AI chats**, 50 each of Claude Haiku, Sonnet and Opus. Each got the verbatim challenge in one of the same 5 framings × 2 wordings as model 2, with each prompt sent 5 times, the way many people paste the same text. None saw the others, this project or model 2's answers. All 150 passed an isolation check (their only action was reading their own prompt file). They submit the AI's answer unchanged. |
| **Asked an AI, then fiddled** | 100 (20) | Rounded an AI answer to 5s (35), moved a few soldiers on a hunch (35), or added +1 to beat ties (30). |
| **Metastrategists** | 75 (15) | 15 each of level-2 thinkers, simulators, AI samplers, equilibrium players and contrarians. |
| **Solving it by hand** | 175 (35) | Proportional (35), round numbers (25), 20 everywhere (20), skip the cheap castles (25), all-in (15), "one more than others" (20), random (20), take the ignored castles (15). |

The contest was run the same way: Game 1 matches every pair (124,750 matchups), and
Game 2 shuffles everyone into 125 groups of four 20,000 times. Everything was then
redone 200 times with freshly drawn crowds.

### 2. What the 150 AIs said

**Game 1**

| Cluster | Count | Which AI | Average score |
|---|---|---|---|
| Textbook proportional, exactly 7/13/20/27/33 | 28 | all Haiku | **5.54** (bottom quarter) |
| Round-number ladder (e.g. 10/15/20/25/30, 5/10/20/30/35) | 18 | Haiku 16, Sonnet 2 | 6.37 |
| Proportional with "+1" tweaks, keeps some on castle 2, usually 9-14 (e.g. 1/11/21/31/36, given 8 times) | 46 | Opus 27, Sonnet 14, Haiku 5 | 7.56 |
| Almost nothing on 1-2, about a third each on castles 3-5 (e.g. 0/0/30/34/36) | 20 | Sonnet 19, Opus 1 | 8.38 |
| Just above the crowd on castles 3-5, almost nothing on 1-2 (e.g. 1/3/22/33/41) | 33 | Opus 17, Sonnet 15, Haiku 1 | **9.57** |
| Contrarian, starves castle 3, 4 or 5 (e.g. 1/21/1/36/41) | 5 | all Opus | **9.49** |

**Game 2**

| Cluster | Count | Which AI | Average payout |
|---|---|---|---|
| Two-castle bet on castles 3+5 (e.g. 0/0/38/0/62) | 34 | all Opus | **5.70** |
| Two-castle bet on 4+5 or 3+4 (e.g. 0/0/0/49/51, 0/0/44/56/0) | 11 | Sonnet 5, Opus 5, Haiku 1 | 5.54 |
| Three castles, skipping castle 5 (e.g. 0/14/35/51/0) | 7 | all Opus | 5.07 |
| Cheap castles plus one big pile (12/21/0/0/67, 12/17/0/0/71, 13/23/0/64/0) | 3 | all Opus | **7.41** |
| Roughly even over castles 3-5 (e.g. 0/0/25/35/40) | 39 | Sonnet 36, Haiku 3 | **2.21** (bottom quarter) |
| Top-heavy ladder, most on castle 5 (e.g. 5/10/15/30/40) | 56 | Haiku 46, Sonnet 9, Opus 1 | 2.43 |

| AI model | Game 1 average | Game 2 average |
|---|---|---|
| Opus (premium) | 8.75 (8.70) | **5.78** (5.90) |
| Sonnet (standard) | 8.53 (8.19) | 2.71 (2.33) |
| Haiku (fast/free tier) | 5.86 (6.24) | 2.37 (2.54) |

| How the person asked | Game 1 average | Game 2 average |
|---|---|---|
| "Others use AI too, beat them" | **8.13** (8.41) | 3.76 (3.86) |
| "What's the optimal answer?" | 7.96 (8.15) | **3.78** (3.91) |
| "Use game theory" | 7.83 (7.63) | 3.71 (3.60) |
| Just pasted it | 7.38 (7.75) | 3.49 (3.56) |
| "Quick, I have 3 minutes" | 7.26 (6.60) | 3.38 (3.02) |

The AIs behaved the same way at 5x the sample. Haiku gave the textbook answer 28 times
out of 50 (7 of 10 in model 2). Opus is again the only model that reliably makes
concentrated Game 2 bets (49 of 50 answers put 10+ soldiers on at most three castles). The way the
question is asked matters much less than which AI answers it.

### 3. The leaderboards (baseline crowd of 500)

**Game 1**

| Rank | Applicant | Type | Allocation | Score |
|---|---|---|---|---|
| 1 | P283 | AI sampler | 5/16/0/37/42 | 10.31 |
| 2 | P293 | AI sampler | 3/15/0/36/46 | 10.24 |
| 3 | P284 | AI sampler | 8/15/0/35/42 | 10.19 |
| 4 | P281 | AI sampler | 3/16/0/35/46 | 10.19 |
| 5 | P294 | AI sampler | 3/16/0/35/46 | 10.19 |

The best raw AI answer, `1/21/1/36/41` (Opus, asked for "optimal"), came 9th with
10.07. Last place was a random guesser with 3.56.

**Game 2**

| Rank | Applicant | Type | Allocation | Payout | Finished 1st |
|---|---|---|---|---|---|
| 1 | P117 | raw AI (Opus, "beat the others") | 12/17/0/0/71 | 7.66 | 78% |
| 2 | P225 | AI + "+1" | 12/21/0/0/67 | 7.61 | 80% |
| 3 | P120 | raw AI (Opus, "beat the others") | 12/21/0/0/67 | 7.59 | 80% |
| 4 | P293 | AI sampler | 7/23/2/0/68 | 7.58 | 80% |
| 5 | P311 | contrarian | 13/33/52/1/1 | 7.47 | 76% |

Last place was a random guesser with 1.12.

| Group | Game 1 average (rank of 500) | Game 2 average (rank of 500) | Game 2, finished 1st |
|---|---|---|---|
| Metastrategists (75) | **9.39** (88) | **6.09** (83) | **58%** |
| AI-assisted (250) | 7.63 (241) | 3.54 (257) | 24% |
| By hand (175) | 6.50 (333) | 3.05 (313) | 17% |

### 4. Which *types* of strategy win (averaged over 200 re-runs)

| Strategy type | Group | Game 1 avg (rank of 500) | Game 2 avg (rank of 500) |
|---|---|---|---|
| AI sampler | Metastrategist | **10.00** (28) | **6.78** (44) |
| Level-2 thinker | Metastrategist | 9.80 (40) | 6.47 (61) |
| Simulator | Metastrategist | 9.65 (62) | 6.54 (56) |
| Contrarian | Metastrategist | 9.24 (112) | 6.21 (83) |
| Skip the cheap castles | Human | 8.43 (179) | 3.56 (253) |
| AI + gut tweak | AI-assisted | 7.99 (215) | 3.73 (231) |
| AI + "+1" | AI-assisted | 7.93 (215) | 3.69 (241) |
| All-in on 1-2 castles | Human | 7.86 (232) | 5.12 (150) |
| Equilibrium ("perfect" random) | Metastrategist | 7.67 (243) | 3.94 (214) |
| **Raw AI answer** | AI-assisted | **7.65** (239) | **3.56** (258) |
| AI, rounded to 5s | AI-assisted | 7.50 (254) | 3.58 (255) |
| "One more than others" | Human | 7.32 (281) | 2.71 (341) |
| Take the ignored castles | Human | 6.67 (314) | 6.25 (81) |
| Round numbers | Human | 6.09 (374) | 2.06 (391) |
| Proportional | Human | 5.68 (403) | 1.88 (424) |
| Random guess | Human | 5.50 (398) | 2.69 (320) |
| 20 everywhere | Human | 4.51 (482) | 2.00 (391) |

**Who finished 1st of 500** in the 200 re-runs:

| | Game 1 | Game 2 |
|---|---|---|
| Winners by type | AI sampler **200** (model 2: AI sampler 179, level-2 11, simulator 6, other 4) | Raw AI answer **102**, contrarian 26, AI + "+1" 18, AI sampler 18, take-the-ignored 17, AI rounded 13, AI + gut 4, simulator 2 (model 2: AI sampler 152, simulator 22, raw AI 7, other 19) |
| Most common winning allocation | 4/16/0/37/43 (77 wins), 2/16/0/37/45 (37) | 12/21/0/0/67 (68 wins), 12/17/0/0/71 (41) |

The Game 2 column is the biggest change from model 2. The *average* raw AI answer is
still mid-table (258th of 500), but there are 150 AI tickets in the draw. Two Opus
answers that bet on cheap castles plus one big pile, 12/21/0/0/67 and 12/17/0/0/71,
took 109 of the 200 wins between them (counting AI-tweaker copies), more than all
metastrategists combined. The more people paste the prompt into an AI, the more likely
one of those answers lands on the winning shape by chance.

### 5. Trends: what separates winners from losers

Rank correlation between each feature and the score, across all 500 applicants
(+1 = always helps, -1 = always hurts):

| Feature of an allocation | Game 1 | Game 2 |
|---|---|---|
| How concentrated it is (a few big piles) | **+0.83** (+0.84) | **+0.85** (+0.81) |
| Size of the biggest pile | +0.75 (+0.72) | **+0.87** (+0.80) |
| Number of castles with 10+ soldiers | **-0.75** (-0.77) | **-0.70** (-0.69) |
| Soldiers on castle 4 | **+0.77** (+0.83) | +0.17 (+0.24) |
| Soldiers on castle 1 / castle 2 | -0.61 / -0.57 (-0.54 / -0.49) | -0.06 / -0.24 (-0.09 / -0.15) |
| Round-number piles (multiples of 5) | -0.48 (-0.46) | -0.28 (-0.39) |
| Skipping castle 5 entirely | +0.01 (-0.08) | **+0.32** (+0.33) |

Every trend from model 2 reproduces with the same sign and a similar size (no value
moves by more than 0.11): concentrate, avoid round numbers, and in Game 2 dodge the
castle-5 fight.

### 6. The winning strategy: applicant #501

| | Castle 1 | Castle 2 | Castle 3 | Castle 4 | Castle 5 | Result against the simulated crowd |
|---|---|---|---|---|---|---|
| **Game 1** | 3 | 16 | 1 | 37 | 43 | **10.37** in the baseline crowd (**1st of 501**); **10.43** over 200 re-runs, **1st in 99.5%**, top 5 in 100% |
| **Game 2** | 7 | 25 | 0 | 0 | 68 | **7.81** in the baseline crowd (1st of 501; finishes 1st in 84% of its groups, top 2 in 94%); **7.70** over 200 re-runs, **1st in 64.5%**, top 5 in 94% |

(Model 2's #101: Game 1 `2/16/1/38/43`, 1st in 89% of re-runs; Game 2 `3/35/0/62/0`,
1st in 80%.)

- **Game 1 is the same pick as model 2's, give or take one soldier.** Concede castle 3,
  where 60% of the crowd sends 20-23. Win castle 2 cheaply with 16 (beats 82% of the
  crowd there), and sit just above the AI clusters on castles 4 and 5 (beats 92% and
  87%). Game 1 is even more predictable at 500 than at 100: the pick finishes 1st
  almost every time, and before it was added, AI samplers reasoning the same way won
  all 200 re-runs.
- **Game 2 moves from castles 2+4 to castles 1+2+5.** 68 on castle 5 tops every Opus
  "castle 3 + castle 5" bet (59-66) and every ladder (40-50). 25 on castle 2 and 7 on
  castle 1 take two cheap castles nearly everyone leaves light. Only 2% of the crowd
  sends more than 68 to castle 5 and 3% more than 25 to castle 2, so it usually banks
  7 points and often castle 1 too (7.0 castle points per group on average). The plain best reply to the one baseline crowd,
  `5/25/0/0/70`, scored 7.67 over the re-runs, a little below this robust version.

### 7. Does the winner survive a different crowd?

| Crowd (of 500) | Game 1 pick, average | Game 1, beats all 500 | Game 2 pick, average | Game 2, beats all 500 |
|---|---|---|---|---|
| 85 AI users / 340 humans (+75 meta) | 10.01 | 0% | 7.40 | 62% |
| 170 AI / 255 humans | 10.22 | 93% | 7.53 | 73% |
| **250 AI / 175 humans (baseline)** | **10.44** | **100%** | **7.73** | **78%** |
| 340 AI / 85 humans | 10.66 | 93% | 7.89 | 23% |
| 425 AI / 0 humans | 10.89 | 70% | 8.09 | 2% |
| 0 metastrategists | 10.62 | 65% | 7.92 | 32% |
| 25 metastrategists | 10.55 | 90% | 7.86 | 47% |
| 150 metastrategists | 10.23 | 100% | 7.52 | 10% |
| 250 metastrategists | 9.98 | 80% | 7.34 | 0% |

Both picks stay far above average (7.5 and 3.75) in every crowd. "Beats all 500" is a
harder bar than model 2's "beats all 100", because there are five times as many people
who might stumble onto the same idea. The Game 1 pick tops the field in 65-100% of
cases unless AI users are rare. The Game 2 pick is more fragile. In an almost all-AI
crowd, some lucky AI answer edges it out. When metastrategists are 30% or more of the
field, many of them find the same castles 1+2+5 idea and tie or beat it.

### 8. Critical findings from model 3

1. **Game 1 is settled.** Two independent simulations, built from 180 different real
   AI answers, give the same pick to within one soldier. The final answer beats all
   500 applicants in 94.5% of re-runs.
2. **AI answers are stable enough to exploit.** Five times more AI answers produced
   the same clusters in roughly the same proportions: Haiku is textbook, Sonnet spreads
   over castles 3-5, Opus makes concentrated bets. The ranking Opus > Sonnet > Haiku
   held in both games.
3. **The raw AI answer is still exactly average:** 239th of 500 in Game 1 and 258th
   in Game 2, the same mid-table finish as in model 2.
4. **Metastrategy still wins on average.** The top four strategy types in Game 1 and
   the top five in Game 2 either think about the other players or deliberately dodge
   the crowd. AI samplers won all 200
   Game 1 re-runs.
5. **In Game 2, the crowd's composition decides the best shape.** Model 3's crowd had
   more Opus-style "castle 3 + castle 5" bets, and the best reply moved to castles
   1+2+5. That is the rock-paper-scissors finding from model 2, seen in real data: the
   right Game 2 move depends on which popular plan is most common. That is why the
   final answer uses the shape that holds up across all three models, not the
   500-player one.
6. **A big AI crowd makes winning a lottery as well as a skill.** With 150 AI tickets,
   a handful of lucky raw AI answers won half of the Game 2 re-runs. The type that
   wins *on average* (AI sampler) and the type that most often *finishes first* are no
   longer the same.

## Critical findings (all models)

1. **The "optimal" answer everyone quotes, 7/13/20/27/33, is a trap.** It's the
   *average* of the perfect random strategy, not the strategy. It loses 14-1 to
   3/14/21/28/34 and finishes in the bottom quarter in all three models.
2. **The perfect (Nash) strategy only guarantees average.** Against it, every sensible
   allocation scores exactly 7.5. Real points come from exploiting how real people play.
3. **Most applicants using AI makes the field predictable.** Haiku gave the textbook
   answer 7/10 times in model 2 and 28/50 times in model 3. Sonnet and Opus mostly bid
   "one more than a round number" on castles 3-5. That over-fights castle 3 and leaves
   castle 2 cheap, which is exactly what the final picks exploit.
4. **Pasting the prompt into an AI and submitting the answer is a mid-table result**
   (about 49th of 100 in Game 1 and 52nd in Game 2; 239th and 258th of 500 in
   model 3). Which AI matters: Opus averaged about 5.8-5.9 in Game 2, against 2.3-2.7
   for Sonnet and Haiku.
5. **Metastrategy wins.** Every top strategy type thinks about the *other* players.
   The best one was to ask the AI several times to see what AI users will submit,
   then counter it.
6. **Concentrate and avoid round numbers.** These were the strongest predictors of a
   high score in both games and in both simulations. Spreading out is the most
   reliable way to lose.
7. **Game 2 is rock-paper-scissors.** Every popular plan has a counter (3+4 beats
   "go big on 5", 1-2-3 beats 3+4, 5+1 beats 1-2-3, ...). The robust move takes the
   castles the popular plans under-defend, by margins nobody else bothers with. Model 3
   showed this directly: a crowd with more "3+5" bets moved the best reply from
   castles 2+4 to castles 1+2+5.

## Repository layout

```
Trial.txt                      the challenge
README.md                      this file (final answer + comparison + model 3)
compare_strategies.py          scores every pick in every model, finds the consensus
results/comparison.json        output of compare_strategies.py
shared/castle.py               exact game rules + best-response search (used by all)
shared/chart_style.py          chart styling
strategy1_probability/         Strategy 1: analysis.py, EXPLAINED.md, CLAUDE.md, results/
strategy2_simulation/          Strategy 2: population.py, run_simulation.py, collect_ai_contestants.py,
                               contestants/ (30 real AI answers + the 100), EXPLAINED.md, CLAUDE.md, results/
model3_simulation_500/         Model 3: contestants/ (150 real AI answers, their prompts, the 500),
                               results/, CLAUDE.md (code is shared with strategy2_simulation/)
```

## Reproduce

Requires Python 3.11+ with `numpy` and `matplotlib`.

```bash
python strategy1_probability/analysis.py        # ~12 min   (--quick for ~4 min)
python strategy2_simulation/run_simulation.py   # ~4 min    (--quick for ~1 min)
cd strategy2_simulation && python run_simulation.py --players 500 \
    --ai-file ../model3_simulation_500/contestants/ai_contestants.json \
    --out ../model3_simulation_500 && cd ..     # ~12 min   (model 3)
python compare_strategies.py                    # ~4 min    (~1.5 min without model 3)
python strategy1_probability/make_charts.py
python strategy2_simulation/make_charts.py
python strategy2_simulation/make_charts.py model3_simulation_500
```

All runs are seeded, so the numbers above reproduce exactly. The scoring engine was
checked against brute-force reference implementations:

- 3,000 random four-player groups matched exactly.
- The Game 1 knapsack matched an exhaustive search over all 4,598,126 allocations.
- Every simulated group pays out exactly 15 points in total.

## Caveats

Nobody can see the real applicant pool. The 180 AI answers (30 in model 2, 150 in
model 3) are real but come only from Claude models. Real applicants also use ChatGPT,
Gemini and others. The modelled people (70 in model 2, 350 in model 3) and Strategy
1's field priors are informed models, not data. Both final picks stayed well above
average in every variation tested (different AI shares, 0-50% metastrategists, 64
probability scenarios), but none of this is a guarantee. Game 2 in particular
depends on which popular plan is most common, as model 3 shows.
