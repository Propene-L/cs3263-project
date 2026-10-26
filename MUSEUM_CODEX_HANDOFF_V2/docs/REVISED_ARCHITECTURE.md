# Revised Architecture and Semantics

## Research problem
Given (i) a finite ArtGraph-derived fact set `F`, (ii) a fixed, documented set of Horn clauses `R`, (iii) a visitor goal `g`, and (iv) a known-topic set `K`, derive a set of **supported and relevant next topics** `C(g,K)`, then apply a deterministic, documented ranking policy. The user wants a reference guide, **not** an objectively reliable psychometric diagnosis.

## What the project genuinely demonstrates

- **Logical reasoning:** Prolog predicate representation, variable unification/substitution, recursive/multi-rule backward deductions, optional tabled evaluation, evidence/proof reconstruction. These are operational inference steps, not merely Boolean flags.
- **RDF-to-logic transformation:** Selected ArtGraph triples become ground Prolog facts with stable ID/URI mappings. Other graph relationships are not blindly classified as prerequisites.
- **Visitor state reasoning:** Interpret `K` as confirmed/assumed covered topics, and `T \notin K` as a *candidate for guidance* under a finite closed-world policy. Do not assert the visitor literally lacks that knowledge.
- **Decision policy:** Logic derives all supported candidate topics; a separate transparent ordering chooses which one to present first. Prefer strongest relationship, then shortest evidence path or rule-based domain priority, then stable ID to break ties. This ordering is a policy, not a theorem.

## Formalization

Let `Topic` be a finite set of eligible candidate IDs derived from the actual dataset and kept identical for all baselines. Let `F` contain whitelisted ArtGraph triples reified as ground facts, and `R` contain safe function-free Horn rules. Let `Cl_R(F)` denote logical consequences supported by `R` and `F`. Given a visitor goal `g` and known topic IDs `K`, define:

`Relevant(g) = {t in Topic : relevant_topic(g,t) in Cl_R(F ∪ {goal(g)})}`

`Candidates(g,K) = Relevant(g) \ (K ∪ Skipped ∪ Presented)`.

Absence from `K` has the operational meaning *not recorded as covered*. Candidate filtering is over the finite allowed topic set, not unrestricted FOL negation. Record rule and imported fact provenance for each derived candidate. Be explicit that factual entailment and recommendation utility are different properties.

## Example rules (schematic; actual predicates require imported ArtGraph facts)

```prolog
:- table artwork_movement/2.
artwork_movement(W,M) :- created_by(W,A), belongs_to_movement(A,M).

% Context for a visitor's selected artwork, not a learning prerequisite.
relevant_to_goal(W,M) :- artwork_movement(W,M).
relevant_to_goal(W,S) :- has_style(W,S).
relevant_to_goal(W,G) :- has_genre(W,G).

candidate_topic(V,T) :-
    goal_artwork(V,W), relevant_to_goal(W,T),
    allowed_candidate(T), \+ knows(V,T), \+ skipped(V,T).
```

Add more nontrivial rules and tests that require conjunctive joins and chained deductions. Do not claim that styles, genres or movements are prior knowledge the visitor *must* possess; they are plausible contextual references. A manually annotated pedagogical `requires/2` predicate may be included only when validated separately.

## Interaction and flow

1. Offline real ArtGraph RDF → controlled extraction and provenance → logic fact file/topic manifest + same graph to embedding baseline.
2. User goal and known topics → Python state validator → safe Prolog subprocess JSON input.
3. Prolog evaluates grounded visitor facts + general museum clauses, returning candidate topics and proof evidence.
4. Python validates and ranks entailed candidates; never manufactures unsupported candidates.
5. Optional LLM turns output into grounded text; user correction updates `K` → fresh deduction next turn.
6. Independent KG embedding and direct LLM recommenders receive matching candidate IDs and comparable authorized museum context.

## Reasoning engine details

- SWI-Prolog's standard `:-` clauses support goal-directed rule execution using unification and resolution. Use cycle-safe tabling for recursion if applicable; Prolog documentation warns that cached results may become stale when facts change. A **fresh Prolog subprocess per turn** is preferred for the small extracted subgraph.
- The explanatory trace must show actual base fact IDs, applied rule IDs and substitutions. Build explicitly instrumented proof predicates if necessary. Do not equate an English paragraph with a proof.
- Avoid blind `assertz` with text from an LLM. Use a validated allowlist of IDs in a safe data channel and separate immutable rule code from mutable visitor facts.

## Scope guardrails

- Not a general first-order theorem prover or unrestricted OWL reasoner.
- Not required to write unification from scratch: using Prolog's inference machinery is the intended implementation; explicitly demonstrate it with tests and derivation traces.
- No claim to solve a visitor's actual knowledge state perfectly; treating uncovered as eligible is a project assumption.
- A polished interface, itinerary planning, long-term user profiles and unrestricted web retrieval are out of scope.
