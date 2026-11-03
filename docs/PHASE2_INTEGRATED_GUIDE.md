# Phase 2 — Integrated Logic-Driven Museum Guide

**Patch target:** `Propene-L/cs3263-project`, branch `phase-1-2-state-reasoning-relevance` (after `5fd3dec`). Install by copying the included `museum_guide`, `data`, `ui`, `tests` and `docs` files into the repository root. **Do not replace the repository's existing `museum_guide/__init__.py`, `preference_state.py` or `prolog_bridge.py`.** This patch does not modify the Phase 0–1.2 inference rules, frozen benchmarks or historical result files.

## Implemented workflow

- **Manual/offline:** explicit commands -> validation -> existing corrected Prolog state engine -> source-bounded explanation/clarification templates.
- **Hybrid:** natural-language turn -> separate Responses-compatible LLM state-delta extraction -> same allowlist validator -> corrected Prolog preference engine (plus deterministic educational prerequisite planner) -> source-bounded templates. The LLM cannot choose the hybrid next action.
- **Direct LLM:** the *same* validated state extraction -> separate direct-LLM next-action selection. The direct selector does not call Prolog and does receive the original current utterance and recent history. This is an engineering baseline, **not** a fair single-call vs single-call comparison: direct mode makes separate extraction and selection calls. Report both calls, errors and costs when evaluating it.
- **Knowledge:** session-limited `known`, `not_known`, `unknown`, `conflicted` states; backwards prerequisite traversal; explicit response updates; `presented` independent of `known`; skips and corrections. The educational prerequisite traversal is currently implemented as deterministic Python graph rules, **not SWI-Prolog**; SWI-Prolog remains authoritative for preference deduction.
- **Content:** six small educational concepts with explicit source URLs, plus recommendations whose displayed metadata comes from reviewed ArtGraph facts and `agf_*` identifiers. Educational prerequisites are **curatorial workflow choices, not ArtGraph assertions**.
- **UI:** thin optional Streamlit chat with session reset, mode switch and provenance panel. The UI does not implement reasoning.

## Setup (Windows PowerShell)

Run from the **full repository root**, not inside the patch ZIP:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:SWIPL_PATH = (Resolve-Path ".\.tools\swipl\bin\swipl.exe").Path
.\.venv\Scripts\python.exe -m pytest -q tests\test_phase2_dialogue.py tests\test_phase2_evaluation.py tests\test_phase2_prolog_integration.py
.\.venv\Scripts\python.exe -m museum_guide.cli --mode manual --demo
.\.venv\Scripts\python.exe -m museum_guide.cli --mode manual
```

Manual commands (IDs must exist in the frozen ArtGraph snapshot):

```text
like ag_8416
 dislike ag_13231
 dislike ag_8296
 yes
 topic c_expressionist_portrait
 no
 no
 unsure
```

The scripted acceptance evaluator is:

```powershell
.\.venv\Scripts\python.exe -m evaluation.evaluate_integrated_guide --mode manual
# Optional: provide a separate natural-language scenario JSONL and a configured model for live modes.
# .\.venv\Scripts\python.exe -m evaluation.evaluate_integrated_guide --mode hybrid --input your_live_scenarios.jsonl
```

It writes into `.runtime/` by default; scenario action labels are authored test expectations, not human ground truth.

Manual mode is intentionally **not** a natural-language parser. In hybrid mode, real visitor messages such as “I liked Albert Kollmann” are mapped to validated observation IDs by the configured model.

## Optional live LLM / UI

```powershell
$env:OPENAI_API_KEY = '<set-secret-locally>'
$env:MUSEUM_LLM_MODEL = '<provider-supported-model-id>'
# Optional for Responses-compatible services:
# $env:MUSEUM_LLM_ENDPOINT = 'https://your-provider.example/v1/responses'
.\.venv\Scripts\python.exe -m museum_guide.cli --mode hybrid
.\.venv\Scripts\python.exe -m museum_guide.cli --mode direct_llm
.\.venv\Scripts\python.exe -m pip install streamlit
.\.venv\Scripts\python.exe -m streamlit run ui\app.py
```

The existing `OpenAIResponsesTransport` is reused. External model support depends on the endpoint's **actual** compatibility with strict JSON schemas. No model name, key or evaluation score is hardcoded. API calls are **not** made by the offline unit tests. The model may return malformed outputs; the atomic state transaction prevents them from mutating a visitor session.

## Explicit trust boundary

`VisitorTurn -> LLM proposed StateDelta -> deterministic validate_delta -> visitor state -> Prolog inference -> next action -> fixed renderer`

The extractor can propose only allowlisted artwork likes/dislikes, exact hypothesis confirmations/rejections/conjunctions/corrections, knowledge-status assertions, topic requests and answers to a known pending question. It cannot inject predicates or facts into SWI-Prolog, edit the source catalog, change source URLs, mark an unknown concept as `not_known` through lack of evidence, or select a hybrid action. Keep provider credentials in environment variables, not in files or audit logs.

The direct baseline receives the same validated state *but independently selects the action*. Never describe fake-transport test results as real direct-LLM performance.

## Data and safety semantics

- Visitor profiles exist only for the current in-memory session; resetting starts a new state.
- No automatic disk or server persistence, user accounts, face recognition or identifiable visitor tracking.
- `not_recorded` museum attributes are unknown rather than negative facts.
- An observed dislike does **not** imply rejection of every attribute of the artwork.
- Unanswered interest confirmation is not repeatedly asked; `unsure` and `skip` are respected.
- Explicit contradictory knowledge statements produce `conflicted` and a follow-up confirmation; answering resolves it.
- Presenting a concept never silently changes its knowledge status to `known`.
- Source text is reviewable and short; it is not an unrestricted text generation system.
- ArtGraph data rights remain unresolved; only the already bounded, committed reviewed facts are used.

## Status and remaining validation

- New pure Python integration tests: 21 mocked-prover/provider tests passed locally during patch creation. Test file is portable to the full repo, but **there has been no real SWI-Prolog execution or live model call in this isolated build environment**.
- Real Prolog smoke test is included and should run in a full checkout where SWI-Prolog and generated facts exist.
- Existing regression tests must all pass in the user's actual repository before merging.
- The current integration does **not** claim that visitor knowledge is psychologically inferred; all knowledge statuses arise from visitor statements or confirmation, and the topic prerequisites are curated educational choices.
- Live system evaluation (multi-turn task completion, user-rated relevance, correction handling and unsupported factual claims) remains necessary. Preserve the 56 existing saved direct-LLM results as an offline *reasoning-core* benchmark, distinct from live end-to-end tests.

## Repo change surface

Add the following files (without overwriting earlier modules):

- `museum_guide/knowledge_layer.py`
- `museum_guide/turn_extraction.py`
- `museum_guide/dialogue.py`
- `museum_guide/direct_dialogue.py`
- `museum_guide/response_renderer.py`
- `museum_guide/cli.py`
- `data/curated/education_topics.json`
- `ui/app.py`
- `evaluation/evaluate_integrated_guide.py`
- `evaluation/integrated_scenarios.jsonl`
- `tests/test_phase2_evaluation.py`
- `tests/test_phase2_dialogue.py`
- `tests/test_phase2_prolog_integration.py`
- `docs/PHASE2_INTEGRATED_GUIDE.md`

**Please do not copy the temporary isolated-testing stubs for `preference_state.py`, `prolog_bridge.py` or `__init__.py`.** Those are not part of the delivered patch.
