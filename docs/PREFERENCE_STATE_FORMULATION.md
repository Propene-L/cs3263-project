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
- immutable `likes`, `dislikes`, `explicit_interest`, and
  `explicit_rejection` observations;
- a finite allowlist of action artworks;
- the frozen ArtGraph v1.0 evidence snapshot.

Museum facts, visitor observations, modeling assumptions, and derived
explanations remain separate. Raw visitor text is never executed as Prolog.
Deriving an explanation never mutates or deletes an observation.

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

In compositional mode, an available interaction explanation takes precedence;
an artwork receives support only when all components are recorded. Without an
interaction, a contrastive atomic component receives the main score and mixed
attributes receive a penalty so clean probes rank above high-overlap examples.

Atomic Prolog preserves the Phase 1 positive-only behavior as an ablation.
The Python positive-accumulation and signed-additive baselines independently
construct their states from exported evidence and never read Prolog output.

Action relevance is evaluated independently from proof validity using the
scenario's controlled latent profile:

```text
atomic(H):       relevant(A) iff recorded_support(A,H)
all_of(H1,H2):   relevant(A) iff recorded_support(A,H1) and recorded_support(A,H2)
```

This evaluates consistency with the declared benchmark model only.
