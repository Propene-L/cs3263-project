# Phase 0.75 — Interest-Inference Investigation Review

## Outcome

ArtGraph supports a bounded, interest-based artwork recommendation prototype.
It provides enough tag coverage, typed categorical attributes, cross-artist
overlap, and provenance-bearing multi-step paths to test the architecture.
It does not provide ground-truth visitor interests, calibrated probabilities,
or evidence that more matching tags produce a better human recommendation.

The proof-of-concept is intentionally limited. It does not implement a full
Phase 1 service, conversational LLM adapter, frontend, embedding baseline, or
direct-LLM baseline.

## Candidate-dataset comparison

| Candidate | Strength | Main concern |
|---|---|---|
| Musical instrument, 188 works / 138 artists | Highest artist diversity; 24 styles, 13 genres, 41 movements; clear cross-artist examples | Instrument taxonomy creates correlated tag inflation |
| Nature reserve, 199 / 78 | Dense landscape evidence and movement/style joins | Very redundant forest/nature taxonomy; 14.45 links per work |
| Water transportation, 188 / 114 | Strong cross-artist boat/water subject paths | Vehicle/watercraft taxonomy redundancy |
| Felidae, 198 / 78 | Specific animal subject with style/genre diversity | Zoological tags may dominate artistic attributes |
| Village, 197 / 89 | Landscape/cityscape variation and movement diversity | Broad subject anchor; oil/canvas matches dominate |

Recommendation: adopt the Musical instrument universe for the next reviewed
development phase and retain Morris Louis as a regression snapshot.

## Five real-data scenarios

The structured inputs and descriptive overlap profiles are stored in
`docs/interest_inference_scenarios.json`.

1. **Single familiarity:** `ag_10472` Study for The Cellist. Familiarity yields
   weak signals. Prolog recommends `ag_37634` The Cellist (Serevitsch) with
   `r_two_distinct_attribute_match`, one observation ID, and 24 imported fact
   IDs. Score: 2237.
2. **Repeated familiarity:** `ag_10472` plus `ag_37634`. Prolog recommends
   `ag_70351` The Cello Player. Both
   `r_repeated_signal_plus_distinct_attribute` and
   `r_two_distinct_attribute_match` fire, supported by two observation IDs and
   34 imported facts. Score: 3242.
3. **Explicit positive preference:** liking `ag_10472` produces `strong`
   signals rather than the weak familiarity assumption. The same leading
   candidate receives a higher deterministic score (12237), not a higher
   probability.
4. **Positive and negative evidence:** liking `ag_10472` while disliking
   `ag_70351` creates separate positive and negative signals. The conservative
   two-negative-attribute conflict reduces the eligible universe to six in
   this pilot and changes the top candidate to `ag_102988`. This dramatic
   change shows that negative generalization needs human review.
5. **Rejected candidate:** the repeated-familiarity scenario initially admits
   `ag_70351`. Adding `obs_filtered_rejected_1` excludes it without modifying
   museum facts; the next top result becomes `ag_11268` The Cellist (Portrait
   of Upaupa Scheklud), score 3142.

These are executed proof-of-concept outputs, not relevance labels or
experimental scores.

## Real proof excerpt

For Scenario A:

```text
source:    ag_10472 Study for The Cellist
candidate: ag_37634 The Cellist (Serevitsch)
rule:      r_two_distinct_attribute_match
visitor observation: obs_single_known_1

shared tag ag_3236 Musical instrument:
  source fact    agf_8e49e33270d2ff0f08d3
  candidate fact agf_6874fdb88122b2574ed8

shared style ag_21 expressionism:
  source fact    agf_8df98244fec9bec2de1b
  candidate fact agf_a68e7fc478bb3905e696
```

The full JSON proof additionally includes genre, media, and taxonomy-related
tag matches.

## Logic versus heuristics

Factual deductions:

- imported `about`, style, genre, medium, series, and period relations;
- derived Artwork → Artist → Movement relations;
- the existence of matching typed attributes;
- exclusion of an explicitly identified viewed/rejected artwork.

Modeling assumptions:

- familiarity supplies weak positive interest evidence;
- liking transfers to all recorded attributes of the artwork;
- two distinct matches are sufficient for eligibility;
- repeated evidence is stronger than one observation;
- two negative matches justify a candidate conflict;
- the deterministic type weights represent desirable ranking priorities.

No assumption is presented as an ArtGraph fact or visitor truth.

## Fair baseline comparison

All systems should receive:

- identical structured visitor observations;
- the same 188 allowed artwork IDs;
- the same authorized ArtGraph snapshot;
- identical viewed/rejected filters;
- no system-generated gold labels.

Required ablations:

1. **Raw attribute overlap:** count typed shared attributes, with no Prolog
   interest rules.
2. **Single-rule Prolog:** `r_two_distinct_attribute_match` only.
3. **Multi-rule Prolog:** add repeated evidence, strength, negative conflict,
   and indirect movement.
4. **KG embedding similarity:** paper-inspired, same graph/candidate universe,
   deterministic seed.
5. **Direct LLM:** same authorized fact slice and IDs, no Prolog proofs or
   gold labels.

Evaluation must separate recommendation relevance, cross-artist diversity,
evidence-backed explanation rate, already-viewed/rejected rate, logical proof
correctness, and runtime. Independently reviewed acceptable-recommendation
sets are required before calculating Hit/Recall/Precision@k or MRR.

## Risks

- The logic may be ordinary weighted attribute overlap expressed declaratively.
- Tag taxonomy produces correlated evidence and inflated proof length.
- The anchor-tag universe makes one attribute universal and therefore
  nondiscriminative.
- Broad media such as oil/canvas can swamp more meaningful signals.
- Negative transfer from one disliked work is especially brittle.
- Artist-level movement transfer may overgeneralize across an oeuvre.
- Dataset labels and classifications have not been independently verified by
  an art historian.
- ArtGraph licensing remains unresolved for redistribution beyond the bounded
  textual snapshot.

## Required changes before production implementation

1. Approve the artwork-recommendation objective and versioned contract
   migration in `INTEREST_INFERENCE_DESIGN.md`.
2. Decide whether familiarity should create any positive signal by default.
3. Decide whether correlated tag families require a curated hierarchy or
   frequency-based down-weighting.
4. Approve or replace the negative-conflict rule.
5. Freeze the common candidate universe and ranking policy before baselines.
6. Add safe stateless JSON IPC; never interpolate visitor text into Prolog.
7. Create independent development/test relevance labels before tuning.
8. Measure raw-overlap and single-rule ablations before claiming benefit from
   compositional logic.

## Review gate

Phase 0.75 establishes feasibility and a runnable pilot. The complete Phase 1
system must not begin until the human reviewer approves the new objective,
development universe, state semantics, and assumption-driven rules.

