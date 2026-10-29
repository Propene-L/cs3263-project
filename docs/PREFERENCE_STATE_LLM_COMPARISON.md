# Phase 1.2 Direct-LLM Comparison

## Status

The direct-LLM evaluation was executed on 2026-10-29 through the supplied
SOCLAAS Responses-compatible endpoint with its `default` model. The fresh run
made exactly one request for each of 56 scenarios: zero transport retries,
zero order permutations, zero clarification follow-up calls, and zero Prolog
reruns. Each response was checkpointed before the next request. Final raw
calls, scored results, and the compact comparison are respectively:

- `evaluation/preference_state_llm_single_pass_calls.json`;
- `evaluation/preference_state_llm_single_pass_results.json`;
- `evaluation/preference_state_llm_single_pass_summary.csv`.

The run used 554,195 input tokens and 26,991 output tokens (581,186 total).
For the primary comparison, an offline deterministic normalizer maps stable
IDs or exact unique official labels (trimmed and case-insensitive) to stable
IDs before validation. It does not use fuzzy matching, synonyms, gold labels,
or Prolog output. This maps 221 component occurrences and raises contract-valid
outputs from 2/56 under strict ID-only parsing to 31/56. Raw responses remain
unchanged and both strict and normalized results are retained.

| Method | Valid / attempted | Coverage | Primary accuracy | Explanation P/R | Top-1 relevance | Action type |
|---|---:|---:|---:|---:|---:|---:|
| Compositional Prolog | 56 / 56 | 98.21% | 33.93% | 75.74% / 91.07% | 86.61% | 98.21% |
| Direct LLM, normalized | 31 / 56 | 41.96% | 25.89% | 32.14% / 42.86% | 42.86% | 30.36% |

The table is end-to-end over all 56 attempts; invalid outputs count as zero
rather than disappearing from the denominator. Conditional on the 31 valid
normalized outputs, LLM coverage is 75.81%, primary accuracy 46.77%,
precision/recall 58.06%/77.42%, top-1 relevance 77.42%, and action-type
accuracy 54.84%. Those conditional values describe reasoning after interface
success, while the end-to-end values describe the complete system.

After normalization, 25 attempts remain invalid: eight have invalid component
cardinality, four contain non-exact/fabricated component IDs, four are invalid
JSON, three are provider failures, two have invalid explanation types, and
four have one-off duplicate/status/primary/top-level schema errors.

The normalized result still underperforms compositional Prolog on every
headline end-to-end metric. It also has a 14.52% false-interaction rate among
valid outputs versus 0.89% for Prolog, and fails to clarify in 58.82% of valid
cases whose expected action is clarification.

## Targeted contract-repair pass

The diagnostic identified four saved responses that were conservatively
recoverable offline and 21 cases requiring a new response. Those 21 IDs were
rerun exactly once with the strengthened ID/cardinality/action prompt, zero
transport retries, per-case checkpointing, and no Prolog reruns. Eighteen of
the 21 reruns validate; three remain invalid. The final composite therefore
uses 31 original normalized outputs, four conservative offline recoveries, and
21 targeted rerun records, of which 18 are valid.

| Method | Accepted output | Valid decision | Coverage | Primary accuracy | Explanation P/R | Top-1 | Action type |
|---|---:|---:|---:|---:|---:|---:|---:|
| Compositional Prolog | 56 / 56 | 56 / 56 | 98.21% | 33.93% | 75.74% / 91.07% | 86.61% | 98.21% |
| LLM final composite | 53 / 56 | 51 / 56 | 74.11% | 36.61% | 52.08% / 75.00% | 73.21% | 60.71% |

These are end-to-end metrics over all 56 scenarios, with the three remaining
invalid outputs scored as zero. Conditional on the 53 accepted outputs, LLM
coverage is 78.30%, primary accuracy 38.68%, precision/recall 55.03%/79.25%,
top-1 relevance 77.36%, action-type accuracy 64.15%, and decision validity
96.23%. The LLM still has a 19.81% false-interaction rate among accepted
outputs and fails to clarify in 40.63% of accepted clarification cases.

This composite is a **second-chance contract-repair evaluation**, not a
single-shot comparison: 21 failures received a stronger prompt and another
request. The initial normalized 31/56 table above remains the fair one-request
baseline. Across both passes the LLM used 77 requests, zero transport retries,
757,617 input tokens, and 36,469 output tokens (794,086 total).

