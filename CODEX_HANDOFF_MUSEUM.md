# Codex Handoff — CS3263 Logic-Driven Museum Guide

**Purpose:** An executable engineering handoff for Codex to build the prototype, not merely propose an architecture.

**Basis:** `CS3263_Museum_Prototype_Development_Plan.md` and the submitted `CS3263 proj proposal.docx`. Where this handoff specifies packages, file names, interfaces, targets or run commands, these are **implementation recommendations**, not course requirements.

**Target:** Demonstrable, source-backed, three-turn prototype for presentation week (9 Nov 2026), with reproducible direct-LLM comparison before the final report (13 Nov 2026).

---

## A. Operating procedure — how to use this with Codex

1. Open or create a Git repository named `museum-logic-guide`. Put this file and `AGENTS.md` at its root. Copy the prototype development specification into `docs/development_spec.md` for reference.
2. Start a Codex coding session in that repository. Paste the **Kickoff prompt** in section B. Ask Codex to implement **Phase 1 only**. Do not have Codex execute every phase in one unreviewed change.
3. After each phase, inspect the file diff and run the listed acceptance commands. Then paste the next phase prompt. Codex should edit files and run tests, not reply with example code only.
4. Preserve a working **offline/manual** path. Do not block logic-engine progress on API credentials, token budgets or UI polish.
5. Keep change sets separable (`git commit` after each accepted phase, or separate pull requests). Do not commit `.env`, API keys or personal visitor transcripts.

**Non-negotiable research distinction:** `hybrid` must use an LLM to translate language into *state updates*, then let the deterministic logic engine choose the action. `direct_llm` must have the LLM choose the action without calling the logic selector. `offline_manual` exists only for development/tests and must not be described as an evaluated LLM baseline.

---

## B. Kickoff prompt — paste directly into Codex

> You are the implementation agent for a CS3263 research prototype, **Logic-Driven Museum Guide LLM**. Read `AGENTS.md`, this `CODEX_HANDOFF_MUSEUM.md`, and `docs/development_spec.md` if present. Inspect the repository before editing.
>
> **Implement, don't just plan.** Work in small, tested phases. Start with **Phase 1 only** as specified below, creating real runnable Python files and tests. Do not implement an elaborate frontend, web scraper, agent framework, vector database or authentication. Favor transparent, deterministic classical-AI logic over opaque orchestration.
>
> Preserve the scientific comparison: `hybrid` = LLM extracts predicates → validator/state update → rule-based selector; `direct_llm` = LLM chooses action directly from the same visitor conversation and curated museum content. The two modes must never silently share the logic selector.
>
> Respect the provided scope: one finite, curated museum concept graph, explicit visitor states (`known`, `not_known`, `unknown`, `conflicted`), multi-round clarification and explanation, interpretable rule traces, and no long-term profiling. Unknown is **not** false; a presented explanation does **not** establish visitor mastery.
>
> After edits: run available tests, show changed files, list exact run commands, and note any failures/blockers. If APIs or credentials are unavailable, complete all offline work and stub external calls behind a mockable interface. Do not invent performance results or real museum citations. Do not ask me to repeat decisions already recorded in these files.

---

## C. Recommended stack and file tree

**Proposed defaults:** Python 3.11+, standard-library `dataclasses`/`Enum` for domain types, `pytest`, JSON KB/fixtures, `openai` Python SDK behind an interface for real API calls, and `streamlit` for the optional thin UI. Use lightweight dependencies. The implementation must run without any external key in manual mode.

```text
museum-logic-guide/
  AGENTS.md
  CODEX_HANDOFF_MUSEUM.md
  README.md
  pyproject.toml
  .env.example
  .gitignore
  docs/development_spec.md
  data/demo_kb.json
  museum_guide/
    __init__.py
    models.py           # enums and typed dataclasses
    kb.py               # file load, edge validation, ordered dependencies
    state.py            # session state, pending question, correction/conflict
    rules.py            # deterministic action selection + trace
    renderer.py         # template messages with approved source IDs
    llm_client.py       # LLM interface + optional real provider
    extraction.py       # utterance -> validated state delta
    baseline.py         # direct LLM next-action selector
    pipeline.py         # multi-round orchestration, three execution modes
    cli.py              # offline runnable entrypoint
  ui/app.py             # Streamlit, added late
  evaluation/
    scenarios.jsonl
    score.py
    run.py
  tests/
    test_kb.py
    test_state.py
    test_rules.py
    test_pipeline.py
    test_baseline.py
    test_eval.py
```

