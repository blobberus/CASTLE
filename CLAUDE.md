# CASTLE

The Castle Challenge (`Trial.txt`), solved two independent ways, then compared. Strategy 2
was then rerun from scratch at 500 players (model 3).

- `strategy1_probability/`: probability model, Nash equilibrium, level-k ladder, Bayes-robust pick. Has its own `CLAUDE.md`.
- `strategy2_simulation/`: 100 simulated applicants (30 real AI answers), tournament, 101st-entrant best response. Has its own `CLAUDE.md`.
- `model3_simulation_500/`: data and results only. Strategy 2's code run with `--players 500` on 150 fresh real AI answers. Has its own `CLAUDE.md`.
- `compare_strategies.py`: scores picks in every model and computes the consensus final answer (`results/comparison.json`). The final answer is the models 1+2 consensus. Model 3 adds columns and a separate 3-model consensus without changing any model 1-2 number (it uses its own RNG stream).
- `shared/castle.py`: the only implementation of the game rules. Both strategies import it, so change rules in one place only.

The final answer and headline findings are in `README.md`. Each strategy's
`EXPLAINED.md` is the plain-English version for a non-technical reader. Model 3's
write-up is the "Model 3" section of `README.md`. Keep these in sync with the results
JSON after re-running anything.

Order to re-run everything: `strategy1_probability/analysis.py`, then
`strategy2_simulation/run_simulation.py` and the model 3 run (see
`model3_simulation_500/CLAUDE.md`). These three are independent. Then run
`compare_strategies.py`, then the `make_charts.py` scripts (Strategy 2's takes the
model 3 folder as an argument).

Sanity checks after touching `shared/castle.py`:
- The Game 1 round-robin mean must be 7.5.
- The Game 2 mean payout and mean castle points must be 3.75.
- The DP best response must match the brute-force top of `game1_best_response(P, top=k)`.
