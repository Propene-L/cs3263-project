# Phase 0 Rulebook

This rulebook separates imported ArtGraph facts, factual Horn-clause
deductions, and proposed educational guidance assumptions. Only the Phase 0
pilot context rules are currently implemented. A valid factual entailment is
not, by itself, evidence that a topic is educationally useful.

## Imported fact predicates

Every imported relation is ground and carries a deterministic `agf_*` source
triple ID. `source_fact/5` retains the normalized predicate, subject/object,
and original RDF predicate URI; `fact_snapshot/2` and `source_dataset/2` link
that fact to the extracted snapshot and the official Zenodo record.

| Prolog predicate | Original RDF predicate | Meaning in this project |
|---|---|---|
| `created_by(W,A,F)` | `artgraph:createdBy` | ArtGraph states artwork W was created by artist A. |
| `has_style(W,S,F)` | `artgraph:hasStyle` | ArtGraph associates artwork W with style S. |
| `has_genre(W,G,F)` | `artgraph:hasGenre` | ArtGraph associates artwork W with genre G. |
| `made_of(W,M,F)` | `artgraph:madeOf` | ArtGraph associates artwork W with medium/material M. |
| `belongs_to_movement(A,M,F)` | `artgraph:belongsToMovement` | ArtGraph associates artist A with movement M. |
| `rdf_type/3`, `rdf_label/3` | RDF type and ArtGraph name/title | Type and display metadata with source IDs. |

The populated fact predicates differ from two names in the bundled ontology:
facts use `madeOf`/`belongsToMovement`; the ontology declares
`madeFrom`/`belongToMovement`. The importer intentionally follows the facts and
records this mismatch in the dataset manifest.

## Implemented Phase 0 factual context rules

These rules are in `logic/pilot_rules.pl`. They derive contextual topics, not
learning prerequisites.

| Rule ID | Horn-clause reading | Status |
|---|---|---|
| `r_context_artist` | `created_by(W,A) -> artwork_context(W,A)` | Implemented and tested with real sample. |
| `r_context_style` | `has_style(W,S) -> artwork_context(W,S)` | Implemented and tested with real sample. |
| `r_context_genre` | `has_genre(W,G) -> artwork_context(W,G)` | Implemented and tested with real sample. |
| `r_context_medium` | `made_of(W,M) -> artwork_context(W,M)` | Implemented and tested with real sample. |
| `r_context_movement_via_artist` | `created_by(W,A) AND belongs_to_movement(A,M) -> artwork_context(W,M)` | Implemented as a two-join pilot rule; not exercised by seed 8142 because its sampled artist has no imported movement edge in the bounded sample. |

Each proof returns its rule ID and exact imported fact IDs. Prolog supplies
unification and resolution; Python only validates input IDs, invokes SWI-Prolog,
and validates JSON output.

## Proposed Phase 1 factual rules

These are proposals, not implemented or evaluated in Phase 0:

1. `shared_style(W1,W2,S)` from two `has_style` facts, with `dif(W1,W2)`.
2. `shared_genre(W1,W2,G)` from two `has_genre` facts.
3. `artist_movement_context(W,M)` from `created_by(W,A)` joined with
   `belongs_to_movement(A,M)`; the pilot clause needs real-sample coverage.
4. A cycle-safe, tabled contextual connection predicate over an explicitly
   whitelisted relation set, with bounded proof reconstruction.

Rules must retain all supporting fact IDs and must not infer facts absent from
their premises.

## Proposed visitor-guidance rules — educational assumptions

The following rules encode policy or educational assumptions rather than
objective ArtGraph facts. They require independent team review and scenario
annotation before Phase 1 implementation:

- A factually related artist/style/genre/medium may be an eligible explanatory
  topic for an artwork goal.
- Candidate filtering may exclude topics recorded as known, presented, or
  skipped under a finite closed-world guidance policy. “Not recorded as known”
  must never be phrased as proven ignorance.
- A deterministic ranking may prefer relation type, shorter proof, and stable
  topic ID. This ranking is a design policy, not a theorem.
- No `learning_prerequisite/2` fact will be derived from arbitrary ArtGraph
  edges. Any such facts require separate human annotation, justification, and
  provenance.

## Explicit non-rules

- Same artist/style/genre does not imply an educational prerequisite.
- `made_of` does not imply visitor familiarity with a technique.
- Missing RDF edges are not negative museum facts.
- A Prolog proof establishes consequence under the imported facts and clauses;
  it does not establish recommendation utility or learning gain.

## Phase 0.5 readiness additions

Phase 0.5 adds imported `has_subject/3`, `has_period/3`,
`part_of_series/3`, and `related_to_school/3` facts. Subject, Period, Series,
and Training are typed context entities but remain outside the default shared
recommendation candidate set.

`logic/phase_0_5_pilot_rules.pl` feasibility-tests derived
`artwork_movement/4`, shared-style/series peers, artwork training context, and
tabled contextual reachability over the real Morris Louis sample. These are
Layer A factual/context rules only. The separately proposed Layer B visitor
eligibility rule and all rule justifications are documented in
`PHASE_0_5_REVIEW.md`. They are not the production Phase 1 engine.

## Phase 0.75 visitor-interest proof of concept

`logic/interest_poc.pl` imports typed `about`/Tag facts and treats style,
genre, medium, series, period, and the Artwork → Artist → Movement join as
typed artwork attributes. The following rules execute in SWI-Prolog over the
bounded real-data snapshot, but remain proposals pending the Phase 0.75 review:

| Rule ID | Reading | Classification |
|---|---|---|
| `r_interest_from_like` | A liked artwork supplies strong positive signals for its recorded attributes. | Visitor-model assumption |
| `r_weak_interest_from_familiarity` | A known artwork supplies weak positive signals. | Visitor-model assumption |
| `r_negative_interest_from_dislike` | A disliked artwork supplies negative attribute signals. | Visitor-model assumption |
| `r_two_distinct_attribute_match` | An unseen artwork matching at least two distinct typed attributes is eligible. | Guidance assumption |
| `r_repeated_signal_plus_distinct_attribute` | Evidence from two source artworks plus two distinct attributes is an additional eligibility proof. | Guidance assumption |
| `r_two_negative_attribute_matches` | Two matching negative attributes exclude a candidate. | Conservative guidance assumption |

The score is a deterministic, lexicographic-style policy encoded in Prolog;
it is not a probability or relevance judgment. Proofs return rule IDs,
visitor-observation IDs, typed matching attributes, and the exact `agf_*`
source fact IDs. Python only performs RDF analysis/export and does not select
recommendations. Full semantics and review questions are in
`INTEREST_INFERENCE_DESIGN.md` and `INTEREST_INFERENCE_REVIEW.md`.