### Contract to freeze before implementation

- `requires(target, prerequisite)` represents a directed prerequisite edge. Reject cycles and unknown IDs. Traverse **transitive** prerequisites in a stable prerequisite-first order.
- `KnowledgeStatus`: `known | not_known | unknown | conflicted`. An omitted status means `unknown`, *not* `not_known`.
- `VisitorState`: session ID, topic/goal, explicit knowledge status map, `asked`/`presented`/`skipped` sets or lists, `pending_question`, and turn index. Treat conflicts as explicitly confirmable rather than silently overwriting evidence.
- `StateDelta`: recognized interest(s), knowledge assertions, skips, topic change, ambiguity indicator; every referenced ID must be validated against the finite KB.
- `Action`: `type` (`ASK`, `EXPLAIN`, `CONFIRM`, `CHANGE_TOPIC`, `ASK_INTEREST`, `FINISH`), `target_id` (nullable), rule ID, reason, prerequisite trace, and permitted source IDs. All actions must be machine-readable.
- `TurnResult`: the updated state, selected action, rendered response, audit trace, raw/validated extraction when applicable, mode and relevant errors.

**Priority policy (deterministic, first applicable):** resolve relevant conflict → honor skip/topic change → inspect transitive prerequisites in stable order → ask about first unresolved concept (once, no loop) → explain first explicitly-not-known concept not yet presented → explain selected goal → finish. If unanswered after asking, offer a non-repeating alternative; do not label the visitor as ignorant. A user saying “yes/no” can be interpreted relative to the stored `pending_question`.

**Academic precision:** This is a finite rule-based inference and action-selection engine, not a general-purpose first-order theorem prover. Implement explicit backward dependency tracing and forward updates of derived readiness/candidate actions; expose which facts and rules fired. Keep “presented” different from “known.”

---

## D. Build phases: exact prompts and acceptance gates

### Phase 1 — Foundation and deterministic inference (highest priority)

**Paste into Codex:**

> Implement Phase 1: initialize the Python package and pytest setup; create typed models, curated KB loader/validator, visitor-state transitions, and a deterministic rule-based next-action selector. Include source IDs on all explanation content. Create `data/demo_kb.json` with 8–12 **synthetic or clearly labeled illustrative concepts**, 5–10 prerequisite edges, and stubbed source references; do not invent authentic museum/history citations. Provide a documented place to substitute reviewed curator content.
>
> Implement prerequisite-first traversal over a DAG, traceable rules, explicit statuses, pending questions, skip/correction/conflict logic, repeat-question protection, and a pure `select_next_action(kb, state)` API that calls no model. Define `Action` and `TurnResult` types. Build an offline CLI or example script that walks through a minimum three-turn scenario using manual `StateDelta` inputs. Write unit tests for core cases. Run `python -m pytest -q` and `python -m museum_guide.cli --mode manual --demo` (or document the equivalent). **Write the actual files**, then provide a concise summary and any unresolved defects.

**Exit criteria:** offline 3-turn flow works; `pytest` passes; no network/API needed; the logic trace specifies relevant facts, prerequisite path, selected rule and target; no duplicate ASK loop.

**Minimum unit cases:**
1. Missing/invalid/cyclic KB edge → rejected with helpful error.
2. Unknown prerequisite → `ASK` (absence does not imply `not_known`).
3. Explicit `not_known` prerequisite → `EXPLAIN` with permitted source ID.
4. `known` prerequisite → advance, not redundant ASK.
5. `presented` prerequisite permits progression but status does **not** silently become `known`.
6. Contradictory assertions → `CONFIRM`, not silent overwrite.
7. `skipped` / topic change respected.
8. Same unanswered question not repeatedly asked each turn.
9. Nested prerequisites are considered, not merely direct parents.

### Phase 2 — LLM extraction and real multi-round hybrid pipeline

