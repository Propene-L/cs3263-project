# CS3263 Museum Reference Guide — Codex Handoff V2

**Date:** 26 October 2026  
**Status:** Replacement for the previous `CODEX_HANDOFF_MUSEUM.md` and its first-phase rule-selector implementation.  
**Research framing:** Symbolic logical deduction for museum next-topic guidance, evaluated against a KG-similarity recommender inspired by Liu et al. (2022) and a direct LLM.

> **Implement runnable software.** Do not respond with only a plan. Complete and test one phase before proceeding. See `AGENTS.md`, `docs/REVISED_ARCHITECTURE.md` and `docs/EVALUATION_PROTOCOL.md`.

## 0 — Decisions already settled; do not reinterpret

1. **Museum knowledge source:** ArtGraph v1.0 RDF (Castellano et al., Zenodo record 6337958). Start with a connected, tractable, **actual** RDF-derived subgraph. Original RDF is not itself a learning prerequisite graph.
2. **Deduction language:** **SWI-Prolog** (function-free Horn clauses/logic programming), called by **Python**. SWI-Prolog performs unification, rule execution, recursive inference and candidate derivation. Python does **not** reimplement these predicates with if/else graph traversal.
3. **Integration:** Python 3.11+; `rdflib` for RDF, `pytest` for Python tests, SWI-Prolog `plunit` for rule tests; JSON messages over a controlled, stateless `swipl` subprocess interface for the first version. This makes every turn recompute its deductions from the current visitor state, avoiding stale tabling and shared-state contamination. Test subprocess stderr and exit status, enforce timeouts. All Prolog inputs must be whitelisted IDs or safely serialized data—**never interpolate raw visitor language into executable Prolog queries**. Do not require SWI-native Python bindings for MVP.
4. **Visitor state:** A finite known-topic set, interest/goal IDs, previously presented and skipped topics. On the **finite candidate universe**, any eligible topic not recorded as known can be treated as **not yet covered** (closed-world policy for guidance). Never claim this proves visitor ignorance or implies objective museum facts are false.
5. **Next topic is a recommendation, not a diagnosis.** Build recommendations from inferred contextual relevance and, where independently annotated, learning prerequisites. Do not convert arbitrary KG edges into educational prerequisites by fiat.
6. **Comparison systems:** (A) Prolog deduction, (B) **paper-inspired** KG-embedding/similarity baseline, (C) direct LLM. All must recommend from identical predeclared candidate topic IDs under a shared evaluation scenario, and expose recommendation scores or rationale where possible. **Do not claim exact reproduction of Liu et al.** Their system recommends art objects and models weighted interests; ours adapts the idea to a common next-topic task.
7. **LLM responsibility:** parse utterances into *proposed* visitor facts and optionally phrase system responses; **never select the symbolic system's next topic**. For direct-LLM baseline, the model itself selects the next topic.
8. **Research quality:** Use traceable museum facts, defined Horn clauses, at least three nontrivial multi-rule deductions, independent scenario labels and ablations. A chat interface is optional; a command-line demo is required.
9. **Course timing:** Presentation week of 9 November 2026, report due 13 November 2026. Work division from proposal: Chen Chi = logic/backend, Song Bingxi = LLM adapter/frontend; share evaluation.

## 1 — What changed from V1

| Topic | Old handoff (withdrawn) | New implementation (mandatory) |
|---|---|---|
| Source | Illustrative JSON prerequisite DAG | Real ArtGraph RDF subset + typed, provenance-tracked facts |
| Inference | Python dependency walk + `if status` | Prolog definite clauses, variables, unification, backward rule proving |
| Visitor state | 4 statuses, unknown never false | Closed-world *guidance* over eligible topics, explicit known/uncovered; optional contradicted evidence handling |
| Output | `ASK` / `EXPLAIN` of first prerequisite | Ranked or deterministically prioritized **next-topic candidates** with real derivation evidence |
| Baselines | Direct LLM only | KG-embedding/similarity (paper-inspired) **and** direct LLM; trivial KG-neighbor ablation advisable |
| Evaluation | Scripted 3-turn examples | Symbolic entailment tests + separately annotated recommendation-quality scenarios + scaling/ablation |
| UI | Streamlit milestone | Optional, no effect on inference method |

