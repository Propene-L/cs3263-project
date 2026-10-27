# Phase 0.75 — Interest-Inference Logic Design

## 1. Revised objective

The symbolic system recommends artworks, not prerequisite topics. A visitor
observation supplies evidence; SWI-Prolog derives typed interest signals and
eligible candidate artworks; deterministic ranking orders only the entailed
candidates. The LLM may later extract allowlisted observations or render a
response, but it may not select the symbolic recommendation.

The system is a transparent hypothesis generator, not a psychometric or
probabilistic model.

## 2. Visitor-state semantics

```prolog
visitor_observation(ObservationID, Visitor, Kind, ArtworkID).
```

Allowed pilot `Kind` values are:

| Kind | Meaning | Interest consequence |
|---|---|---|
| `knows` | Visitor reports familiarity | Weak positive signal under an explicit assumption |
| `likes` | Visitor explicitly appreciates the artwork | Strong positive signal |
| `dislikes` | Visitor explicitly dislikes the artwork | Separate negative signal |
| `viewed` | Artwork has already been presented/visited | Candidate filter only |
| `rejected` | Visitor rejected this candidate | Candidate-specific filter only |

Knowing an artwork never logically entails liking it. The rule
`r_weak_interest_from_familiarity` is deliberately named and exposed in every
proof so the assumption can be ablated.

## 3. Factual attribute representation

```prolog
artwork_attribute(Artwork, AttributeType, Value, FactIDs).
```

Direct attributes retain one imported `agf_*` fact. Movement is derived through
two imported facts:

```prolog
artwork_attribute(A, movement, M, [FCreated, FMovement]) :-
    created_by(A, Artist, FCreated),
    belongs_to_movement(Artist, M, FMovement).
```

This preserves the distinction between an artwork tag and an artist movement.
The pilot attribute types are `tag`, `style`, `genre`, `medium`, `series`,
`period`, and `movement`.

## 4. Interest-signal rules

Explicit positive signal:

```prolog
interest_signal(V, Type, Value, strong,
                signal(Obs, Artwork, Facts, r_interest_from_like),
                r_interest_from_like) :-
    visitor_observation(Obs, V, likes, Artwork),
    artwork_attribute(Artwork, Type, Value, Facts).
```

Assumption-driven familiarity signal:

```prolog
interest_signal(V, Type, Value, weak,
                signal(Obs, Artwork, Facts,
                       r_weak_interest_from_familiarity),
                r_weak_interest_from_familiarity) :-
    visitor_observation(Obs, V, knows, Artwork),
    artwork_attribute(Artwork, Type, Value, Facts).
```

Negative signal remains separate:

```prolog
negative_interest_signal(V, Type, Value,
                         signal(Obs, Artwork, Facts,
                                r_negative_interest_from_dislike)) :-
    visitor_observation(Obs, V, dislikes, Artwork),
    artwork_attribute(Artwork, Type, Value, Facts).
```

These rules establish only that the system has evidence for an interest
hypothesis. They do not establish a visitor's true preference.

## 5. Candidate rules

### R1 — two distinct attribute matches

```prolog
candidate_support(V, C, r_two_distinct_attribute_match, Observations, Facts) :-
    matched_signal(V,C,T1,X1,_,O1,_,_,Source1,Candidate1),
    matched_signal(V,C,T2,X2,_,O2,_,_,Source2,Candidate2),
    T1-X1 @< T2-X2,
    provenance_union(Source1,Candidate1,Source2,Candidate2,Facts),
    Observations = [O1,O2].
```

This rejects one-tag matching as sufficient. It remains a typed overlap rule,
so it is necessary but not by itself the main research contribution.

### R2 — repeated evidence plus a distinct attribute

```prolog
repeated_interest_signal(V,T,X,O1,A1,O2,A2) :-
    interest_signal(V,T,X,_,signal(O1,A1,_,_),_),
    interest_signal(V,T,X,_,signal(O2,A2,_,_),_),
    dif(A1,A2), O1 @< O2.

candidate_support(V,C,r_repeated_signal_plus_distinct_attribute,Obs,Facts) :-
    repeated_interest_signal(V,T1,X1,O1,_,O2,_),
    artwork_attribute(C,T1,X1,_),
    matched_signal(V,C,T2,X2,_,O3,_,_,_,_),
    dif(T1-X1,T2-X2),
    Obs = [O1,O2,O3].
```

