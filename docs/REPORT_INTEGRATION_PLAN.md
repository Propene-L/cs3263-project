# Page-Neutral Report Integration Plan

This plan changes Sections 6–7 of the existing 10-page report by replacement,
not accumulation. It does not edit the Google Docs report. Figure numbering
below should be reconciled with the current document after replacement.

## 1. Replace the current Phase 1.1 single-round results paragraph and figure

Replace the paragraph that reports only final three-question totals and the
existing Phase 1.1 comparison graphic with Figure
`fig_multi_round_resolution` and this paragraph:

> Across the fixed cohort of 57 initially solvable scenarios, compositional
> Prolog resolved 15, 28 and 44 cases after one, two and three questions,
> compared with 15, 16 and 27 for the single-rule ablation. At the three-question
> horizon this is 77.19% versus 47.37% (+29.82 percentage points); mean active
> hypotheses fell from 4.14 initially to 1.32 versus 2.25. Raw contrast reached
> 35/57 and random eligible selection 1/57. Exact Python matched compositional
> Prolog exactly, so the gain is attributable to the complete-hypothesis
> objective rather than Prolog as an optimizer. These are controlled response-
> model outcomes, not human information gain.

Replacement caption:

> **Figure X. Multi-round controlled clarification.** Cumulative correct
> resolution (left) and fixed-cohort active hypotheses with terminal states
> carried forward (right), both over the same 57 initially solvable scenarios.
> Carry-forward is used only for the plotted state size; actual question counts
> remain separate. Exact Python overlaps compositional Prolog.

Page-neutral action: remove the old final-rate bar chart and its explanatory
paragraph; use this two-panel figure in the same footprint.

## 2. Replace the generic “multi-hypothesis benefit” paragraph

Replace the current qualitative claim that compositional reasoning helps on
complex cases with Figure `fig_difficulty_breakdown` and this paragraph:

> The compositional benefit is conditional on state complexity. Both Prolog
> variants resolved all 14 cases with exactly two active hypotheses. Among 43
> cases with three or more, compositional Prolog resolved 30 (69.77%) and the
> single-rule ablation 13 (30.23%), a paired difference of 39.53 percentage
> points; there were 18 compositional-only successes and one single-rule-only
> success. Compositional selection distinguished 2.36 hypothesis pairs per
> question versus 1.42, at a saved mean selector cost of 883 versus 645 ms.
> The counterexample `phase_1_1_multi_021` shows that maximizing aggregate
> distinction need not be optimal for every hidden state.

Replacement caption:

> **Figure Y. Resolution by initial hypothesis-set size.** Three-question
> resolution rates use paired scenario IDs within each stratum (n=14 and n=43).
> The added objective provides no benefit for two-hypothesis states and a large
> descriptive benefit for larger states.

Page-neutral action: replace the current runtime or method-summary table with
this compact grouped figure; keep only the runtime contrast in prose.

## 3. Replace any claim that interaction inference explains conjunction scores

Replace the Section 6 preference-state paragraph that attributes true-
conjunction accuracy to inferred interaction reasoning with this negative-result
paragraph and Figure `fig_interaction_ablation`:

> Disabling only `c_interaction/3` changed one of 32 robustness scenarios. It
> removed a provisional conjunction in `ambiguous_albert` and changed the
> clarification target, but changed no primary explanation, action type or
> recommendation. Overall primary accuracy remained 59.38% and action accuracy
> 96.88%; false-interaction rate fell from 1.56% to zero, while explanation
> recall fell from 84.38% to 82.81% and top-1 relevance from 82.81% to 81.25%.
> All four true-conjunction cases were unchanged because their conjunctions were
> explicitly stated. Thus the benchmark verifies explicit conjunction handling
> and ablation isolation, but does not identify a benefit for discovering latent
> conjunctions.

Replacement caption:

> **Figure Z. Evaluation-only ablation of inferred conjunctions.** Full
> corrected-v2 versus the identical policy with `c_interaction/3` disabled.
> Values average alternative worlds within each scenario; 32 scenarios, not 36
> worlds, are the sample units.

Page-neutral action: replace the current broad conjunction-success discussion
and one redundant robustness table. Preserve the limitation sentence even if
space is tight.

## 4. Replace the current Figure 4 interpretation of direct-LLM results

Replace Figure 4 or its current validity paragraph with
`fig_llm_failure_decomposition` and this text:

> Only 2/56 initial LLM responses satisfied strict ID-only parsing. Exact-label
> normalization raised validity to 31/56; conservative repair plus 21 targeted
> reruns accepted 53/56, of which 51 decisions were deterministically valid.
> Nevertheless, only 34/56 attempted scenarios had the correct action type
> end-to-end. Among valid decisions, 19 action errors remained—13 missed
> clarifications, two unnecessary clarifications and four inappropriate
> clarification decisions where insufficient evidence was expected. The final
> composite used 77 requests (56 initial + 21 reruns) and is not an equal-budget
> comparison with single-pass Prolog.

Replacement caption:

> **Figure W. Direct-LLM failure decomposition.** Fixed denominator 56 separates
> parsing/contract recovery from deterministic decision validity and end-to-end
> action correctness. Repair improves acceptability but does not eliminate
> reasoning-policy errors.

Page-neutral action: remove the existing normalization-count table and fold its
counts into this figure.

## 5. Replace the Section 7 clarification-quality paragraph

Use this replacement without adding another figure:

> Clarification timing and question quality are distinct. Against authored
> labels, Prolog achieved 9 TP, 0 FP and 0 FN; the repaired LLM achieved 3 TP,
> 6 FP and 6 FN. Conditional on asking, Prolog grounded 9/9 questions and the
> LLM 7/9, but this comparison is selection-biased because six of nine LLM
> questions were unnecessary. Competitive diagnostic recall over all nine
> needed cases was 8/9 versus 2/9. In the three cases where both asked, the LLM
> supplied an important counterexample: for `ambiguous_cellist`, its musical-
> subject question split the two authored worlds while Prolog's Expressionist-
> style question did not. Counterfactual results use the same exact oracle and
> Prolog updater for both methods and do not measure independent multi-turn LLM
> adaptation.

Page-neutral action: replace the current conditional quality paragraph and
retain the existing clarification chart. Do not add a fifth figure.

## Recommended final layout

- Keep three experimental figures in Section 6: multi-round trajectory,
  difficulty breakdown, and interaction ablation.
- Replace the existing LLM Figure 4 with the failure-decomposition funnel.
- Keep the existing clarification figure and replace only its interpretation.
- Remove redundant final-rate, normalization-count, and robustness tables.

This substitution keeps approximately the same figure and paragraph count
while strengthening the causal claims and adding the required negative result.

