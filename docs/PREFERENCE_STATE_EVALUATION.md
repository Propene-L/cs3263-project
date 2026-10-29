# Phase 1.2 Preference-State Evaluation

## Correction status

The results below headed **Historical v1** are the original record from commit
`28e77c98614ca35a23bd40f0b1ce56e01cfb8cd2`. Those files and hashes remain
unchanged. The original `state_explanation_accuracy` was explanation coverage:
it counted a case correct when the gold explanation appeared anywhere among
the outputs, even alongside unsupported explanations. Candidate targets also
occupied position 1 in all 24 source scenarios before v2 randomized them.

Corrected v2 separates regression from robustness cases, records candidate
order and seed, reports precision/recall and primary accuracy, and performs a
real clarification state update. Raw corrected results are in
`evaluation/preference_state_corrected_results.json`; compact results are in
`evaluation/preference_state_corrected_summary.csv`.

### Corrected robustness results (32 authored scenarios / 36 worlds)

| Method | Coverage | Primary accuracy | Explanation P/R | False interaction | False atomic | Action type | Top-1 | Recall@3 | Precision@3 | Mean runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Positive accumulation | 57.81% | 25.00% | 25.13% / 57.81% | 0% | 37.37% | 40.63% | 48.44% | 36.07% | 30.73% | 17.96 ms |
| Signed additive | 54.69% | 0% | 29.69% / 54.69% | 0% | 29.69% | 40.63% | 53.13% | 43.64% | 38.02% | 18.95 ms |
| Atomic Prolog | 57.81% | 0% | 25.13% / 57.81% | 0% | 37.37% | 40.63% | 48.44% | 36.07% | 30.73% | 613.04 ms |
| Compositional Prolog | 96.88% | 59.38% | 62.76% / 84.38% | 1.56% | 34.38% | 96.88% | 82.81% | 64.40% | 63.02% | 604.66 ms |
| Interaction Python | 96.88% | 59.38% | 62.76% / 84.38% | 1.56% | 34.38% | 96.88% | 82.81% | 64.40% | 63.02% | 17.92 ms |

All five offline methods produced valid constrained decisions. Corrected
Prolog and interaction Python were identical in every base and permutation
run. This means the quality improvement belongs to the richer representation
and decision policy; the Prolog implementation adds independently checkable
proof provenance, while Python is about 34 times faster in this subprocess
configuration.

On the held-out robustness split, compositional Prolog/Python achieved 100%
coverage, 67.86% precision, 85.71% recall, 50% primary accuracy, 82.14% top-1,
65.03% Recall@3, 58.33% Precision@3, and 100% action-type accuracy. The split
uses a tag+style conjunction schema while development uses genre+style, but it
shares the vocabulary and candidate pool, so this is reported as in-pattern
generalization rather than out-of-distribution evidence.

### Closed-loop clarification

Compositional Prolog/Python asked nine questions on robustness cases. The
declared response model made all nine informative. Averaged over possible
worlds, primary accuracy increased by 61.11 percentage points, explanation
precision by 22.22 points, recall by 33.33 points, and top-1 recommendation
relevance by 38.89 points. Top-1 relevance after clarification was 88.89%; all
actual post-clarification recommendations were relevant. The response model is
an exact profile-membership oracle, so these are controlled transition tests,
not evidence about how people answer museum questions.

The old `clarification_useful_at_1` is retained only in the historical result.
Corrected output calls it `CleanProbe@1` and keeps it separate from the
closed-loop metrics.

### Recommendation interpretation

The original 34.72% interaction Precision@K equality came from candidate-set
geometry: each interaction case had one relevant item, `K` was 2 for the
flagship and 3 otherwise, and both methods placed that one item somewhere in
the top K. Better top-1 order could not improve precision when the same single
relevant item remained inside the cutoff. Corrected v2 reports top-1,
Recall@K, Precision@K, Hit@K, and irrelevant-action rate separately. It does
not equate a top-1 gain with better whole-ranking quality.

## Scope and execution

Phase 1.2 evaluates whether each method can independently build a visitor
state from multi-turn likes/dislikes and use it to rank a relevant next action.
It does not evaluate human preference accuracy and does not begin frontend or
Phase 2 work.

Commands:

```powershell
.\.venv\Scripts\python.exe scripts\build_preference_state_benchmark.py
.\.venv\Scripts\python.exe -u evaluation\evaluate_preference_state.py
.\.venv\Scripts\python.exe scripts\build_preference_state_human_review.py
.\.venv\Scripts\python.exe -m pytest -q
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_pilot.pl -g run_tests -t halt
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_phase_0_5_pilot.pl -g run_tests -t halt
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_interest_poc.pl -g run_tests -t halt
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_clarification.pl -g run_tests -t halt
& .\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_preference_state.pl -g run_tests -t halt
```

Raw results are in `evaluation/preference_state_results.json`; the compact
table is in `evaluation/preference_state_summary.csv`.

The final local verification completed with 44 Python tests and 32 Prolog
tests passing. `compileall` and `git diff --check` also completed cleanly.

## Historical v1 controlled results

| Method | State explanation accuracy | Atomic accuracy | Interaction accuracy | Relevant@1 | Clarification useful@1 | Interaction recommendation Relevant@1 | Mean runtime |
|---|---:|---:|---:|---:|---:|---:|---:|
| Positive attribute accumulation | 50% | 100% | 0% | 79.17% | 0% | 83.33% | 0.115 ms |
| Signed additive atomic | 50% | 100% | 0% | 50% | 8.33% | 0% | 0.221 ms |
| Existing atomic Prolog | 50% | 100% | 0% | 79.17% | 0% | 83.33% | 409.907 ms |
| Compositional Prolog | 100% | 100% | 100% | 100% | 100% | 100% | 406.592 ms |
| Direct frontier LLM | Not executed | — | — | — | — | — | — |

