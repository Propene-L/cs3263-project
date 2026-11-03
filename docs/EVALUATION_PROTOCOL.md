# Evaluation Protocol — V2

## Phase 1 comparable task

Phase 1 supersedes the earlier next-topic comparison. Every method receives
the same validated visitor evidence, provisional hypotheses, allowed artwork
IDs, state filters, and authorized ArtGraph evidence. It returns two artwork
IDs for the next pairwise preference clarification question, or reports that
no useful pair was found.

1. **Compositional symbolic:** all active hypotheses, Prolog discrimination,
   response balancing, deterministic ordering, and proof trees.
2. **Single-rule symbolic ablation:** only the first competing hypothesis pair.
3. **Raw attribute contrast:** independent one-step positive-evidence counts.
4. **Random eligible:** deterministic-seed pair selection.
5. **Direct LLM:** the same evidence and IDs, with no access to Prolog proofs,
   symbolic scores, or expected results. Only actual configured calls count as
   experimental results.

The paper-inspired KG embedding baseline remains a later extension; it is not
the Phase 1 priority.

## Tracks

- **Algorithm isolation:** manually curated structured state and identical
  candidate sets; this is the primary comparison.
- **End-to-end:** natural language extraction is evaluated separately so its
  errors are not attributed to the recommendation algorithm.

## Labels and safeguards

Acceptable topics must be independently reviewed using documented factual and
pedagogical criteria. They must not be copied from any system output. Labels
must distinguish factual support, reasonable contextual guidance, and genuine
learning prerequisites. Use fixed development/test splits if tuning occurs.

## Phase 1 metrics

- Independent positive-evidence validity of the selected pair.
- Number of hypothesis pairs distinguished and predicted split balance.
- Hypothesis reduction and questions needed over controlled rounds.
- Repeated/unnecessary questions and correct no-question behavior.
- Proof completeness: observation, hypothesis, rule, assumption, and fact IDs.
- Runtime, configured model cost, and deterministic seed reproducibility.
- Human question realism and relevance must be reported separately from the
  controlled response-model simulation.

Report failures by missing fact, bad import, overly broad guidance rule,
unsupported premise, extraction error, similarity mismatch, LLM hallucination,
and ranking-policy weakness. Gold labels and quantitative results belong to a
later reviewed phase and must come from genuine runs.

## Dataset/licence constraint

The minimum manifest fields are implemented in `dataset_manifest.json`. The
Zenodo v1.0 record's displayed Rights/License field was blank during the Phase
0 audit. Do not redistribute bulk RDF or images until this is clarified.

