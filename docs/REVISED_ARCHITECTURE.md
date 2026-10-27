# Revised Architecture and Semantics

## Phase 1 research problem

Phase 1 supersedes the earlier prerequisite/next-topic objective. Given a
finite ArtGraph-derived fact set `F`, documented Horn clauses `R`, provisional
visitor-interest hypotheses `H`, and session state `S`, select two allowlisted
artworks whose predicted pairwise responses distinguish as many hypotheses as
possible under a declared response model. Hypotheses remain provisional and
revisable; this is not a psychometric diagnosis.

## Operational architecture

1. Official ArtGraph RDF is checksum-verified, audited, and converted into a
   bounded provenance-bearing fact snapshot.
2. Stable topic IDs and an identical candidate universe are shared by the
   symbolic, KG-similarity, and direct-LLM systems.
3. Validated visitor observations, finite hypotheses, allowed artwork IDs,
   prior questions, and corrections are passed to a fresh SWI-Prolog process.
4. Prolog derives hypothesis evidence, response predictions, discrimination,
   pair eligibility, deterministic selection, and structured proof trees.
5. Python validates IDs/output, manages isolated sessions, and evaluates
   results. It does not recreate symbolic eligibility or discrimination.
6. An optional LLM may propose allowlisted observations or phrase the selected
   question, but never overrides the symbolic artwork pair.

RDF extraction may use deterministic breadth-first traversal to create the
finite sample. This preprocessing operation is not the deduction engine.

## Frozen Phase 0 contracts

- `Topic`: `{id,type,label,source_uri,properties}` where type is one of
  `artwork|artist|movement|style|genre|medium`. Artworks may be goals; default
  recommendation candidates are the five explanatory types.
- `Fact`: `{predicate,args,source_triple_id,source_uri,provenance}`.
- `VisitorState`: session, goal, known/presented/skipped topic IDs, and recent
  turns.
- `Candidate`: stable topic ID, `RECOMMEND`, rank, method, and proof support
  containing rule IDs and imported fact IDs.
- `RecommendInput`: scenario, goal, known/skipped IDs, allowed candidate IDs,
  and context snapshot ID.
- `RecommendOutput`: method, ranked IDs, details, runtime, metadata, errors.
- `StateDelta`: allowlisted additions/removals, goal change, skips, confidence,
  and uncertainty. It cannot create rules or RDF facts.

These remain regression contracts. Phase 1 introduces separate
`ClarificationObservation`, `AskedQuestion`, and `ClarificationState` types;
it does not silently repurpose `RecommendInput` or `Candidate`.

## Phase 1 clarification contract

- Input: session ID, validated observations, allowlisted artwork IDs,
  previously asked pairs/responses, rejected hypotheses, and solver mode.
- Output: selected pair or `no_discriminative_question`, active hypotheses,
  predicted responses, rule/assumption IDs, a nested proof tree, exact ArtGraph
  fact IDs, and secondary recommendations from remaining hypotheses.
- Responses: `prefer_a`, `prefer_b`, `neither`, or `unsure`; only a determinate
  opposite prediction contradicts a hypothesis.
- Corrections replace the earlier response before a fresh stateless solve.

## Semantics

Factual ArtGraph associations and educational guidance are distinct. A style,
genre, artist, movement, or medium related to an artwork is contextual evidence,
not automatically a learning prerequisite. On the finite allowed candidate set,
absence from `K` can mean “not recorded as covered” for filtering; it never
proves ignorance or a negative museum fact.

SWI-Prolog's clauses use goal-directed resolution and unification. Phase 1 may
use tabling for cycle-safe recursion. Proof output must be purpose-built from
rule IDs, substitutions, and imported `agf_*` facts—not an English summary or
the debugger trace. A fresh subprocess per state avoids stale tables and
cross-session leakage.

## Scope limits

- Function-free Horn-clause logic programming, not a general FOL/OWL reasoner.
- No claim that logical correctness establishes educational usefulness.
- No raw visitor language interpolated into Prolog.
- No frontend, LLM integration, baselines, or full recommendation policy in
  Phase 0.

