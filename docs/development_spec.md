# Logic-Driven Museum Tour Guide LLM
## Prototype Development Specification (Draft v1.0)

**Course:** CS3263 — Foundations of Artificial Intelligence  
**Project:** Logic-Driven Museum Tour Guide LLM  
**Target:** Demonstrable prototype for the presentation (week of 9 November 2026); evaluated implementation for the final report (13 November 2026)  
**Owners (as proposed):** Chen Chi — logic engine and backend; Song Bingxi — LLM query adaptation and frontend

> **Status of this document.** The project motivation, scope, division of work and original milestone windows follow the submitted proposal. The schemas, algorithms, evaluation targets, technology choices and revised action plan below are **proposed engineering decisions**, not requirements prescribed by the course.

## 1. Goal and research question

**Goal.** Implement and evaluate a small museum-guide prototype that identifies missing visitor knowledge or interests, selects a useful clarification question using logical reasoning, and adapts subsequent explanations to the updated visitor state.

**Research question.** For a bounded museum-information task, does an LLM that translates a visitor utterance into predicates and delegates clarification selection to a logic engine outperform an LLM that selects questions directly from the same information?

The **AI subproblem** is *next-action selection for information gathering*: given a curated knowledge base, a requested topic and a partially known visitor model, decide whether to **ASK**, **EXPLAIN**, **CONFIRM**, **CHANGE_TOPIC**, or **FINISH**, and identify the relevant concept. The solver must make this choice from explicit facts and rules rather than asking an LLM to decide implicitly.

## 2. Scope and completion criterion

### Must have — demonstration-ready MVP

1. A **small, curated museum KB** with concept identifiers, topic/artwork links, a directed prerequisite graph, and source references.
2. A **session-only visitor model** that distinguishes `known`, `not_known`, `unknown`, and `conflicted` knowledge; records interests, previously asked/presented items, and skips.
3. An **LLM extraction component** that maps a visitor message to a validated, structured state update. The system must reject nonexistent concept IDs and must not convert silence into a negative assertion.
4. A **deterministic logic selector** that inspects the target's prerequisites, chooses an action, and returns a trace explaining the selection.
5. **Multi-round interaction**, including an update after the visitor replies and prevention of repeated clarifications.
6. A **direct-LLM baseline** that performs the same next-action-selection task without the logic selector.
7. A **reproducible set of test scenarios** and an initial comparison of the two approaches.

### Out of scope

Full museum itinerary planning, unconstrained web retrieval, extensive collections, user accounts, long-term visitor tracking, automatic knowledge mastery assessment, or polished product deployment. A thin chat interface or terminal demo is sufficient; accurate reasoning and evaluation take priority.

**Definition of done:** From an initial visitor utterance, the system must (i) extract and display the current state, (ii) select the next action with a logic trace, (iii) ask or explain appropriately, (iv) process a follow-up turn without looping, and (v) run the equivalent example through the LLM-only baseline.

## 3. System architecture

```text
                         +-----------------------+
Visitor utterance ------>| LLM state extractor   |
                         +-----------+-----------+
                                     | candidate JSON changes
                                     v
                         +-----------------------+
                         | Schema & ID validator |
                         +-----------+-----------+
                                     | accepted changes
                                     v
                         +-----------------------+
                         | Session visitor state |
                         +-----------+-----------+
                                     |
Curated museum KB -------------------+----> Logic engine
                                            | action + target + trace
                                            v
                                       Response renderer
                                            |
                                            v
                                      Visitor-facing UI

Baseline comparison: Same visitor dialogue + curated information
                     ------------------> Direct LLM action selection
```

**Recommended architecture:** Python modules with in-memory session state and JSON/YAML KB files. Use a simple Streamlit screen or minimal web UI; a full backend service is optional. Keep the logic engine callable independently of both the LLM and UI so that unit tests can run without an API.

## 4. Data and logical representation

### 4.1 Museum knowledge base

Use **one bounded museum collection or theme** (e.g., a handful of artworks and associated concepts). Start with roughly **8–12 concepts and 5–10 prerequisite links**; these are manageable engineering targets, not grading minimums. Each explanation must have a curated text snippet and a source identifier. Do not use unverified historical details in the submitted demo.

Example *illustrative* records (not actual museum claims):

```json
{
  "concepts": {
    "intro": {"title": "Theme introduction", "source_ids": ["S1"]},
    "light": {"title": "Light and colour", "source_ids": ["S2"]},
    "technique": {"title": "Painting technique", "source_ids": ["S3"]}
  },
  "prerequisites": [["technique", "intro"], ["technique", "light"]],
  "topic_targets": {"sample_theme": "technique"}
}
```