**Paste into Codex:**

> Implement Phase 2 on the passing Phase 1 code. Add `LLMClient` protocol/interface, fake client for offline tests, and optional real OpenAI-backed adapter configured via environment variables (no hard-coded secrets or default claims of model availability). Build extraction with a strict JSON output contract and validation of action-independent `StateDelta` against allowed IDs/statuses. The extractor may infer updates from the visitor message and `pending_question`, but may not insert museum facts or mark an unknown concept as `not_known` without explicit evidence. Handle invalid JSON, nonexistent concept IDs, ambiguous responses and provider failures safely.
>
> Build `pipeline.run_turn(mode='hybrid', ...)` that updates session state, calls the existing deterministic selector, then uses a **template-based renderer** for source-backed questions/explanations. Maintain audit logs for raw output, validated delta, rule trace and response, without logging secrets. Add tests with the fake client to demonstrate a real multi-turn flow and graceful provider failure. Ensure unit tests still run with no API key. Run all tests and CLI demo.

**Exit criteria:** `hybrid` end-to-end through fake LLM in tests, and through a configured live model when credentials are supplied; model never chooses the hybrid action; malformed extraction does not corrupt visitor state.

### Phase 3 — Genuine direct-LLM baseline (evaluation-critical)

**Paste into Codex:**

> Implement Phase 3: a `direct_llm` baseline where the model sees the same finite museum content, visitor turns and task objective as the hybrid system, and **chooses `Action` and `target_id` itself** using structured output. The direct mode must not invoke `rules.select_next_action` or reuse its rule-generated decision. Keep allowed action types and target IDs identical, validate returned actions, and render explanations from curated source text only. Use comparable prompt context and model configuration; record actual model name/config, tokens if reported, latency, parse failure and output.
>
> Add tests using a fake provider that verify the direct path does not call the logic selector, rejects invalid targets, and produces machine-scorable actions. Do not substitute a scripted response for a real baseline in research results; fixtures are for testing only.

**Exit criteria:** modes are separable and traceable; baseline can be called; both return the same `Action` schema; no baseline data is fabricated.

### Phase 4 — Evaluation harness and bounded scenario set

**Paste into Codex:**

> Implement Phase 4: a reproducible evaluation runner reading version-controlled JSONL dialogue scenarios, ground-truth *acceptable* action/target pairs, and expected state changes. Seed 8–10 carefully constructed test cases spanning: full knowledge, missing knowledge, partial knowledge, vague reply, correction/conflict, skip, topic change, duplicate question, nonexistent concept and nested dependency. Support extension to 20–30 without code changes; do not falsely represent templates as human-annotated benchmarks.
>
> Add an offline scorer for action validity, acceptable action/target match, unnecessary clarification, state update accuracy and multi-round completion. Write JSONL per-turn records and summary CSV (or JSON), including mode, scenario ID, timestamp, chosen action, references, errors, latency and model metadata. Running a live baseline must require explicit API configuration; no automatic expensive calls in tests. Document benchmark fairness and failure taxonomy. Run scorer tests and show exact eval commands.

**Exit criteria:** same scripts can evaluate hybrid and direct modes, outputs machine-readable, sample scoring works offline, test scenarios are clearly distinguished from reported live experiment results.

### Phase 5 — Thin demo UI and report-ready artifacts

**Paste into Codex:**

> Implement Phase 5: a single-screen Streamlit UI with conversation, `manual/hybrid/direct_llm` mode selector, reset, and debugging panel showing current knowledge statuses, active goal, prerequisite trace, selected rule, source IDs, and most recent parsed state delta. Never display provider secrets. The UI must invoke the existing pipeline rather than implement its own reasoning. Explain clearly when content is synthetic/illustrative.
>
> Make the README genuinely runnable from a clean clone: setup, environment variables, offline demo command, live model configuration, test command, evaluation command, failure-handling notes and project limitations. Add a short architecture diagram and one verified three-turn example transcript. Run all tests and a lightweight UI import/smoke check, and provide final status (implemented / missing / untested) without overstating readiness.

**Exit criteria:** demo can show a three-turn state transition with source IDs and rule trace; README reproduces CLI/eval steps; UI failure does not block CLI demo.

