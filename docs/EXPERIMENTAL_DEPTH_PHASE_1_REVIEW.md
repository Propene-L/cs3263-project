# Experimental Depth Review — Experiment 1

## Scope and provenance

This review covers only **Experiment 1: multi-round uncertainty reduction**.
The repository rule requiring human review between phases prevents beginning
the difficulty analysis or interaction-rule ablation in the same phase.

The analysis reads the committed `evaluation/phase_1_1_results.json` artifact
without rerunning selectors or modifying scenarios. The input SHA-256 is
`aef7cf9dbf3993a5d03c3801275a04037be0a418ccc506db7b32119a6f95d2e0`.
The source artifact contains 65 controlled real-ArtGraph scenarios: 57 are
initially solvable, three initially resolved, and five initially unsolvable.

All percentages below use the same 57 initially solvable scenarios. Round 0 is
the post-replay, pre-question state. For the fixed-cohort mean, a scenario's
terminal state is carried forward after resolution or early stopping. The CSV
also reports the mean over the smaller subset that actually received a
question in each round, with that subset's question count. This prevents the
changing subset from being mistaken for a fixed-denominator trajectory.

No resampling or sensitivity analysis is performed, so the requested
resampling seed `32631202` is not invoked. The historical random-selector run
retains its recorded seed `3263`; this analysis does not regenerate it.

## Results

| Method | Resolved after rounds 0 / 1 / 2 / 3 | Fixed-cohort mean active hypotheses after rounds 0 / 1 / 2 / 3 | Mean eliminated per actual question (all 65) |
|---|---:|---:|---:|
| Compositional Prolog | 0 / 15 / 28 / 44 (0 / 26.32 / 49.12 / 77.19%) | 4.140 / 2.649 / 1.789 / 1.316 | 1.258 |
| Single-rule Prolog | 0 / 15 / 16 / 27 (0 / 26.32 / 28.07 / 47.37%) | 4.140 / 3.456 / 2.825 / 2.246 | 0.771 |
| Raw attribute contrast | 0 / 11 / 22 / 35 (0 / 19.30 / 38.60 / 61.40%) | 4.140 / 2.842 / 2.000 / 1.474 | 1.101 |
| Random eligible | 0 / 1 / 1 / 1 (0 / 1.75 / 1.75 / 1.75%) | 4.140 / 4.018 / 3.877 / 3.754 | 0.126 |
| Exact Python | 0 / 15 / 28 / 44 (0 / 26.32 / 49.12 / 77.19%) | 4.140 / 2.649 / 1.789 / 1.316 | 1.258 |

The final cumulative totals reproduce the committed headline values exactly:
44/57, 27/57, 35/57, 1/57, and 44/57 in the table order. Compositional Prolog
and single-rule Prolog resolve the same 15 cases in the first round, but the
compositional method reaches 28 rather than 16 by round 2 and 44 rather than 27
by round 3. Its final advantage is 17 scenarios, or 29.82 percentage points.
It also leaves 1.316 rather than 2.246 active hypotheses at the fixed
three-question horizon.

The comparison does not establish an advantage over conventional exact
optimization. Exact Python follows the declared objective and tie-break and
therefore overlaps compositional Prolog at every plotted point. The experiment
instead isolates the advantage of considering the full active hypothesis set
over the single-rule and raw-contrast heuristics under the controlled model.

Across all 65 scenarios, the stop counts were:

| Method | Resolution (including 3 initially resolved) | No discriminative pair | Round limit | Error |
|---|---:|---:|---:|---:|
| Compositional Prolog | 47 | 5 | 13 | 0 |
| Single-rule Prolog | 30 | 5 | 30 | 0 |
| Raw attribute contrast | 38 | 5 | 22 | 0 |
| Random eligible | 4 | 5 | 56 | 0 |
| Exact Python | 47 | 5 | 13 | 0 |

## Real proof example

In `controlled_pair_01`, compositional Prolog selected `ag_10472` (Study for
The Cellist) and `ag_11014` (Boy by the Water). The controlled partition maps
`h_musical_subject` to `prefer_a` and `h_nature_subject` to `prefer_b`. The
structured proof records selection rule
`r_select_max_discrimination_then_balance`, response assumption
`a_recorded_positive_support_comparison`, and imported ArtGraph fact IDs
`agf_8e49e33270d2ff0f08d3` and `agf_b9548b8d9dc380a4b674`. The exported facts
identify both as `about` relations from the
`https://www.gennarovessio.com/artgraph-schema#about` source predicate in the
`artgraph_v1_phase_1_clarification` snapshot.

## Generated artifacts

- `evaluation/depth_analysis/multi_round_resolution.csv`
- `evaluation/depth_analysis/multi_round_trajectory.csv`
- `evaluation/depth_analysis/fig_multi_round_resolution.png`
- `evaluation/depth_analysis/fig_multi_round_resolution.svg`

The two-panel figure is generated from the saved trajectory CSV, not from
hard-coded plotting values. The left panel shows cumulative resolution; the
right panel shows carried-forward fixed-cohort state size. Actual per-round
question counts remain in the CSV.

## Reproduction and verification

Environment: Python 3.12.10, Matplotlib 3.11.2, and SWI-Prolog 10.0.2 on
Windows x64.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m evaluation.depth_analysis.run_all
.\.venv\Scripts\python.exe -m pytest -q tests\test_depth_analysis.py
.\.venv\Scripts\python.exe -m pytest -q
$tests = Get-ChildItem -LiteralPath 'logic\tests' -Filter 'test_*.pl' | Sort-Object Name
foreach ($test in $tests) {
  & .\.tools\swipl\bin\swipl.exe -q -s $test.FullName -g run_tests -t halt
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

Observed results:

- Dedicated depth-analysis tests: **5 passed**.
- Full Python suite: **137 passed** in 19.47 seconds.
- All six Prolog test files: **42 passed**.
- Headline validation: all five final resolution counts and the denominator 57
  reproduced exactly.

## Limitations and licensing

- Responses are generated by the declared recorded-positive-support model,
  not by museum visitors. The results do not demonstrate human preference
  accuracy, educational usefulness, or real-world information gain.
- Compositional Prolog and the independent evaluator share the formal response
  semantics. This is an implementation and policy comparison, not external
  validation of those semantics.
- Terminal-state carry-forward is used only for the labelled fixed-cohort
  trajectory. It is not counted as an additional question or observation.
- Exact Python's identical trajectory is a negative result: the logical
  implementation supplies proofs and policy transparency, but not a superior
  numerical objective for this task.
- The ArtGraph v1.0 Zenodo record's displayed licence field was blank during
  the Phase 0 audit. No bulk RDF or images are added or redistributed here.

## Review gate

Human review is required before beginning **Experiment 2: performance by
scenario difficulty**. Review should confirm the fixed-cohort definition,
carried-forward plotting convention, stop-reason grouping, and whether the
all-scenario or fixed-cohort elimination-per-question column should be the
primary report value. Historical evaluation JSON and CSV files remain
unchanged.
