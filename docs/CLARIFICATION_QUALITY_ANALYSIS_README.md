# CS3263 Phase 1.2 — Clarification quality analysis

This drop-in patch works with commit `2bf09a3f345984768188636d2ffd2439a3447b2b` on branch `phase-1-2-state-reasoning-relevance`. It **does not edit your existing inference rules or historical results** and **makes no LLM API requests**.

## Installation

Unzip the archive into your existing `cs3263-project` repository root, preserving the `evaluation/`, `tests/`, and `docs/` paths. Existing files are not overwritten by this patch (other than files from a previous installation of this exact patch).

The analysis reads the following already-committed files:

- `evaluation/preference_state_llm_normalized_results.json` — one-request LLM baseline with deterministic name normalization.
- `evaluation/preference_state_llm_final_comparison_results.json` — second-chance LLM composite.
- `evaluation/preference_state_corrected_scenarios.jsonl` — 24 pattern-matched regressions.
- `evaluation/preference_state_robustness_scenarios.jsonl` — 32 authored robustness scenarios.
- `data/curated/clarification_evidence.json` — typed ArtGraph facts and the 10 reviewed hypotheses.

## Run the offline analyses first

From PowerShell in the repository root:

```powershell
.\.venv\Scripts\python.exe -m evaluation.analyze_clarification_quality `
  --source both --benchmark robustness
```

This creates four files under `evaluation/clarification_analysis/`:

- `onepass_robustness_questions.csv`
- `onepass_robustness_summary.json`
- `final_robustness_questions.csv`
- `final_robustness_summary.json`

Repeat with `--benchmark all` or `--benchmark regression` for separate descriptions of the constructed 24-case subset versus all 56 cases. **Keep robustness as the primary claim.**

For each method, the summary includes:

- Clarification TP, FP, FN, TN, with invalid outputs counted as missed clarification only when clarification was expected. Invalid non-clarification outputs are **not** credited as true negatives.
- Clarification precision, recall, F1 against **authored** expected-action labels.
- Question Grounding Rate (QGR), a weaker contextual-relation rate (including observed dislikes), and `grounded_and_unsettled_rate_given_asked`.
- Effective grounded clarification recall among cases labeled as needing clarification.
- Controlled-world question splits and binary information gain **only for histories with two or more authored latent worlds**. Single-world cases have `null` rather than an invented information-gain estimate.

Inspect the per-case CSV. A question about `h_musical_subject` in the `noisy_water` scenario should fail grounding even if its JSON is schema-valid.

## Run the paired post-clarification experiment

Requires the repository's SWI-Prolog installation and original dependencies. This **replays each saved question**; it does not request additional LLM generations.

```powershell
.\.venv\Scripts\python.exe -m evaluation.analyze_clarification_quality `
  --source both --benchmark robustness --closed-loop
```

Additional per-case outputs:

- `onepass_robustness_counterfactual_loop.csv`
- `final_robustness_counterfactual_loop.csv`

The summaries add `counterfactual_shared_prolog_updater` with average changes in primary explanation accuracy, precision, recall, top-1 ranked-artwork relevance and actual post-answer recommendation relevance. It reports both **asked-only deltas** and **all expected-clarification cases (missed questions = zero improvement)**. Cases where both methods ask are compared separately, averaging alternative worlds *within each scenario*.

**Interpretation:** The starting visitor state and correction mechanism are always those of corrected Prolog for both sources. The simulated visitor returns `yes` exactly if the queried explanation is a member of that world's authored profile; otherwise `no`. This isolates how useful the *selected question* is under a shared updater. It is not an evaluation of LLM follow-up reasoning or real human responses. Because the common updater is Prolog's own model, this still favors questions compatible with its state semantics; treat it as a controlled engineering comparison, not independent human evidence.

## Pure unit tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_clarification_quality_analysis.py -v
```

Alternatively, run `pytest -q tests/test_clarification_quality_analysis.py`. The tests need neither Prolog nor a model API. They check evidence grounding, the independent-interest-vs-conjunction distinction, hidden attributes, explicit status, world splitting, invalid-output denominators, and a schema-valid but ungrounded clarification.

## Definitions and limitations

**Clarification precision:** TP / (TP + FP), where TP means an output asked when the scenario author labeled clarification necessary. It is policy-label agreement, not human-rated utility.

**Clarification recall:** TP / (TP + valid FN + invalid attempts on positive scenarios). An invalid response cannot silently earn a true negative.

**Grounded clarification:** The queried preference is supported by a liked artwork's *visible recorded* attribute(s), or the visitor explicitly stated the exact interest. The separate `contextually_related` indicator also counts relevant disliked artworks; it is more permissive than QGR. For conjunctions, both component attributes must appear in the **same liked artwork**, unless an explicit conjunction was stated. A question about two independently declared interests is not automatically grounded as a conjunction. `grounded_and_unsettled` additionally requires that the exact preference has not already been explicitly settled.

This is a conservative factual-support test, not an independent judgement of psychological preference. An exploratory question about a genuinely new topic can be helpful even if it fails this definition; these cases require human review.

**World information gain:** For an ambiguous history with multiple authored worlds, a question splits worlds according to the deterministic membership oracle. With a uniform prior, the binary entropy of yes/no answers is the expected information gain in bits. The experiment has very few multi-world cases, so do not generalize this metric.

**Counterfactual update:** Replays both models' saved questions through the **same corrected Prolog engine**. It does not simulate a visitor's actual language or an LLM's next-turn decisions. Conditional averages across only asked questions are selection-biased; report question frequency and the matched both-ask subset.

**Method identity:** The LLM source is the SOCLAAS Responses-compatible endpoint with returned model identifier `default`, not an independently verified frontier OpenAI model. The composite selectively reran invalid first-pass responses with a stronger contract prompt, so it must not replace the one-request baseline.

**No results are hard-coded.** Run the scripts inside the full repository to generate numerical findings. The zip does not include GitHub's large archived result JSON or any secrets.