R2 requires two distinct visitor-evidence artworks, an inferred repeated
interest, and another matched attribute. A simple one-seed nearest-neighbour
lookup cannot satisfy this proof structure, although an engineered weighted
overlap algorithm could emulate its ranking behavior. That is why the raw
overlap ablation remains essential.

### R3 — conservative negative conflict

```prolog
strong_negative_conflict(V,C,
    conflict(r_two_negative_attribute_matches,Obs,Facts)) :-
    negative_match(V,C,T1,X1,O1,_,_,_),
    negative_match(V,C,T2,X2,O2,_,_,_),
    T1-X1 @< T2-X2,
    Obs = [O1,O2].
```

The pilot blocks a candidate only after two distinct negative matches. This is
a heuristic policy, not a museum fact. It may overgeneralize a disliked work,
so production behavior needs user study or review.

### R4 — state filters

```prolog
candidate_artwork(V,C) :-
    allowed_artwork(C),
    candidate_support(V,C,_,_,_),
    \+ excluded_candidate(V,C,_,_),
    \+ strong_negative_conflict(V,C,_).
```

Candidates are grounded in the finite allowlist before negation. `viewed` and
`rejected` are session-specific filters; they do not alter ArtGraph facts.

## 6. Proof contract

Every `candidate_recommendation/4` result contains:

- final artwork ID;
- applied candidate rule IDs;
- visitor-observation IDs;
- inferred signal records and strengths;
- typed matched attributes;
- source-artwork fact IDs;
- candidate-artwork fact IDs;
- deterministic score.

Raw visitor text is never consulted or executed. Only allowlisted atoms appear
in the pilot facts.

## 7. Ranking policy

The pilot score is calculated in Prolog after eligibility:

```text
score = 10000 × explicit-positive observations
      + 1000  × distinct supporting artworks
      + 100   × distinct matched attributes
      + 10    × applicable candidate rules
      + typed-specificity weights
```

Type priorities are Style/Movement 5, Genre/Series 4, Period 3, Tag 2, and
Medium 1. This is a deterministic policy—not a probability or learned weight.

For production, the recommended boundary is:

1. Prolog derives eligibility, proof paths, and evidence features.
2. Python validates Prolog output and may apply the frozen deterministic rank
   policy to entailed candidates only, as allowed by `REVISED_ARCHITECTURE.md`.
3. The identical rank policy and candidate set are versioned for evaluation.

Keeping ranking outside the logical clauses can make ablations easier, but
Python must never recreate `candidate_artwork/2` through graph traversal or
conditional rules.

## 8. Beyond ordinary attribute overlap

The pilot offers behavior beyond a one-tag matcher through:

- evidence strength: explicit liking versus assumption-labeled familiarity;
- repeated signals that require multiple source artworks;
- indirect movement attributes requiring Artwork → Artist → Movement;
- multiple independent rule proofs for one candidate;
- explicit negative evidence and candidate-specific rejection;
- provenance joining visitor observations to original `agf_*` facts.

Nevertheless, the core factual operation is still typed attribute matching.
Claims of a research advantage require ablations against raw overlap and
single-rule Prolog; proof transparency alone does not establish better
recommendation relevance.

## 9. Contract migration plan

The old contracts should not be silently repurposed. Proposed migration:

1. Keep `Topic` and `Fact`; add `Tag` to `TopicType` while preserving stable
   IDs and provenance.
2. Replace goal-oriented `VisitorState` with an artwork-observation collection
   containing observation ID, artwork ID, kind, and optional extraction
   confidence. Preserve session isolation.
3. Change `Candidate.topic_id` to an explicit `artwork_id`, or introduce a
   method-neutral `RecommendationItem` whose type is always `artwork` for this
   study.
4. Replace `RecommendInput.goal_id/known_topic_ids` with structured
   `visitor_observations`, `viewed_artwork_ids`, `rejected_artwork_ids`, and a
   shared `allowed_artwork_ids` universe.
5. Keep `RecommendOutput`, but require proof observations, signals, rule IDs,
   and ArtGraph facts for the symbolic method.
6. Version the contract rather than breaking Phase 0/0.5 regression fixtures.
7. Update `REVISED_ARCHITECTURE.md` and `EVALUATION_PROTOCOL.md` only after
   human approval of this investigation.

