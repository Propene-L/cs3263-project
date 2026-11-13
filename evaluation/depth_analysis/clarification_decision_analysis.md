# Clarification timing versus question quality

This analysis uses the existing 32-scenario robustness audit and saved LLM
outputs only. It separates the decision to ask from the quality of the selected
question.

## Stage 1 — when to ask

The authored `expected_action_type` is the clarification label; it is not a
human preference judgment. Compositional Prolog produced 9 true
positives, 0 false positives, and
0 false negatives: precision and
recall were both 100.0% (9/9 needed cases).

The one-pass LLM produced 1 TP, 4 FP, and
8 FN, for
20.0% precision and
11.1% recall.
After deterministic repair and targeted contract reruns it produced
3 TP, 6 FP, and
6 FN: precision and recall were
both 33.3%. The repaired result uses
additional requests and is not an equal-budget single-shot comparison.

## Stage 2 — what to ask

Conditional on asking, Prolog grounded 9/9 questions in recorded positive
evidence and targeted a competitive explanation in 8/9. The repaired LLM
grounded 7/9 and targeted a competitive explanation in 6/9. These conditional
rates are selection-biased: every Prolog question occurred in a scenario whose
authored label required clarification, whereas only 3/9 LLM questions did; the
other six were false-positive clarifications. Accordingly, the effective
competitive diagnostic recall over the nine needed cases was 8/9 for Prolog
and 2/9 for the repaired LLM.

For multi-world scenarios, Prolog asked four questions and split the authored
worlds in three (mean oracle split entropy 0.75 bits). The repaired LLM asked in
one such scenario and split it (1.0 bit). This does not imply superior general
LLM question quality because the conditioning sets differ.

## Three matched cases where both asked

- `independent_feline_impressionist`: both methods asked about
  `h_feline_subject`; both questions were grounded and competitive-diagnostic.
- `noisy_water`: Prolog asked about `h_oil_medium`, which was grounded but not
  competitive-diagnostic under the audit. The LLM asked about
  `h_musical_subject`, which was neither grounded nor competitive-diagnostic.
- `ambiguous_cellist`: both questions were grounded and structurally
  diagnostic. Prolog asked about `h_expressionist_style`, which did not split
  the two authored worlds (0 bits); the LLM asked about `h_musical_subject`,
  which split them evenly (1 bit). This is the required counterexample to any
  claim that the Prolog question is always better.

Across these three matched scenarios, the common-updater replay increased mean
primary accuracy by 0.333 for the Prolog questions and 0.500 for the LLM
questions. The sample is only three selected cases.

## Counterfactual replay limitation

Both saved questions are answered by the same exact membership oracle and fed
into the same corrected Prolog updater. The replay therefore compares question
choice under a common update policy. It does **not** evaluate independent
multi-turn LLM adaptation, natural visitor replies, or a new LLM inference
after the answer. No new figure is generated because the existing
clarification chart plus the supporting CSV already expresses the timing and
quality separation without another redundant visualization.
