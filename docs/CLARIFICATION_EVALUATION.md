# Phase 1 Clarification Evaluation

## Scope

The executed benchmark contains 20 controlled scenarios over the same 112
real-ArtGraph artworks and ten hypothesis definitions. Fourteen scenarios have
two hypotheses, four have four hypotheses, one has only one remaining
hypothesis, and one deliberately restricts the candidate universe to artworks
with no useful recorded support contrast.

The hidden preference and simulated answers follow the declared deterministic
response model. Results measure internal logical behavior under that model;
they are not human preference accuracy, museum utility, or evidence of
real-world recommendation quality.

An independent Python evidence judge checks selected pairs directly against
the exported positive ArtGraph attribute catalog. It does not consume Prolog
proofs or scores. This avoids using the symbolic selector's own output as its
correctness label.

## Executed results

Command:

```powershell
.\.venv\Scripts\python.exe -u evaluation\evaluate_clarification.py --max-rounds 3
```

Results from `evaluation/clarification_results.json`:

| Method | Selection result | Independently valid | Mean distinguished hypothesis pairs | Mean runtime |
|---|---:|---:|---:|---:|
| Compositional Prolog | 22 questions across 20 scenarios | 100% | 1.4545 per question | 1656.602 ms/scenario |
| Single-rule Prolog | 18/20 scenarios | 100% | 1.0556 per selected pair | 553.555 ms/scenario |
| Raw attribute contrast | 19/20 scenarios | 73.68% | 1.1579 per selected pair | 13.125 ms/scenario |
| Random eligible pair | 20/20 scenarios | 10% | 0.15 per selected pair | 0.252 ms/scenario |
| Direct LLM | Not run | — | — | — |

The compositional loop resolved 19 scenarios to one remaining hypothesis
within three rounds and repeated no question. “Resolved” here includes the
single-hypothesis stopping case. The intentionally missing-support case
correctly retained two hypotheses and returned no discriminative question.

Direct-LLM execution is marked
`not_run_missing_configuration_or_flag`; no mocked result is reported as an
experiment. The interface and allowlist validation are tested with a fake
transport only as an engineering test.

## What the ablation shows

- The single-rule solver is enough for most two-hypothesis cases and is about
  three times faster. The full system does not demonstrate an advantage there.
- With larger active sets, compositional selection distinguishes more
  hypothesis pairs and explicitly optimizes response balance.
- Raw contrast is dramatically faster. Its objective counts individually
  contrasted attributes rather than opposing hypothesis predictions, so it
  can select a pair that does not actually distinguish two active hypotheses.
- Random selection nearly always asks a valid-looking pair of IDs but rarely
  distinguishes the current hypotheses.
- These findings establish behavior under the formal model only. They do not
  establish that visitors find the selected questions natural or useful.

## Multi-round real-data example

The offline demo starts from a liked real artwork, `ag_10472` Study for The
Cellist, plus an explicit nature-subject hypothesis. Five active hypotheses
are initially derived. Prolog selected:

```text
ag_10026  A mountain
ag_13351  Blind singer
```

Four hypothesis pairs were distinguished with a balanced 2/2 determinate
split and one unknown prediction. A simulated `prefer_a` response contradicted
the hypotheses that predicted `prefer_b`, reducing the state from five to
three. The next independently selected question changed to:

```text
ag_11014  Boy by the Water
ag_13231  A Bird Passing through a Cloud
```

The second proof distinguished expressionist style from both nature subject
and oil medium. Each prediction node includes its exact `agf_*` support.

## Failure and uncertainty cases

- When only one hypothesis remains, discrimination is undefined and the
  solver returns `no_discriminative_question`.
- When allowed artworks have equal/no recorded support for both hypotheses,
  the solver refuses to fabricate a contrast.
- `neither` and `unsure` preserve all hypotheses, so a session may stop at its
  round limit without resolution.
- A broad hypothesis such as oil medium may dominate many artworks and yield
  questions that are logically discriminative but aesthetically unhelpful.
- Exhaustive pair enumeration and fresh-process isolation cost substantially
  more runtime than direct Python baselines.
- Controlled answers exactly match the declared response assumption and are
  therefore optimistic. Human-reviewed question quality remains outstanding.
- Direct-LLM quality and cost remain unknown because no real provider call was
  executed.

## Reproduction and interpretation

The raw scenario-level outputs include pair IDs, independent distinction
counts, response sequence, hypothesis reduction, repeat counts, and runtime.
They must remain labeled as controlled simulation. Future human evaluation
should separately judge question naturalness, answerability, and whether the
attribute hypotheses match the visitor's intended reasons.
