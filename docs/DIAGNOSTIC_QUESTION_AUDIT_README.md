# Phase 1.2 diagnostic-question audit

## Scope

This patch assesses **whether a saved clarification question targets a competitive, unresolved explanation** rather than simply whether one of its attributes occurs in a liked artwork. It reads the repo's **32 authored robustness scenarios**, frozen ArtGraph v1.0 reviewed attributes, and the already saved SOCLAAS `default` one-pass and repaired-composite LLM questions. No new model or Prolog inference calls are needed.

It does **not** create new user-preference labels, prove psychological usefulness, or evaluate a multi-turn LLM.

## Install and run

Extract `evaluation/` and `tests/` into the same folders in the `cs3263-project` checkout at commit `945b009db765d9321bf97dbeaaccc88c063cd4e3` (or a later compatible commit).

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m evaluation.audit_diagnostic_questions --source both
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_audit_diagnostic_questions.py -v
```

The script produces `evaluation/diagnostic_question_analysis/`:

- `diagnostic_question_summary.json`: one-pass and repaired-composite summary, each under three assumption thresholds
- `final_competitive_questions.csv`, `onepass_competitive_questions.csv`: question-by-question results
- `*_strict_questions.csv`, `*_permissive_questions.csv`: sensitivity outputs
- `blind_review_questions.csv`: **unscored**, method-blind A/B actions with visitor histories and visible evidence
- `blind_review_PRIVATE_key.csv`: mapping of A/B to method; **do not give to reviewers**

These files are *generated on your machine*. This package includes `MEASURED_FINDINGS.md` and `measured_summary.json`, containing results computed independently from the published GitHub evidence and CSV in the current review. The Python implementation has passed synthetic unit tests but has not been executed against a complete repository checkout in this environment; verify its regenerated counts against that summary.

## Method: transparent competing explanations, not ground truth

1. Active observations are computed after chronological supersession/corrections.
2. Artwork supports use only the 10 reviewed hypothesis IDs and facts visible to both models. A masked or unrecorded attribute is unknown, **not false**.
3. Enumerate atomic explanations and tag–style, tag–genre, style–genre conjunctions. No Prolog conclusions, preferred questions, latent profiles, or gold labels are imported into this enumeration.
4. Exclude explicitly settled explanations, and do not infer a conjunction merely because both atomic interests are explicitly confirmed.
5. Count distinct liked artworks supporting the candidate explanation. A candidate qualifies according to one of three thresholds:
   - **Competitive (primary):** at least `max(1, maximum support count − 1)` liked artworks. This tolerates one extra positive example explained by some other feature, and allows two independently liked themes.
   - **Strict:** support in **every** liked artwork.
   - **Permissive:** support in **at least one** liked artwork (approximately the old grounding rule, except explicit-settlement handling).
6. A question is a **diagnostic candidate** if it asks about one of the remaining explanations. This is a *proxy for diagnostic targeting*, not proof that its answer will be informative.
7. Optional `structural_proxy_bits` is a **toy entropy** under a uniform set of mutually exclusive one-explanation alternatives plus an 'other/unmodeled' explanation. It is **not empirical entropy reduction**: real visitors may hold multiple simultaneous interests and candidate probabilities are not known. Do not call these numbers real information gain or use them as a primary superiority result.

`effective_diagnostic_recall_over_needed` uses the existing *authored* `expected_action_type==clarify` labels, including missed questions as zeros. Reviewers should be free to disagree with the authored label.

## Interpret the strongest comparison correctly

The final repaired LLM asked nine questions and Prolog asked nine, but they asked in different scenarios. In the **three shared asked scenarios** (`independent_feline_impressionist`, `noisy_water`, and `ambiguous_cellist`), both systems score **2/3** under the competitive diagnosticity proxy. The overall difference reflects **when** to ask much more strongly than **what** to ask.

The pre-existing *controlled-world* evaluation still matters. In `ambiguous_cellist`, Prolog asks about expressionist style, which splits **0/2** authored worlds, while the LLM asks about musical subjects, which splits **2/2**. That is a genuine local counterexample to universal Prolog question superiority. In `noisy_water`, neither method selects the noise-conflicted water interest: Prolog asks about oil, LLM asks about music. Both need improvement.

## Independent human check (not yet performed)

Ask reviewers to complete `blind_review_questions.csv` **without the PRIVATE key, gold profiles, expected action labels, or method names**. Ideally use at least two reviewers. They should separately judge whether clarification is necessary, which action is more appropriate, and which question most directly distinguishes the visitor's uncertainty. Allow `equal` and `neither` responses, calculate inter-rater agreement, and report discordant examples. The sheet is text-only ArtGraph evidence; results do not generalize to visual appreciation of actual artwork.

## Caveats

- The 32 scenarios are hand-authored by the implementation agent and share a limited artwork pool; they are not independent visitor transcripts.
- Candidate alternatives are induced by a simple heuristic, not a validated preference model; the threshold sensitivity is essential.
- The single-explanation toy world space omits multiple-independent-interest profiles except where known explicit interests exclude premature conjunctions.
- The pre-existing LLM is SOCLAAS `default`, with model snapshot unknown. The repaired composite selectively reruns invalid initial responses and is not a one-request model test.
- The companion controlled-world information-gain test has four two-world scenarios only. Do not generalize to arbitrary visitor conversations or claim the symbolic engine always asks the optimal question.
- The new Python script does not modify inference rules, saved original results, or the GitHub branch.
