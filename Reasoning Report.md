# Reasoning Report

**Submitted allocation (castles 1 to 5):** Game 1 `2 / 16 / 1 / 38 / 43`, Game 2 `1 / 37 / 0 / 62 / 0`

**Methodology.** I solved the challenge three independent ways and only trusted
answers that held up in all of them. First, a probability model: I found the
perfect (Nash equilibrium) strategy and showed that it only guarantees an average
score. Then I built a level-by-level "I think that you think" ladder and chose the
allocation with the best average result over 64 possible fields for Game 1 and 36
for Game 2. Second, a simulation of 100 individual applicants. Because I expected
most applicants to use AI, 30 of them were real answers from fresh Claude Haiku,
Sonnet and Opus chats given the challenge text. 20 more were people who tweaked an
AI answer, 15 were metastrategists who reason about everyone else, and 35 solved it
by hand. I played both games exactly by the rules: every head-to-head matchup in
Game 1, and 20,000 random four-player groupings in Game 2. I re-drew the whole crowd
200 times, then searched for the best reply to it. Third, I rebuilt that simulation
from scratch with 500 applicants, including 150 new AI answers, to check that the
result wasn't a fluke of one small sample. Finally, I scored every candidate
allocation inside all three models and picked the one with the best combined result.

**Why Game 1 is `2/16/1/38/43`.** In Game 1 my score is the average over every
matchup, so each castle is a separate bet: its points times the share of opponents I
outbid there. The simulations showed that an AI-heavy field is predictable. The most
common answer is the "textbook" 7/13/20/27/33 (Haiku gave it in 35 of its 60
answers), and most other answers cluster on "one more than a round number". Half to
60% of the crowd sends 20-23 soldiers to castle 3, which makes it the most overpaid
castle for its value, so I concede it with 1 soldier. Castle 2 is starved (the median
bid is about 11), so 16 wins it cheaply against more than 80% of opponents. 38 and 43
sit just above the clusters on castles 4 and 5, whose median bids are about 30 and 35.
This pick averages 10.3-10.4 points per matchup, against an average of 7.5. It beat
every single applicant in 74% of the 100-player crowds and in 94.5% of the 500-player
crowds. The 500-player rerun independently landed one soldier away (`3/16/1/37/43`).
The probability model's own pick scores 0.31 points better inside that model, but it
almost never tops a realistic AI-heavy crowd. I traded that small amount for a much
higher chance of finishing first.

**Why Game 2 is `1/37/0/62/0`.** Game 2 plays very differently. With three
opponents, a castle only counts if I have the top bid of the four. The 9/4/2/0 payout
also rewards first place heavily, so spreading soldiers out wins nothing. Most
players fight over castle 5 or the castle 3-4-5 block, so I take the two castles they
under-defend, by margins few will match: 62 on castle 4 and 37 on castle 2. That's
6 points. The remaining castles (5, 3 and 1) usually split between different
opponents, so 6 points usually finishes first. The probability model and the
100-player simulation reached this castle 2 + castle 4 shape independently, and the
probability model has no simulated people at all. The 500-player rerun preferred
castles 1+2+5 (`7/25/0/0/68`), because its crowd had more Opus-style castle 3 +
castle 5 bets. That disagreement shows that Game 2 is rock-paper-scissors: the best
move depends on which popular plan is most common. So I chose the allocation that is
strongest across all three models, not the one that is best in any single model. It
finishes 1st in about 61-84% of its groups depending on the model. Across the three
models it averages 7.15, against 6.78 for the alternative and 3.75 for an average
applicant. The main limit of this reasoning is that the real AI answers come only
from Claude models, and the other applicants are informed models rather than real
data. Even so, both picks stayed well above average in every variation I tested.
