# Model 3: the Strategy 2 simulation rerun independently with 500 players

Same model as `../strategy2_simulation/`, scaled 5x and rebuilt from scratch. It
reuses only the game rules, the 10 prompts, and the archetype definitions. Every
result and every random draw is fresh. Nothing from the 100-player run (its AI
answers, its metastrategist library, or its picks) is an input here.

## Contents

| Path | What |
|---|---|
| `contestants/prompts/*.txt` | The 10 prompt files the AI contestants read: 5 framings x 2 wordings, identical in text to model 2's prompts. |
| `contestants/ai_contestants.json` | **150 fresh real AI contestants**, each a new Claude subagent (Haiku, Sonnet, Opus), with full reply, prompt and an isolation check. |
| `contestants/population.json` | The baseline 500 contestants with allocations, reasoning and scores. |
| `results/simulation_results.json` | All outputs: same keys as model 2, except `entrant_501` instead of `entrant_101`. |
| `results/leaderboard.csv`, `results/model_fields.npz`, `results/fig_*.png` | Same formats as model 2. |

## How it was produced

1. **AI contestants.** IDs 1-150 = 5 framings x 3 models x 2 wordings x 5 repeats
   (`id = 1 + ((framing*3 + model)*2 + wording)*5 + repeat`). Each subagent got a
   one-line instruction to Read exactly one prompt file and follow it. That kept the
   orchestration small and kept the agents out of the repo. Repeating a prompt five
   times mirrors many people pasting the same text into an AI.
   The harvest checks that each agent made exactly one Read of its own prompt file
   (`isolation_ok`).
   ```
   python ../strategy2_simulation/collect_ai_contestants.py <session>/subagents \
       --prefix "M3 AI contestant" --id-prefix M3-AI \
       --out contestants/ai_contestants.json --prompts-dir contestants/prompts
   ```
2. **Simulation.** This is the same code as model 2 with `--players 500`. Every archetype
   count is scaled x5 by `scaled_mix(500)`: 150 real AI, 100 AI-tweakers,
   75 metastrategists and 175 by-hand humans. The metastrategist library has 45
   decisions per expensive type. The sensitivity sweeps scale with N (metastrategist
   seats 0/25/75/150/250).
   ```
   python ../strategy2_simulation/run_simulation.py --players 500 \
       --ai-file contestants/ai_contestants.json --out .          # about 10-15 min
   python ../strategy2_simulation/make_charts.py .
   ```
3. **Cross-model comparison.** `python ../compare_strategies.py` picks this folder up
   automatically and adds model-3 columns plus a 3-model consensus.

## Gotchas

- One contestant (#092) failed on a usage limit and was relaunched. The collector
  keeps the transcript that contains an answer.
- Contestants never see each other or the repo, but they are all Claude models.
  As in model 2, ChatGPT/Gemini answers are not represented.
- Seeds are the same as model 2 (`--seed 7`). The populations still differ because
  the player count, the AI answers and the library all differ.
