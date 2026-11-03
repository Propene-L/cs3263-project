# Direct-LLM Clarification Protocol

## Status

The Phase 1.1 provider adapter is implemented and mock-tested. No genuine
model request was executed in the recorded run because the required provider
configuration was absent. No mock output is reported as an experiment.

## Provider adapter

`OpenAIResponsesTransport` uses the OpenAI Responses API with a strict JSON
Schema response format. This follows the official guidance to use the
[Responses API for direct model requests](https://developers.openai.com/api/docs/guides/text)
and [Structured Outputs with `text.format`](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
The adapter:

- sends bearer authentication only from environment variables;
- uses the configured, recorded model ID;
- validates completed status, refusal/no-text conditions, JSON parsing, the
  declared decision enum, distinct options, and the current allowlist;
- retries transient HTTP 408/409/429/5xx and network failures;
- records response ID, requested/returned model, token usage when supplied,
  raw provider output, and the independently validated decision;
- sends `store: false` and commits no key or visitor transcript.

The legacy generic HTTP transport remains only for compatibility and mock
tests; it is not assumed to match a real provider response shape.

## Information parity and anti-leakage

For each round the direct model receives:

- the task and permitted `select_question`/`no_valid_question` schema;
- complete human-readable definitions for every active hypothesis;
- validated observations (or the authored utterance in Track B);
- eligible candidate IDs, labels, typed attributes, and supporting fact IDs;
- allowed IDs, excluded/viewed/rejected artworks, and prior questions;
- response-model assumptions and transition semantics;
- the same stable ranking policy used to describe the controlled task.

It never receives the hidden hypothesis, simulated response, Prolog-selected
pair, Prolog score, Prolog proof, or evaluation label. Returned decisions are
checked independently. `no_valid_question` is permitted and is scored as
correct or false using the shared evaluator.

The hybrid method receives the equivalent structured observations and facts,
then SWI-Prolog—not an LLM—selects the question.

## Tracks

**Track A — algorithm isolation** is the primary controlled comparison. Both
systems receive the same validated structured observations. Direct LLM selects
the pair; Prolog selects the hybrid pair.

**Track B — natural-language integration** uses each scenario's
`natural_language_utterance` and `intended_observation_ids`. Direct LLM selects
from the utterance plus the same evidence. The hybrid path uses
`ValidatedLLMObservationExtractor`, validates every proposed kind and ID, and
then passes only that state to Prolog. Extraction exactness must be reported
separately from question-selection validity. Generic Phase 1 descriptions are
not used as realistic utterances; the 45 Phase 1.1 additions contain explicit
utterances and intended interpretations.

## Configuration and commands

Required environment variables:

```powershell
$env:CLARIFICATION_LLM_PROVIDER = "openai"
$env:CLARIFICATION_LLM_MODEL = "<documented model or pinned snapshot>"
$env:OPENAI_API_KEY = "<secret>"
```

Optional override for compatible test infrastructure:

```powershell
$env:CLARIFICATION_LLM_ENDPOINT = "https://api.openai.com/v1/responses"
```

Smoke test on a deliberately reduced scenario file before a full run, then:

```powershell
.\.venv\Scripts\python.exe -u evaluation\evaluate_clarification.py `
  --max-rounds 3 --run-direct-llm --llm-track structured
```

For the direct-model side of Track B:

```powershell
.\.venv\Scripts\python.exe -u evaluation\evaluate_clarification.py `
  --max-rounds 3 --run-direct-llm --llm-track natural_language
```

The full command writes genuine raw/validated records to
`evaluation/phase_1_1_llm_results.json`. That file is created only when a real
transport is configured and invoked. Review it for sensitive free text before
sharing. Costs must be computed only when provider usage and a documented
price are both available; this implementation does not guess prices.

## Reproducibility record

Record provider, exact model/snapshot, endpoint class, date, round limit,
scenario hash, evidence hash, request count, input/output/cached/reasoning
tokens where returned, refusal/error counts, and any provider request IDs.
Temperature is intentionally not assumed because model families differ; any
non-default inference setting must be added explicitly and recorded.