The remaining invalid cases are `preference_atomic_006` (primary not active),
`atomic_music` (wrong top-level fields), and `correction_interaction_block`
(malformed JSON). They were not rerun again.

## Interface and leakage boundary

`CorrectedDirectPreferenceStateLLM` receives only:

- the natural-language visitor history;
- allowlisted hypothesis definitions;
- real observed and candidate artwork IDs, labels, and typed ArtGraph facts;
- candidates in the recorded randomized order;
- the missing-evidence flag and output task.

It does not receive latent profiles, target/distractor fields, benchmark
construction metadata, expected actions, relevance labels, Prolog output, or
proofs. Test-only hidden facts are removed before prompt construction.

The validator requires one component for `atomic`, two distinct allowlisted
components for `all_of`, unique explanations, a returned primary explanation
that is active, a valid action type, and an allowlisted candidate for
recommendations. Clarification and abstention cannot smuggle in an artwork ID.
Raw responses, parsed results, request count including retries, timestamps,
returned model ID, token usage, latency, failures, and refusals are recorded.
Structured output and refusal handling follow the official OpenAI
[Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

Normalization happens before that validator. Every transformation records the
original string, stable ID, JSON path, and rule. Strings such as
`expressionist_style`, `non-portrait genre`, or `genre: ag_4` remain invalid;
the evaluator does not guess what the model meant.

## Reproduction and persistence

Set credentials only in the current process environment:

```powershell
$env:PREFERENCE_STATE_LLM_PROVIDER = "openai"
$env:PREFERENCE_STATE_LLM_MODEL = "<selected-model-or-snapshot>"
$env:OPENAI_API_KEY = "<secret-provided-outside-git>"
```

The auditable one-pass runner refuses to overwrite final outputs, checkpoints
each scenario, and can resume without repeating completed scenario IDs:

```powershell
.\.venv\Scripts\python.exe -u `
  -m evaluation.evaluate_preference_state_llm_single_pass --fresh-all
```

If a process ends after one or more checkpoint rows are written, continue only
the unfinished IDs with:

```powershell
.\.venv\Scripts\python.exe -u `
  -m evaluation.evaluate_preference_state_llm_single_pass --fresh-all --resume
```

The API key is read from the environment by the Responses adapter and is not
serialized into requests, result files, tests, documentation, or source.

Normalize and rescore the persisted responses without an API call:

```powershell
.\.venv\Scripts\python.exe -u `
  -m evaluation.normalize_preference_state_llm_results
```

Primary normalized artifacts are
`evaluation/preference_state_llm_normalized_results.json` and
`evaluation/preference_state_llm_normalized_summary.csv`. The strict-ID files
remain an interface-compliance diagnostic rather than the main comparison.

## Invalid-output diagnostic and rerun gate

The 25 normalized failures were inspected offline without API calls. Four are
conservatively recoverable from their saved responses: stripping an exact
JSON Markdown fence, ignoring only an extra closing brace after one complete
object, mapping the unambiguous `conjunction` enum alias to `all_of`, or mapping
a collision-free slug rendering of an official label. This leaves 21 targeted
reruns rather than 25.

The remaining failures cannot be repaired without changing meaning: three
provider failures have no response, two JSON strings are substantially
malformed, and sixteen violate component cardinality/vocabulary, duplicate or
status semantics, primary-explanation consistency, or the top-level contract.
The exact case list and per-case diagnosis are retained in
`evaluation/preference_state_llm_invalid_diagnostic.json` and its CSV mirror.

Before a targeted rerun, the prompt now repeats the allowlisted component IDs,
cardinality, enum, primary, action, and raw-JSON requirements in plain language
in addition to the structured schema. A rerun must call only the 21 manifest
IDs, once each, with zero transport retries and per-case checkpointing. The
original calls must remain immutable and the rerun must be reported as a
targeted contract-repair pass, not silently substituted into the original
single-pass result.

That pass is now complete. Its raw calls and per-case results are in
`evaluation/preference_state_llm_invalid_rerun_calls.json` and
`evaluation/preference_state_llm_invalid_rerun_results.json`. The merged final
comparison is in `evaluation/preference_state_llm_final_comparison_results.json`
with a compact CSV at
`evaluation/preference_state_llm_final_comparison_summary.csv`.