## 2 — Stack and repository layout

```text
museum-logic-guide/
  AGENTS.md
  CODEX_HANDOFF_MUSEUM_V2.md
  README.md
  pyproject.toml
  .env.example
  docs/
    REVISED_ARCHITECTURE.md
    EVALUATION_PROTOCOL.md
    dataset_manifest.json
    rulebook.md                     # every inference/guidance rule and justification
  scripts/
    inspect_artgraph.py             # counts, schema, type diagnostics
    extract_subgraph.py             # deterministic seed, RDF -> validated topic universe
    export_prolog_facts.py          # actual RDF triples -> safe .pl data
  data/
    samples/                        # small, licensed/synthetic test fixtures only
    curated/                        # selected real triples and sources; respect licenses
    raw/                            # gitignored: downloaded ArtGraph archives
  logic/
    museum_rules.pl                 # multi-hop factual deductions
    visitor_rules.pl                # relevance and candidate derivations
    io_runner.pl                    # safe JSON input/output wrapper
    tests/test_rules.pl             # plunit
  museum_guide/
    domain.py                       # typed IDs / state / candidate contracts
    artgraph.py                     # rdflib processing and provenance
    prolog_bridge.py                # subprocess IPC; no Python logical selector
    state.py                        # validated, per-session visitor observations
    extraction.py                   # language -> proposed state updates
    pipeline.py                     # orchestration
    render.py                       # source-grounded text
    baseline_embeddings.py          # independent KG similarity baseline
    baseline_llm.py                 # independent direct-model baseline
    cli.py
  evaluation/
    scenarios.jsonl                 # independently reviewed labels
    runner.py
    metrics.py
  ui/app.py                          # optional Streamlit
  tests/
    test_dataset.py
    test_prolog_bridge.py
    test_state.py
    test_isolation.py
    test_baselines.py
    test_evaluation.py
```

## 3 — Core contracts (freeze in Phase 0)

* `Topic`: `{id, type, label, source_uri, properties}`; `type ∈ {artwork, artist, movement, style, genre, medium}` for MVP. `topic_id` stable, never generated from unchecked free text. Candidate universe can be narrowed by scenario; clarify whether artworks are *seeds only* or *eligible recommendations*. Default: artwork allowed as the **visitor goal**, but recommend *explanatory topics* (`artist`, `movement`, `style`, `genre`, `medium`) for all three systems.
* `Fact`: `{predicate, args, source_triple_id/source_uri, provenance}`. `Provenance` identifies a genuinely imported ArtGraph triple or a clearly labeled manually curated rule. Preserve original RDF predicate URI.
* `VisitorState`: `{session_id, goal_id, known_topic_ids, presented_topic_ids, skipped_topic_ids, recent_turns}`. Updates can add/remove known topics; recompute deductions from scratch per CLI invocation or per turn. State is session-only.
* `Candidate`: `{topic_id, action:"RECOMMEND", rank, support:{derived_predicate, rule_ids, fact_ids, proof_steps}, method}`. The symbolic candidate must be supported by one or more actual rule applications; distinguish proof validity from educational usefulness.
* `RecommendInput`: `{scenario_id, goal_id, known_topic_ids, skipped_topic_ids, allowed_candidate_ids, context_snapshot_id}`; the same **closed set of candidate IDs** is supplied to all systems; baseline model prompts include the same authorized museum fact slice, not hidden label answers or Prolog deductions.
* `RecommendOutput`: `{method, ranked_topic_ids, candidate_details, runtime_ms, metadata, errors}`. For direct LLM, add provider/model/version/seed/temperature/token counts when available.
* `StateDelta`: strictly validated `add_known`, `remove_known`, `set_goal`, `skip`, optional `confidence`/`uncertainty`. Language extraction may propose IDs only from an allowlist; do not allow code/rule creation.