The edge `prerequisites = [target, prerequisite]` means that explaining the target is more appropriate once the prerequisite has been covered. Validate the prerequisite graph as a DAG; flag cycles and missing IDs during KB loading.

### 4.2 Visitor model

Let **M** be the finite set of museum concepts. Let **K ⊆ M** be the set of concepts explicitly confirmed as known by the visitor. Other concepts are *not* assumed to be unknown-to-the-person or false; they have an explicit state.

```json
{
  "session_id": "demo_01",
  "interests": ["sample_theme"],
  "goal": "technique",
  "knowledge": {"intro": "unknown", "light": "unknown"},
  "presented": [],
  "skipped": [],
  "asked": [],
  "turn": 1
}
```

Allowed knowledge states are `known`, `not_known`, `unknown`, `conflicted`. Maintain `presented` separately: **giving an explanation is not proof that a visitor understands it**. `asked` supports duplicate-question prevention; `skipped` respects visitor preference. Store all data in session memory by default.

### 4.3 Predicates and rules

Use course-relevant logical notation, with the actual implementation operating on a finite KB:

- `goal(t)`: concept *t* is the selected explanation target.
- `requires(t,p)`: concept *p* is a prerequisite of target *t*.
- `knows(p)`, `not_knows(p)`, `unresolved(p)`: explicit state facts, never inferred solely from missing entries.
- `presented(p)`, `skipped(p)`: interaction history and visitor control.
- `ready(t)`: all relevant prerequisites are known or already presented, subject to no unresolved conflict.

Illustrative rules:

```text
goal(t) AND requires(t,p) AND unresolved(p) -> candidate_ask(p)
goal(t) AND requires(t,p) AND not_knows(p)
        AND NOT presented(p)                 -> candidate_explain(p)
all required p are (knows(p) OR presented(p)) -> ready(t)
```

These are **policy rules over explicitly stored states**, not unrestricted first-order inference. The `all` prerequisite check and the `NOT presented` test are bounded program operations, so the implementation should not present them as pure Horn-clause derivations. Use **backward chaining** to expand prerequisites for the chosen goal and **forward updates** to recompute eligible actions after visitor-state changes. Critically, infer readiness to *present* a concept, **not** that the visitor *knows* it.

## 5. Decision policy and interaction loop

A deterministic priority order prevents the rules from emitting multiple incompatible actions:

1. **CONFIRM** if the latest visitor answer creates a meaningful contradiction (`conflicted`).
2. **CHANGE_TOPIC / OFFER_ALTERNATIVE** if the goal or an essential prerequisite was skipped.
3. Visit the goal's prerequisites in a stable order (depth-first, prerequisites before dependent concepts, with ID/curator priority as tie-breaker).
4. For the first `unknown` prerequisite not already asked without an intervening change, **ASK** whether the visitor knows it.
5. For the first `not_known` prerequisite not yet presented, **EXPLAIN** it with a cited curated snippet.
6. If prerequisites are covered, **EXPLAIN** the goal (or **FINISH** if it has already been presented).
7. If no goal can be selected, **ASK_INTEREST** or **FINISH** rather than inventing content.

```python
def select_next(goal, kb, visitor):
    if visitor.has_conflict():
        return Action("CONFIRM", visitor.conflict_id(), reason="conflicting answers")
    if visitor.skipped_goal_or_required_concept(goal, kb):
        return Action("CHANGE_TOPIC", goal, reason="visitor skipped dependency")

    for p in kb.ordered_prerequisites(goal):
        status = visitor.status(p)
        if status == "unknown":
            if visitor.can_ask(p):
                return Action("ASK", p, reason=f"unresolved prerequisite of {goal}")
            return Action("CHANGE_TOPIC", goal, reason="unanswered prerequisite; avoid re-asking")
        if status == "not_known" and not visitor.was_presented(p):
            return Action("EXPLAIN", p, reason=f"missing prerequisite of {goal}")

    if not visitor.was_presented(goal):
        return Action("EXPLAIN", goal, reason="prerequisites covered")
    return Action("FINISH", goal, reason="target already presented")
```

The production function must additionally handle `conflicted` on prerequisites, retry/skip policy for unanswered questions, and `known` answers. No rule may repeatedly ask the same unresolved question indefinitely. For a DAG, prerequisite traversal can be implemented in **O(V + E)** time per selection, where V and E are the relevant concepts and prerequisite edges.

## 6. LLM contracts

### 6.1 Extractor (hybrid system)

**Input:** allowed concept IDs, current state summary, latest visitor message.  
**Output:** structured candidate updates, with no free-form changes to the KB.

```json
{
  "interest_add": ["sample_theme"],
  "knowledge_updates": [{"concept_id": "intro", "state": "not_known"}],
  "skip_concepts": [],
  "change_topic_to": null,
  "ambiguous": false
}
```

