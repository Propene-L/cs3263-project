# Phase 1.1 Evaluation Review

## Scope and research claim

Phase 1.1 hardens the active preference-clarification experiment only. It does
not implement Phase 2, a frontend, or a broader recommendation policy. The
controlled task remains: choose an eligible artwork pair whose declared
positive-support predictions distinguish active, provisional visitor-interest
hypotheses.

All response outcomes in this review are formal simulations. They are **not**
measurements of human artwork preference, museum usefulness, or psychometric
accuracy.

## Corrected design

Every method now receives the same initial observations, hypothesis set,
candidate artworks, viewed/rejected constraints, corrected question history,
hidden simulated hypothesis, three-round limit, transition semantics, and
stopping rules. The method-independent evaluator in
`evaluation/shared_simulator.py` computes predictions and updates:

- `prefer_a` eliminates only hypotheses predicting `prefer_b`;
- `prefer_b` eliminates only hypotheses predicting `prefer_a`;
- `unsure` and `neither` eliminate none;
- unknown predictions never justify elimination;
- previously asked artwork pairs are unavailable;
- a correction replaces the prior response before responses are replayed.

Question selection and response-model validity are recorded separately. A
method may select an eligible-looking pair that is not formally
discriminative, and the evaluator records that selection without calling it
valid.

The five offline methods are compositional Prolog, single-rule Prolog, raw
attribute contrast, random eligible pair, and an exact-objective Python
optimizer. The Python optimizer uses the same objective and stable-ID tie
break as compositional Prolog, but never calls Prolog or consumes its proof.

## Benchmark composition

The benchmark contains 65 real-ArtGraph controlled scenarios:

| Category | Count |
|---|---:|
| Preserved Phase 1 regression scenarios | 20 |
| New Phase 1.1 scenarios | 45 |
| Initially solvable | 57 |
| Initially unsolvable | 5 |
| Initially resolved | 3 |
| Initially solvable with at least three hypotheses | 43 |
| New development subset | 26 |
| New held-out subset | 19 |

The 45 additions include 39 multi-hypothesis cases, four deliberately
unsolvable candidate universes, two initially resolved cases, correlated
Expressionism movement/style evidence, broad oil-medium evidence, reduced
candidate universes, viewed and rejected artworks, rejected hypotheses,
unknown predictions, an explicitly corrected response, `unsure`/`neither`
non-reductions, and two cases where the hidden hypothesis is already absent.
Scenario expectations are computed from the declared response model and
exported evidence, never from Prolog recommendations.

The original 20-scenario bytes are preserved at
`evaluation/clarification_scenarios_phase_1.jsonl`; the original Phase 1 result
file is unchanged.

## Executed results

Command:

```powershell
.\.venv\Scripts\python.exe -u evaluation\evaluate_clarification.py --max-rounds 3
```

The completed run is in `evaluation/phase_1_1_results.json`. The table below
uses successful resolution **after interaction** over the 57 initially
solvable cases; the three initially resolved cases are reported separately.

| Method | Valid selected questions | Correctly resolved after interaction | Mean distinguished pairs/question | Mean selector runtime |
|---|---:|---:|---:|---:|
| Compositional Prolog | 100% | 44/57 (77.19%) | 2.2109 | 829.858 ms |
| Single-rule Prolog | 100% | 27/57 (47.37%) | 1.3786 | 626.745 ms |
| Raw attribute contrast | 89.13% | 35/57 (61.40%) | 2.0797 | 19.830 ms |
| Random eligible | 22.99% | 1/57 (1.75%) | 0.3793 | about 0.13 ms |
| Exact-objective Python | 100% | 44/57 (77.19%) | 2.2109 | 24.638 ms |
| Direct LLM | Not executed | — | — | — |

The direct-LLM row is unexecuted because no provider endpoint/model/key was
configured. Mock adapter tests are engineering tests and are not counted as
experimental results.

### Exact Python versus Prolog