### Exactly what is deducted

**Museum-domain deductions**: e.g., artwork created by artist; artist member of movement → movement context of artwork; artworks with the same artist/related style/genre; indirect contextual connection requiring two or more joins. **Do not assume a factual association is automatically a prerequisite.**

**Visitor-guidance deductions**: relevant context of the selected goal; eligible candidates filtered by currently known/presented/skipped status under a closed-world **guidance** interpretation; optionally follow a small *independently justified* `learning_prerequisite/2` rule subset. Choose/score among entailed candidates with an explicitly documented stable priority (not an LLM).

**Prolog example (illustrative only; do not assert these as real ArtGraph facts):**

```prolog
:- table artwork_movement/2.
artwork_movement(W, M) :- created_by(W, A), belongs_to_movement(A, M).

relevant_topic(V, M) :- goal_artwork(V, W), artwork_movement(W, M).
% Use nonvar-ground checks before negation-as-failure on the finite candidate set.
candidate_topic(V, T) :- relevant_topic(V, T), allowed_candidate(T), \+ knows(V, T), \+ skipped(V, T).
```

This is **not enough on its own** to satisfy the core depth target: add other typed rules, multi-hop joins, nontrivial interacting derivations, and tests. Prolog's standard top-down execution is SLD-style backward chaining; `:- table ...` enables goal-directed tabled evaluation (SLG). Do **not** claim a custom forward-chaining engine was implemented unless one actually is; optional separate bottom-up materialization is permitted for comparative analysis. Proof explanations require a purpose-built proof wrapper or explicit provenance tracing, **not** merely printing Prolog's debug trace.

## 4 — Build phases (send one at a time to Codex)

### Phase 0: Real data audit, schemas and pilot proof

**Codex instruction:**

> Implement Phase 0 only. Verify ArtGraph v1.0 schema against https://zenodo.org/records/6337958, inspect actual RDF after download, log versions and provenance, and sample a reproducible connected subgraph around a known movement or artworks. Restrict imported predicates to a validated allowlist; make stable IDs and a topic catalog; export safe ground Prolog facts. Write `docs/dataset_manifest.json`, `docs/rulebook.md` with **proposed** deduction and guidance rules, and `docs/REVISED_ARCHITECTURE.md`. Create synthetic minimal fixtures for tests but never present them as ArtGraph data. Install-check `swipl` with `swipl --version` and implement one actual Prolog query on an imported or clearly marked sample. If dataset fetch or SWI install fails, report blocker accurately and finish the offline parsing tests. Do not build an LLM/UI.

**Exit gate:** At least 1 real sampled ArtGraph path verified with source triples; reproducible extraction; stable topic universe and candidate schema; dataset licence/source documented or unresolved explicitly flagged; one demonstrable Prolog deduction.

### Phase 1: Actual symbolic inference (primary CS3263 contribution)

**Codex instruction:**

> Implement actual SWI-Prolog source modules for museum facts and **several** typed Horn-clause deductions, plus visitor relevance and recommendations. Demonstrate unification over variables, recursive/multi-hop reasoning with cycle-safe tabling as needed, and sound query results over a finite rule set. Do not replace Prolog reasoning with Python adjacency traversal or Python status if-statements. Build an independently runnable Prolog test suite with plunit, and a JSON input/output command that returns entailed topic IDs and **proof provenance**. At least three benchmark tests must require two or more rule applications or rule joins and must fail if the logic clauses are replaced with simple 1-hop graph traversal. Add a negative test: a related artwork or style is **not automatically** a learning prerequisite unless a documented guidance rule warrants it. Use stateless invocation or explicitly clear tables after changes. Report exactly which rules fired; do not fabricate derivations.