Validation should discard IDs not in the KB, reject invalid state labels, flag contradictions, and log the raw and validated outputs separately. When evidence is unclear, preserve `unknown` and ask rather than make an unsupported inference.

### 6.2 Renderer

The logic engine returns **action type, concept ID, reason trace and permitted source IDs**. The renderer may paraphrase an approved question or source-backed explanation but may **not change the action, target, visitor status or historical facts**. For a deterministic proof-of-concept, template-based messages are acceptable and make the logic contribution easier to demonstrate.

### 6.3 Direct-LLM baseline

Give the same model the same visitor messages, curated museum information, and task objective, but ask it to choose an action and target **directly**, without calling the deterministic selection algorithm. Require the same output schema and evaluate against the same annotated test cases. Fix model/version, generation settings and context access where possible. Log tokens, failures, latency and invalid outputs. The comparison isolates reasoning strategy better if the museum information is equivalent across both modes.

**Optional ablation:** Run the logic engine with gold/manual state extraction to separate failures caused by the LLM translator from failures caused by the rules.

## 7. Minimum interface and APIs

A single screen is sufficient: **dialogue** on the left; **debug panel** on the right (visitor predicates, prerequisite path, chosen action, rule trace, source IDs). Add a toggle for `Hybrid` versus `Direct LLM`, a `Reset session` control, and an `Export logs` option if time allows.

Internal Python interfaces (HTTP endpoints optional):

```text
parse_visitor_turn(message, state, allowed_ids) -> StateDelta
apply_state_delta(state, delta)               -> VisitorState
select_next(goal, kb, state)                  -> Action
render_response(action, kb)                   -> Message
run_turn(mode, session, message)              -> TurnResult
```

Proposed project layout:

```text
museum-guide/
  data/museum_kb.json
  src/models.py              # schemas, validation
  src/logic_engine.py        # prerequisite traversal and action policy
  src/visitor_state.py       # state transitions and conflicts
  src/llm_extractor.py       # text -> proposed predicate updates
  src/response_renderer.py   # cited messages
  src/baseline.py            # direct LLM action selection
  src/orchestrator.py        # multi-round flow
  ui/app.py                  # minimal demo UI
  tests/test_logic.py
  tests/test_state.py
  eval/scenarios.jsonl
  eval/run_eval.py
  README.md
```

## 8. Demonstration scenario

| Turn | Visitor statement / system event | Expected behavior |
|---|---|---|
| 1 | “I’m interested in this theme.” | Set interest and target; recognize `intro` as unresolved; **ASK** about prior familiarity. |
| 2 | “I haven't studied the introduction.” | Change `intro` to `not_known`; **EXPLAIN** `intro` using curated source S1; mark `presented`, not `known`. |
| 3 | “I already know about light and colour.” | Mark `light=known`; skip redundant clarification; **EXPLAIN** `technique` with source S3. |
| 4 | “Ask me about something else.” | Respect topic change rather than forcing the original goal. |

On the presentation slide, show the **same initial input** to the direct LLM and compare selected actions side-by-side. Include one case where the two methods agree and one where they differ; do not pre-claim that the hybrid system is superior.

## 9. Testing and evaluation

### 9.1 Unit and integration checks

- **State integrity:** unknown is not the same as not-known; extraction cannot invent IDs; conflicting updates do not silently overwrite previous explicit answers.
- **Logical behavior:** unresolved prerequisite triggers ASK; not-known triggers EXPLAIN; known or presented prerequisite permits progression; dependency cycles are rejected.
- **Conversation behavior:** no repeated question loop; skips and topic changes work; restart clears session; every explanation references an approved KB source.
- **Comparison behavior:** both approaches receive equivalent factual context and produce machine-scorable action/target IDs.

### 9.2 Test set

Target **20–30 prewritten scenarios** if resources allow. Include: fully known prerequisites; all prerequisites missing; partially known state; vague answer; correction/contradiction; skip; change of interest; already-asked question; irrelevant user message; and unsupported or nonexistent concept. Use realistic paraphrases in addition to controlled synthetic cases.

For each scenario, manually annotate **acceptable action(s)**, acceptable target(s), prerequisite coverage, and whether clarification is necessary. Make the rubric before inspecting model outputs. A scenario may have more than one reasonable action; do not mark a valid alternative wrong solely because it differs from the hand-coded selector.

### 9.3 Metrics and analysis

| Metric | Operational definition |
|---|---|
| Action validity | Percentage of cases producing a valid allowed action. |
| Action/target appropriateness | Percentage matching one of the annotated acceptable actions and targets. |
| Unnecessary clarification rate | Proportion of asked questions classified as redundant or irrelevant. |
| Visitor-state update accuracy | Correct predicate changes / total evaluated changes (evaluate extraction separately). |
| Multi-round task success | Percentage of dialogues reaching a relevant supported explanation without an unrecoverable loop or contradiction. |
| Unsupported factual claims | Number of explanation claims lacking a supporting curated source. |
| Cost and latency | Tokens/calls and elapsed time per scenario, with experimental conditions recorded. |