All 128 compositional Prolog selections were identical to the independent
Python optimum, including tie-breaking. All 268 checked compositional and
single-rule rounds agreed with the shared evaluator about the active
hypothesis set. Identical selections are expected: the comparison isolates
implementation, proof, and runtime trade-offs rather than a mathematically
different objective.

At 112 candidates and six active hypotheses, the focused scaling run measured
about 55.5 ms for exact Python versus 1,226.1 ms for compositional Prolog. The
full benchmark's means differ because hypothesis/candidate counts and early
stopping vary. Prolog additionally pays fresh-process, JSON, proof-building,
and fact-loading costs.

## What compositional selection changes

Compositional Prolog resolved many multi-hypothesis cases that single-rule did
not, including `controlled_multi_16` and numerous `phase_1_1_multi_*` cases.
It reduced the mean active set after rounds 1/2/3 to approximately
2.65/2.07/1.62, versus 3.46/3.48/2.73 for single-rule Prolog. This is evidence
for the multi-hypothesis objective under the formal simulator, not evidence
that visitors would prefer those questions.

There is no selection advantage over exact Python; the latter is much faster.
For the original two-hypothesis cases, single-rule and compositional selection
usually converge, so the added logic offers little clarification benefit and
costs runtime.

Compositional selection can also do worse in an individual trajectory.
`phase_1_1_multi_021` is the clearest case: the compositional optimum received
two `unsure` responses from the hidden formal hypothesis and ended with two
hypotheses, while single-rule happened to resolve the hidden hypothesis in
three rounds. Maximizing aggregate distinction does not maximize information
for every possible hidden hypothesis.

## Real proof example

For `controlled_pair_01`, Prolog selected `ag_10472` (Study for The Cellist)
and `ag_11014` (Boy by the Water). The partition was musical subject →
`prefer_a`, nature subject → `prefer_b`. The structured proof cites selection
rule `r_select_max_discrimination_then_balance`, response assumption
`a_recorded_positive_support_comparison`, and imported fact IDs
`agf_8e49e33270d2ff0f08d3` and `agf_b9548b8d9dc380a4b674`.
Regression tests verify that every proof fact ID exists in the exported
ArtGraph evidence catalog.

## Limitations and failure analysis

- The simulator and symbolic model share the same idealized positive-support
  assumption. Agreement verifies the formal implementation, not visitor truth.
- A visitor may react to composition, color, familiarity, mood, or interacting
  features absent from the singled-out hypothesis.
- Missing ArtGraph triples are unknown. They are never evidence that an
  artwork lacks an attribute.
- Artworks may have multiple styles, subjects, or media; a one-attribute
  response can be ambiguous.
- Broad oil-medium support can be formally useful but visually uninformative.
- `unsure` and `neither` do not reduce the state, so even an optimal aggregate
  question may use a round without progress.
- Correlated movement/style hypotheses can remain redundant.
- The hidden-hypothesis-absent cases correctly lower retention to 96.92%; no
  selector can recover a candidate hypothesis it was not given.
- Text-only human review has not been performed. The supplied sheet evaluates
  wording and factual basis, not genuine visual preference.
- The ArtGraph v1.0 Zenodo record's displayed licence field was blank during
  the Phase 0 audit. Bulk RDF and images are not redistributed.

## Reproducibility and review gate

```powershell
.\.venv\Scripts\python.exe scripts\build_clarification_benchmark.py
.\.venv\Scripts\python.exe -u evaluation\evaluate_clarification.py --max-rounds 3
.\.venv\Scripts\python.exe -m evaluation.benchmark_clarification_complexity
.\.venv\Scripts\python.exe scripts\build_clarification_human_review.py
.\.venv\Scripts\python.exe -m pytest -q
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_clarification.pl -g run_tests -t halt
```

Human review is the next gate. Do not begin Phase 2 until the benchmark design,
formal interpretation, and unfilled review sheet have been reviewed.