**Exit gate:** `swipl` plunit tests pass; at least 3 correct multi-rule proofs with substitutions + source fact IDs; changing visitor-known set changes candidates; an unrelated/unsupported topic is not derived; 100% rule file is independent from LLM provider.

### Phase 2: Python orchestration and visitor updates

**Codex instruction:**

> Implement typed contracts and safe Python→Prolog JSON IPC with timeout, nonzero-exit handling, output validation and allowlisted IDs. Ensure per-session updates and stateless isolation; a visitor message is only parsed into a validated `StateDelta` (manual/fake LLM tests first). Add optional provider integration behind an interface. Keep source-backed response text; do not ask the LLM to select the hybrid recommendation. Build offline CLI that starts with a visitor goal, marks some topics as known, computes and explains a recommendation, updates known topics, and computes a different recommendation.

**Exit gate:** offline multi-round CLI with *real Prolog deductions*, no provider key; changing known-topic sets alters output; neither UI nor LLM hides deduction; tests work offline.

### Phase 3: Two scientifically separable baselines

**Codex instruction:**

> Implement a deterministic-seed knowledge-graph embedding/similarity recommender **inspired by Liu et al. (2022)**, using the same topic IDs and ArtGraph-derived graph. Explicitly document embedding method, interest aggregation, parameter choices and deviations from the paper. Do not claim access to original authors' code or reproduce their reported accuracy. Implement independent `direct_llm` selector constrained to the same allowed candidate IDs and museum information snapshot. Neither baseline may call Prolog's `candidate_topic` nor read its proof/rank as an input. Both return the same `RecommendOutput`; add anti-leakage tests, stable random seeds and full version tracking. Implement a simple graph-neighbor baseline only if time permits, as an ablation.

**Exit gate:** 3 systems callable on identical scenario candidate sets, no logic crossover, consistent output validation; mocked provider is clearly labeled non-evaluation.

### Phase 4: Evaluation and report artifacts

**Codex instruction:**

> Build a versioned, initially small dataset of independently reviewed visitor goals, known-topic sets, and *acceptable next-topic sets* based on actual ArtGraph facts plus annotated educational usefulness. Never derive gold labels by running the proposed rules. Include 1-hop/multi-hop, multi-interest, sparse/ambiguous, redundant/already-known, correction, and unsupported-rule cases. Design two tracks: (A) controlled algorithm comparison with a shared structured state and KG evidence; (B) end-to-end natural language evaluation where an LLM extracts the symbolic state and the raw LLM directly recommends. Report Recall@k / Hit@k or Precision@k for acceptable candidates, redundancy/unsupported recommendation rates, proof validity, extraction accuracy (track B), latency and qualitative errors. Keep results as actual raw JSONL/CSV, labeled with exact model, run config and reproducibility seeds. Add ablation `symbolic-no-multi-hop` or `symbolic-one-rule` to quantify value of deduction. Tests must check metric calculations and prevent impossible gold-label leakage.

**Exit gate:** valid, independently reviewed scenarios; evaluation tables created from genuine runs, not illustrative outputs; at least one documented failure of each approach; no scores invented.

### Phase 5: Presentation interface (optional)

**Codex instruction:**

> Create a thin Streamlit interface only after the CLI evaluation is working. The UI must show selected goal, visitor known topics, ranked next-topic recommendations for the three modes, and for Prolog the real rules/ArtGraph triples supporting the top result. Do not create fake narrative explanations without citations or let the UI apply its own recommendation logic. Update README with exact installation, raw data download, SWI-Prolog availability check, offline/online commands, report diagrams, limits and academic disclosure of Codex assistance.

**Exit gate:** repeatable CLI and evaluation are independent of UI; UI shows actual proof provenance and method labels; Windows installation instructions verified or caveated.

## 5 — Commands Codex should make real