Report per-category outcomes, a few annotated transcripts and failure cases; avoid sweeping conclusions from a small dataset. Discuss cases where the hybrid approach fails because its KB is incomplete, the prerequisite policy is too rigid, or the LLM misparses a visitor message. Also discuss whether a direct LLM can handle nuanced or unexpected replies more gracefully.

## 10. Responsible AI safeguards

- **Grounding and transparency:** limit museum claims to curated descriptions and cite source IDs; keep a visible logic trace for why a question was asked.
- **Provisional profiling:** record only visitor-stated evidence and clearly distinguish `unknown` from `not_known`; allow corrections.
- **Autonomy:** offer skip and change-topic options; do not turn a visitor’s desire not to answer into a knowledge claim.
- **Privacy:** session-only state by default; no accounts or long-term profile. Obtain consent and remove identifiers before retaining dialogue for analysis.
- **Failure modes:** test unsupported claims, unintended assumptions about expertise, irrelevant clarifications and excessive questioning.

These safeguards instantiate the commitments already listed in the submitted proposal; evaluation should measure them rather than merely mention them.

## 11. Work allocation and near-term milestones

The original proposal assigns **logic engine/backend to Chen Chi** and **LLM query adaptation/frontend to Song Bingxi**. Suggested implementation ownership:

| Workstream | Owner | Deliverable |
|---|---|---|
| KB schema, logical policy, predicate semantics, unit tests | Chen Chi | Testable `logic_engine.py` and KB validator |
| Session state, backend orchestration, integration logging | Chen Chi | Deterministic multi-round turn loop |
| Extraction prompt/schema, output validation integration | Song Bingxi | `llm_extractor.py` with test cases |
| Simple UI, response text and baseline runner | Song Bingxi | End-to-end demo and direct-LLM mode |
| Scenario annotations, experiments, analysis and report | Both | Comparative results and written interpretation |

**Revised execution plan (proposed, beginning 25 October 2026):**

| Date | Milestone / exit criterion |
|---|---|
| **25–27 Oct** | Freeze small KB, predicate schema, goal/prerequisite policy; logic unit tests pass. |
| **28–31 Oct** | Connect extractor, state updater and selector; demonstrate 3+ turns through terminal/UI. |
| **1–3 Nov** | Complete direct-LLM baseline, skips/conflicts, reproducible logs and scenario annotations. |
| **4–7 Nov** | Run comparison; inspect failures; prepare tables and representative transcripts. |
| **8–9 Nov** | Freeze presentation demo, recording fallback and slides for presentation week. |
| **10–12 Nov** | Finalize 10-page report, results, Responsible AI section, limitations and contribution disclosure. |
| **13 Nov** | Submit final report. |

**Administrative check:** The CS3263 guidelines describe **three-person teams**, while the supplied proposal lists two members. Confirm any approved exception with the teaching team and ensure the final contribution statement reflects actual membership.

**Fall-back points:** If the UI is incomplete, use CLI plus logs; if LLM extraction is unreliable, demonstrate the logic solver with manually supplied state and evaluate translation errors separately; if multi-turn evaluation is too costly, preserve a rigorous, smaller benchmark and describe its limits. Do not silently replace an incomplete implementation with a scripted video described as live behavior.

## 12. Acceptance checklist

- [ ] KB is finite, source-backed and validated (including prerequisite acyclicity).
- [ ] At least one three-turn visitor conversation runs end-to-end.
- [ ] Logic engine independently returns action, target and interpretable rule trace.
- [ ] Visitor can correct knowledge, skip a question and change the topic.
- [ ] Previously asked or explained concepts are not repeatedly forced on the visitor.
- [ ] LLM-only baseline runs on the same scenarios with comparable inputs.
- [ ] Annotated scenarios, outputs and evaluation scripts are retained for reproducibility.
- [ ] Presentation shows genuine outputs and explains the logical formulation.
- [ ] Report analyzes successes, limitations, responsible AI and each member’s contribution.
- [ ] The report discloses how LLM tools assisted development, as required by course guidelines.

## Reference materials used

- **CS3263 Project Guidelines (AY2026/27)** — project topic, direct-LLM versus tool-translation comparison, responsible AI, evaluation guidelines, presentation and report requirements.
- **Logic-Driven Museum Tour Guide LLM — submitted proposal** — motivation, small curated KB, visitor-state modeling, forward/backward chaining, excluded features, roles and original timeline.
