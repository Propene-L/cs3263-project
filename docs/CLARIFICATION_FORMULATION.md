# Phase 1 — Logic-Guided Active Preference Clarification

## Research task

The primary output is a clarification question, not a conventional nearest-
artwork recommendation. Given a finite ArtGraph snapshot, provisional visitor
hypotheses, and session constraints, SWI-Prolog selects two real artworks whose
recorded evidence causes competing hypotheses to predict different answers to:

> Which of these two artworks interests you more?

The hypotheses are revisable system hypotheses. They are not psychological
facts, diagnoses, probabilities, or claims that a visitor must like every
attribute of a known artwork.

## Finite model

Let:

- `A` be the 112 allowlisted artwork IDs;
- `H` be the ten reviewed typed hypothesis definitions;
- `F` be the 2,232 imported RDF triples with `agf_*` provenance;
- `O_v` be the current validated observations for visitor `v`;
- `U_v` be artworks already known, liked, disliked, viewed, rejected, or used
  in an earlier question.

For hypothesis `h = (type,value)` and artwork `a`, positive recorded support is:

```text
s(h,a) = 1  when artwork_attribute(a,type,value,facts) is provable
         0  when no such proof exists in the bounded snapshot
```

`s=0` means **no recorded support was found**. It is not a negative ArtGraph
fact and does not prove the depicted or physical artwork lacks that property.

The declared response-model assumption predicts:

```text
p(h,a,b) = prefer_a  when s(h,a) > s(h,b)
           prefer_b  when s(h,b) > s(h,a)
           unknown   otherwise
```

Two hypotheses are discriminated only when both make determinate, opposing
predictions. A pair is eligible only when both artworks are in `A \ U_v` and
at least one active hypothesis pair is discriminated.

Question ordering is deterministic:

```text
score(a,b) = 1000 × distinguished hypothesis pairs
             - 10 × response split imbalance
             - unknown predictions
```

The solver maximizes this score and breaks ties by stable artwork IDs. This is
a transparent selection policy, not a probability or learned utility model.

## Logical layers

`logic/clarification_rules.pl` separates:

1. **Museum facts:** typed attributes and the two-fact
   Artwork → Artist → Movement join.
2. **Preference assumptions:** liking or familiarity may provisionally suggest
   hypotheses; greater recorded support predicts an answer.
3. **Deductions:** active hypotheses, predictions, opposing predictions,
   eligible pairs, and deterministic selection.
4. **Session filters:** viewed, rejected, previously asked, and explicitly
   rejected hypotheses.

Important rule IDs include:

| Rule | Meaning |
|---|---|
| `r_like_suggests_attribute_hypothesis` | A liked artwork provisionally suggests a reviewed hypothesis supported by its facts. |
| `r_familiarity_suggests_attribute_hypothesis` | Familiarity supplies weak hypothesis evidence under a named assumption. |
| `r_greater_recorded_support_predicts_preference` | The bounded response model predicts the option with positive support. |
| `r_equal_recorded_support_is_undecidable` | Equal recorded support yields `unknown`. |
| `r_opposing_predictions_discriminate` | Two hypotheses are distinguished by opposing determinate predictions. |
| `r_finite_state_filtered_pair` | Both options satisfy the grounded session filters. |
| `r_select_max_discrimination_then_balance` | Select the highest-scoring pair with stable tie-breaking. |
| `r_response_contradicts_prediction` | A determinate opposite response removes that provisional hypothesis. |

## Multi-round semantics

`prefer_a` and `prefer_b` contradict only hypotheses that predicted the
opposite option. `neither` and `unsure` eliminate nothing. A correction
replaces the prior response for that question before a new stateless Prolog
process recomputes all deductions. Sessions never share mutable Prolog state.

The loop stops when one hypothesis remains, no discriminative pair is
provable, or the configured round limit is reached. Final artwork suggestions
are a secondary demonstration based on the remaining hypotheses.

## Proof contract

Every selected question contains a structured proof tree with:

- source observation IDs;
- active and distinguished hypothesis IDs;
- prediction nodes and support counts;
- response-model assumption IDs;
- selection and intermediate rule IDs;
- exact source and candidate `agf_*` IDs;
- the finite-state eligibility node.

Raw visitor text is never converted into Prolog source. Python serializes only
allowlisted atom-shaped IDs into a temporary state file and invokes a fresh
SWI-Prolog process.

## Baseline separation

- `random_eligible` samples two independently filtered IDs with a fixed seed.
- `raw_attribute_contrast` performs direct one-step contrast counting from the
  exported evidence JSON and never reads Prolog output.
- `single_rule_prolog` limits selection to the first two active hypotheses.
- `compositional_prolog` reasons over every active hypothesis and balances the
  predicted split.
- `direct_llm` receives the same hypotheses, candidates, and museum evidence
  through a mockable JSON transport. Its returned IDs are independently
  allowlist-validated. It does not receive Prolog proofs or scores.

No LLM is used by the symbolic selector.