```bash
swipl --version
python -m pip install -e '.[dev]'
python scripts/inspect_artgraph.py --input data/raw/artgraph-rdf.zip
python scripts/extract_subgraph.py --seed MOVEMENT_OR_ARTWORK_ID --output data/curated/subgraph.ttl
python scripts/export_prolog_facts.py --input data/curated/subgraph.ttl --output logic/generated_facts.pl
swipl -q -s logic/tests/test_rules.pl -g run_tests -t halt
pytest -q
python -m museum_guide.cli --mode symbolic --demo
python -m evaluation.runner --mode symbolic --scenarios evaluation/scenarios.jsonl
python -m evaluation.runner --mode embedding --scenarios evaluation/scenarios.jsonl
python -m evaluation.runner --mode direct_llm --scenarios evaluation/scenarios.jsonl  # configured API only
```

These are **required intended interfaces**, not claims the commands already exist. Codex must implement them or accurately document equivalent commands and run the supported ones.

## 6 — Research integrity, failure modes, and limits

- Museum RDF relations = factual evidence; rule-derived educational guidance = modeling/annotation. Document source of each rule separately from data source.
- `\+ knows(V,T)` means *not recorded as known under the finite closed-world guidance policy*, not that the visitor demonstrably lacks competence. Ground `T` first.
- Prolog inference alone is not proof of better educational recommendations. Independently annotate utility; keep logic-correctness and human-utility metrics separate.
- Do not introduce the original Liu et al. method as if an official reusable benchmark exists. Calling the KG similarity baseline **paper-inspired** is mandatory unless source code/data/evaluation protocol are independently verified.
- Small connected KG samples are legitimate, but sample-size and selection biases must be reported. Use real ArtGraph data for evaluation; synthetic fixtures are only for engineering tests.
- State changes invalidate prior tabled conclusions; stateless solver invocations avoid cross-turn leakage for MVP. Avoid invoking Prolog `consult` on untrusted input.
- No full OWL reasoning claim: function-free Horn-clause subset is the method, not general first-order completeness. If standard Prolog SLD resolution is used, do not claim custom forward chaining or generic resolution.
- No unsourced exhibit claims, user profiling beyond the session, secrets in commits, or undocumented AI assistance.

## 7 — Immediate kickoff prompt to send to Codex

> Read `AGENTS.md`, `CODEX_HANDOFF_MUSEUM_V2.md`, `docs/REVISED_ARCHITECTURE.md`, and `docs/EVALUATION_PROTOCOL.md`. This **V2 supersedes previous handoffs**. Implement **Phase 0 only**, producing actual code, a real ArtGraph RDF inspection/sample, and an initial runnable SWI-Prolog query. **Do not** implement a JSON-only prerequisite selector, a Python if/else logic engine, an LLM baseline, or UI at this stage. Freeze topic IDs, dataset provenance, and the JSON/Prolog integration boundary before Phase 1. Execute tests where tools/dependencies permit and report what is missing. Show changed files and verification commands. Do not progress to Phase 1 without review.

## Sources to cite in final report and implementation notes

- ArtGraph v1.0: https://zenodo.org/records/6337958 — Castellano et al., *Leveraging Knowledge Graphs and Deep Learning for Automatic Art Analysis*, 2022.
- Liu, Libbi & Rikhtehgar (2022): https://doi.org/10.3233/FAIA220215 — *What Would You Like to Visit Next? Using a Knowledge-Graph Driven Museum Guide in a Virtual Exhibition.* Architecture baseline, **not** a publicly verified turnkey benchmark.
- SWI-Prolog docs, Python integration: https://www.swi-prolog.org/pldoc/man?section=janus-call-prolog
- SWI-Prolog tabling: https://www.swi-prolog.org/pldoc/man?section=tabling

---
**Definition of done:** Actual ArtGraph facts → real Prolog multi-step deductions → reproducible visitor-aware next-topic recommendations; two independent baselines; shared, externally judged evaluation scenarios; source-linked explanations; reproducible tests. A visually polished chat frontend is not the definition of done.
