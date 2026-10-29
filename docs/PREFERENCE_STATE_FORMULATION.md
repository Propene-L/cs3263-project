# Phase 1.2 Preference-State Formulation

## Research task

Phase 1.2 evaluates visitor-state construction, not only question selection.
Each method receives the same validated multi-turn observation history and
independently constructs a provisional explanation before ranking the same
allowed next-action artworks.

The experiment asks whether contrastive and compositional reasoning can better
represent a controlled latent profile than atomic content matching. Controlled
profiles are benchmark definitions, not claims about a real person's
psychology.

## Inputs and separation of concerns

The symbolic input contains:

- stable visitor, observation, hypothesis, and artwork IDs;
- immutable likes/dislikes, explicit atomic or conjunction statements,
  explanation denials, and chronological corrections;
- a finite allowlist of action artworks;
- the frozen ArtGraph v1.0 evidence snapshot.

Museum facts, visitor observations, modeling assumptions, and derived
explanations remain separate. Raw visitor text is never executed as Prolog.
Deriving an explanation never mutates or deletes an observation.
Corrections mark an earlier observation as superseded in the authoritative
view while retaining both raw records. A clarification answer of `no` rejects
only the queried explanation; it does not ban every artwork containing a
component. A direct explicit rejection is a downstream artwork constraint.

## Explanation types

The API serializes provisional explanations as:

```json
{"kind": "atomic", "components": ["h_musical_subject"]}
```

or:

```json
{
  "kind": "all_of",
  "components": ["h_expressionist_style", "h_portrait_genre"]
}
```

`all_of` is modeled as a conjunction for controlled relevance. Predicting both
components as unrelated atomic interests is not treated as an exact
conjunction match.

## Evidence statuses

The Prolog layer distinguishes:

| Status | Operational meaning |
|---|---|
| `candidate` | At least one liked observation has recorded support and no disliked observation does. |
| `mixed` | Recorded support occurs in both liked and disliked observations. |
| `reinforced` | At least two independent liked observations support the hypothesis and no disliked observation does. |
| `interaction_candidate` | A liked example supports both components and separate disliked examples support one component each. |
| `explicitly_confirmed` | A validated explicit visitor observation names the hypothesis. |
| `explicitly_rejected` | A validated explicit visitor observation rejects the hypothesis. |

These are discrete evidence statuses, not probabilities.

## Contrastive and interaction assumptions

`a_bounded_recorded_support_contrast` states that recorded support on liked
versus disliked examples may be diagnostically useful inside the bounded
snapshot. Missing support is serialized as `not_recorded`; it never becomes a
negative ArtGraph fact.

`a_component_rejection_can_suggest_interaction` permits this provisional
pattern:

```text
liked L supports H1 and H2
disliked D1 supports H1; H2 is not recorded
disliked D2 supports H2; H1 is not recorded
------------------------------------------------
interaction_candidate(all_of(H1,H2))
```

Allowed cross-type schemas are deliberately narrow:

- subject/tag + style;
- subject/tag + genre;
- style + genre.

Medium/movement conjunctions are not automatically introduced. This is a
modeling choice intended to limit arbitrary parameter growth, not a logical
theorem about preferences.

## Action ranking

The original v1 experiment gave any inferred interaction overriding score
1000 and disabled atomic fallback. That policy is retained only in
`preference_state_rules.pl` for historical reproduction.

Corrected v2 uses the following deterministic policy:

1. Explicitly rejected atomic or conjunction interests exclude matching
   recommendation candidates. Explanation denials produced by clarification
   do not exclude artworks.
2. Explicit confirmations outrank provisional evidence. An inferred
   interaction cannot replace confirmed independent atomic interests.
3. A unique reinforced interest can justify a recommendation. Candidate,
   mixed, or provisional interaction evidence requires clarification.
4. Declared incomplete evidence produces `insufficient_evidence`; interaction
   inference is disabled because `not_recorded` is unreliable in that view.
5. Eligible artworks are ordered lexicographically by explicit matches, total
   positive-explanation matches, then stable artwork ID. These are ordinal
   rules, not confidence scores or probabilities.

Clarification asks whether one explicit atomic or conjunction explanation is
correct. The controlled response model answers `yes`, `no`, or `unsure` by
membership in the declared profile, appends the answer as a new observation,
and runs inference again. It is a test oracle, not a model of human behavior.

Atomic Prolog preserves the Phase 1 positive-only behavior as an ablation.
The Python positive-accumulation and signed-additive baselines independently
construct their states from exported evidence and never read Prolog output.
The interaction-capable Python comparator independently implements the same
corrected formal policy. Its equality with Prolog measures representation
equivalence; differences between those two implementations would indicate an
engineering defect, not a research advantage.

Action relevance is evaluated independently from proof validity using the
scenario's controlled latent profile:

```text
atomic(H):       relevant(A) iff recorded_support(A,H)
all_of(H1,H2):   relevant(A) iff recorded_support(A,H1) and recorded_support(A,H2)
```

This evaluates consistency with the declared benchmark model only.