---

## E. Evaluation scenario shape (illustrative)

Use one scenario per line. The exact JSON schema can be revised by Codex, but keep expected outputs and model responses separate.

```json
{"id":"unknown_intro","initial_state":{"goal":"technique","knowledge":{}},"turns":[{"user":"I'm interested in this theme."}],"acceptable":[{"action":"ASK","target_id":"intro"}],"category":"missing_knowledge","is_gold_annotated":false}
```

The above is a **fixture example**, not actual experimental data. Before reporting quantitative results, review/correct the acceptable-action annotations and replace illustrative museum text with properly sourced museum content. If multiple next questions are sensible, score against a *set* of acceptable actions, not an arbitrarily unique answer.

---

## F. Suggested run commands to require from Codex

The final README should support commands **equivalent to** these (Codex may adapt entrypoints and must keep them consistent):

```bash
python -m venv .venv
# Activate the environment for your shell, then:
pip install -e '.[dev,ui,llm]'
python -m pytest -q
python -m museum_guide.cli --mode manual --demo
python -m museum_guide.cli --mode hybrid --demo   # requires provider key
python -m museum_guide.cli --mode direct_llm --demo # requires provider key
python -m evaluation.run --mode hybrid --input evaluation/scenarios.jsonl --output results/hybrid.jsonl
python -m evaluation.run --mode direct_llm --input evaluation/scenarios.jsonl --output results/direct.jsonl
streamlit run ui/app.py
```

Include `.env.example` with `OPENAI_API_KEY=` and `OPENAI_MODEL=` placeholders; `.env` should be gitignored. Do not assume all three optional dependency groups exist until Codex implements them.

---

## G. Review checkpoints and change-management rules

At **every phase** Codex must report: (a) files changed, (b) functions/interfaces added, (c) commands actually run and results, (d) relevant sample output, (e) broken or unverified behavior, (f) what phase is next. Codex must not claim green tests it did not execute, or claim live LLM performance from mocked tests.

Use a commit or PR boundary at each accepted milestone:

| Milestone | Repository artifact | Reviewer checks |
|---|---|---|
| P1 — Rules | KB + pure solver + tests + manual CLI | Trace correctness, knowledge semantics, no loops |
| P2 — Hybrid | extractor + validator + pipeline + tests | No LLM-controlled hybrid decision, graceful invalid JSON |
| P3 — Baseline | direct LLM selector + tests | Separate reasoning path, comparable inputs |
| P4 — Evaluation | scenarios + scoring + result logging | Valid annotations, metrics and replicability |
| P5 — Demo | Streamlit + README + smoke check | Unscripted 3-turn demo, visible trace and sources |

**Work allocation in the submitted proposal:** Chen Chi — logic engine/backend; Song Bingxi — LLM query adaptation/frontend. The suggested phases align with this division; both should review evaluation design and results.

**Fallback order if short on time:** P1 must work; then P2; then P3/P4 for course comparison. Skip UI polish before dropping baseline/evaluation. A CLI demo with real state transitions is acceptable as an engineering fallback. Do not describe incomplete/mock features as complete.

---

## H. Final acceptance — do not mark complete without evidence

- [ ] Offline 3+ turn conversation genuinely changes state and next action.
- [ ] Pure, deterministic logical selector works without LLM/API.
- [ ] Prerequisite traversal, rule trace, and explicit visitor statuses are visible.
- [ ] Ambiguous answers, conflict, skip, and topic change do not make the system loop.
- [ ] Every visitor-facing factual explanation comes from a vetted source entry.
- [ ] Hybrid extraction is validated and cannot change the KB.
- [ ] Direct-LLM path is independent of the logic selector.
- [ ] Tests and CLI commands run from clean installation.
- [ ] Quantitative evaluation uses actual collected outputs, not mocked fixtures.
- [ ] Limitations and prompt/model settings are documented for the final report.

**Handoff success condition:** A different developer (or fresh Codex session) can clone the repository, run the offline demo with no secrets, understand exactly why the logic selector chose an action, then optionally configure a real LLM to execute the hybrid and direct-baseline experiments.
