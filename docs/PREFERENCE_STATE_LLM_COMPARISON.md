# Phase 1.2 Direct-LLM Comparison

## Status

The direct-LLM evaluation is **unexecuted**. Neither `OPENAI_API_KEY` nor
`PREFERENCE_STATE_LLM_MODEL` was configured during the corrected run. No LLM
scores or responses were fabricated, and
`evaluation/preference_state_llm_results.json` does not exist.

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

## Exact execution sequence

Set credentials only in the current process environment:

```powershell
$env:PREFERENCE_STATE_LLM_PROVIDER = "openai"
$env:PREFERENCE_STATE_LLM_MODEL = "<selected-model-or-snapshot>"
$env:OPENAI_API_KEY = "<secret-provided-outside-git>"
```

Run a two-case development smoke test first:

```powershell
.\.venv\Scripts\python.exe -m evaluation.evaluate_preference_state_corrected `
  --subset development --smoke --run-direct-llm `
  --output-prefix preference_state_llm_smoke `
  --llm-output preference_state_llm_smoke_results.json
```

Inspect `evaluation/preference_state_llm_smoke_results.json` for the prompt
boundary, raw response, parsing, refusal/error count, and model ID. Then run
the fixed held-out set without changing the prompt:

```powershell
.\.venv\Scripts\python.exe -m evaluation.evaluate_preference_state_corrected `
  --subset held_out --run-direct-llm `
  --output-prefix preference_state_llm_held_out `
  --llm-output preference_state_llm_results.json
```

The evaluator also runs two additional candidate-order permutations for a
small deterministic subset. These are sensitivity checks and contribute zero
independent samples. Any LLM changes are retained in the order audit.

The API key is read from the environment by the Responses adapter and is not
serialized into requests, result files, tests, documentation, or source.
