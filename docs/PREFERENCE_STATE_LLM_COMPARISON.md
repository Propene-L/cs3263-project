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
Only 2 of 56 model outputs passed the strict allowlist/schema validator, so
LLM accuracy figures conditional on those two outputs are not representative.
The primary result is 3.57% valid decisions per attempt, compared with 100%
for compositional Prolog.

| Method | Valid / attempted | Coverage | Primary accuracy | Explanation P/R | Top-1 relevance | Action type |
|---|---:|---:|---:|---:|---:|---:|
| Compositional Prolog | 56 / 56 | 98.21% | 33.93% | 75.74% / 91.07% | 86.61% | 98.21% |
| Direct LLM | 2 / 56 | 50.00%* | 50.00%* | 25.00%* / 50.00%* | 50.00%* | 50.00%* |

`*` Conditional on the two valid LLM outputs, not all 56 attempts.

Of the 54 rejected attempts, 42 used labels such as `expressionist style`
instead of allowlisted IDs such as `h_expressionist_style`; four had invalid
component cardinality, four were invalid JSON, three provider requests
failed, and one returned the wrong top-level fields. Including the exact JSON
schema in the prompt as well as `text.format` was therefore insufficient to
make this provider/model reliably follow the contract.

The two accepted cases were `preference_interaction_024` and `noisy_feline`.
The former had incorrect coverage and top-1 relevance; the latter had correct
coverage and top-1 relevance but the wrong action type. No claim of competitive
LLM state-reasoning performance is supported by this run.

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
