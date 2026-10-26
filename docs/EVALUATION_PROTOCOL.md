# Evaluation Protocol — V2

## Comparable task

All three systems receive the same goal, covered-topic set, allowed candidate
IDs, and controlled ArtGraph context. They return ranked next explanatory
topics from that common closed universe.

1. **Symbolic:** ArtGraph facts plus documented SWI-Prolog Horn clauses, with
   deterministic ordering and proof IDs.
2. **KG similarity:** a reproducible embedding/similarity method inspired by
   Liu et al. (2022), explicitly not claimed as an exact reproduction.
3. **Direct LLM:** the same authorized context and IDs, with no access to Prolog
   proofs, symbolic scores, or gold labels.

Phase 0 implements none of the comparison runs.

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

## Planned metrics

- Logic correctness: substitutions, multi-hop entailments, invalid inference,
  and exact proof IDs.
- Recommendation quality: Hit/Recall/Precision@k, MRR where meaningful,
  redundant-topic rate, unsupported-topic rate, and evidence-backed rate.
- End-to-end: state extraction accuracy and unsupported ID rate.
- Operations: runtime by graph size, model cost, and seed reproducibility.

Report failures by missing fact, bad import, overly broad guidance rule,
unsupported premise, extraction error, similarity mismatch, LLM hallucination,
and ranking-policy weakness. Gold labels and quantitative results belong to a
later reviewed phase and must come from genuine runs.

## Dataset/licence constraint

The minimum manifest fields are implemented in `dataset_manifest.json`. The
Zenodo v1.0 record's displayed Rights/License field was blank during the Phase
0 audit. Do not redistribute bulk RDF or images until this is clarified.