The aggregate `Relevant@3`/precision columns use
`K = min(3, candidate-count)` for the two flagship cases. Relevant@3 is 100%
for compositional, positive accumulation, and atomic
Prolog; it is 54.17% for signed additive. The compositional method's mean
primary component precision and recall are both 100%. Results are controlled
latent-profile consistency, not human truth.

## Flagship regression

Positive accumulation ranks:

```text
ag_8415 Adam and Eve: 3
ag_20804 Baby:        2
```

Signed additive ranks:

```text
ag_8415 Adam and Eve: 2
ag_20804 Baby:        0
```

Existing atomic Prolog likewise ranks Adam and Eve first. Compositional Prolog
derives:

```json
{
  "kind": "all_of",
  "components": ["h_expressionist_style", "h_portrait_genre"],
  "status": "interaction_candidate"
}
```

and ranks `ag_20804` Baby at 1000 over `ag_8415` Adam and Eve at 0. The proof
cites observations `obs_like_albert`, `obs_dislike_bird`, and
`obs_dislike_boy`; rule `r_component_rejection_suggests_interaction`;
assumptions `a_bounded_recorded_support_contrast` and
`a_component_rejection_can_suggest_interaction`; the four interaction input
fact IDs; and Baby's two supporting fact IDs. `not_recorded` components are
explicitly labeled as bounded-snapshot conditions.

In the contrastive flagship, positive accumulation and atomic Prolog select
high-overlap `ag_42361` Adolf Loos. Signed additive and compositional Prolog
select clean musical probe `ag_14531` Three musicians.

## Required analysis questions

### 1. Does compositional reasoning improve over positive accumulation?

Yes under these controlled profiles. Exact state explanation rises from 50%
to 100%, Relevant@1 from 79.17% to 100%, and clarification usefulness from 0%
to 100%. Positive overlap often retrieves a conjunction-relevant artwork by
chance, explaining its relatively high recommendation Relevant@1 despite
never representing the conjunction.

### 2. Does it improve over signed additive atomic rules?

Yes, strongly on interaction cases. Signed cancellation removes components
that occur once in both liked and disliked examples and therefore cannot
represent the conjunction. Its interaction recommendation Relevant@1 is 0%.
It succeeds on the contrastive Cellist flagship but fails all selected
interaction recommendations.

### 3. Which families produce the largest differences?

The interaction family produces the largest state and recommendation gap.
The contrastive family produces the largest clarification-usefulness gap
between positive-only matching and contrastive compositional reasoning.

### 4. Are conjunctions useful or merely extra parameters?

They are operationally necessary for the controlled `all_of` relevance
function: atomic components cannot exclude component-only distractors. However,
the benchmark deliberately searches for the rule's pattern, so this result
does not establish that real visitors possess conjunction preferences. Human
review or independently collected interaction labels remain necessary.

### 5. Does state accuracy translate to next-action relevance?

Within this benchmark, yes: 100% exact state accuracy coincides with 100%
Relevant@1, recommendation Relevant@1, and clarification usefulness. The
positive baseline demonstrates that action relevance can occasionally be high
without a correct explanation, so explanation and action metrics must remain
separate.

### 6–7. Where does direct LLM help or violate constraints?

Unknown. No API key or model was configured, so no genuine requests were made
and no results were fabricated. The task-specific adapter supplies natural
history, allowlisted hypotheses/candidates, and ArtGraph evidence, while
withholding latent profiles, labels, Prolog outputs, and baseline outputs. It
validates components and artwork IDs and records raw responses and token usage
when genuinely executed. Its strict `text.format` schema and refusal handling
follow the official OpenAI
[Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

Configuration for a smoke run:

```powershell
$env:PREFERENCE_STATE_LLM_PROVIDER = "openai"
$env:PREFERENCE_STATE_LLM_MODEL = "<documented model or snapshot>"
$env:OPENAI_API_KEY = "<secret>"
.\.venv\Scripts\python.exe -m evaluation.evaluate_preference_state_corrected `
  --subset development --smoke --run-direct-llm `
  --output-prefix preference_state_llm_smoke `
  --llm-output preference_state_llm_smoke_results.json
```

Run the full held-out subset only after reviewing the smoke output. The key is
never written or echoed.

### 8. Runtime and complexity

Python baselines finish below one millisecond. Both Prolog modes average about
400 ms because fresh-process startup and fact loading dominate this small
state rule set. The compositional joins add search and proof complexity, but
the observed difference from atomic Prolog is within local timing variation.
The cost is orders of magnitude above direct Python matching while providing
structured provenance and explicit assumption boundaries.

### 9. Which conclusions depend on controlled assumptions?

All accuracy and relevance conclusions depend on recorded-support labels, the
allowed interaction schemas, the component-rejection assumption, and the
constructed candidate universes. Missing RDF, multi-feature aesthetics, and
real visitor responses could reverse rankings. No result is human preference
accuracy.

## Historical v1 failures and then-proposed gate

Positive accumulation fails the two flagships and several discovered cases by
favoring shared high-overlap distractors. Signed additive fails the flagship
interaction and every selected interaction recommendation because shared
components cancel. Atomic Prolog reproduces the positive-only limitation.

Compositional Prolog has no controlled failures in this deliberately matched
benchmark; that is itself a limitation and a reason not to overclaim. The next
gate is blinded human relevance review using
`evaluation/preference_state_human_review.csv`, followed by an independently
specified robustness set with noisy/missing/multiple-interaction histories.
That robustness set is now implemented in v2. Human judgments remain the next
gate; the corrected method-blind sheet is
`evaluation/preference_state_corrected_human_review.csv`.
