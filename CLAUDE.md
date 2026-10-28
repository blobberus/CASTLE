# CASTLE

The Castle Challenge (`Trial.txt`), solved two independent ways, then compared.

- `strategy1_probability/`: probability model, Nash equilibrium, level-k ladder, Bayes-robust pick. Has its own `CLAUDE.md`.
- `strategy2_simulation/`: 100 simulated applicants (30 real AI answers), tournament, 101st-entrant best response. Has its own `CLAUDE.md`.
- `compare_strategies.py`: scores picks in both models and computes the consensus final answer (`results/comparison.json`).
- `shared/castle.py`: the only implementation of the game rules. Both strategies import it, so change rules in one place only.

The final answer and headline findings are in `README.md`. Each strategy's
`EXPLAINED.md` is the plain-English version for a non-technical reader. Keep these
in sync with the results JSON after re-running anything.

Order to re-run everything: `strategy1_probability/analysis.py`, then
`strategy2_simulation/run_simulation.py` (these two are independent), then
`compare_strategies.py`, then both `make_charts.py`.

Sanity checks after touching `shared/castle.py`:
- The Game 1 round-robin mean must be 7.5.
- The Game 2 mean payout and mean castle points must be 3.75.
- The DP best response must match the brute-force top of `game1_best_response(P, top=k)`.
