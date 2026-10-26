# Evaluation Protocol — V2

## Comparable output task
All models receive a goal, known/covered topics, an allowed candidate set, and a controlled ArtGraph fact/context slice. They output **ranked next explanatory topics** from the **same** candidate IDs. The direct LLM may use a raw transcript in the end-to-end track, but the controlled track receives the same structured state as the other models. Do not evaluate an art-object recommender against a topic recommender and call the numbers comparable.

## Three systems

**A — Symbolic:** ArtGraph facts + hand-authored documented Horn clauses in SWI-Prolog → entailed topic candidates → deterministic ranking with proof IDs.

**B — KG baseline (Liu et al.-inspired):** Embed / represent ArtGraph-derived entities and rank related candidate topics using visitor goal/interest features. Document chosen embedding algorithm (e.g., node2vec or another reproducible KG embedding) and any adaptation from the **paper's artwork-recommendation task**. This is NOT an exact implementation of Liu et al. and not an official published benchmark. Do not use symbolic candidate/rule scores.

**C — Direct LLM:** User goal, known-topic information and controlled authorized KG content → prompt model to directly choose ranked topic IDs. No call to A or read of proof/gold answers. Record provider, model, seed and generation settings.

Optional D — one-hop graph-neighbor baseline for ablation.

## Two evaluation tracks

**Track 1: Algorithm isolation (primary).** Manually curated, validated structured visitor input; identical topic catalog and allowed candidate lists. This isolates effects of logical deduction vs KG similarity vs direct model. Ensure the KG facts supplied to LLM are comparable, and report context-window limitations if the full graph cannot fit.

**Track 2: End-to-end application (secondary).** Raw text utterance → validated LLM state extraction → symbolic or KG model; raw text → direct LLM action. Measure extraction errors separately so they are not falsely attributed to the deduction algorithm.

## Gold labels and fairness

- Develop 20–30 scenario instances initially, with subsets for multi-hop reasoning, sparse/irrelevant context, goal changes, already-known topics, ambiguity, and unsupported candidates. Treat counts as a **target**, not a course requirement.
- `acceptable_topic_ids`: reviewed by team members using documented museum facts and pedagogical/contextual relevance. More than one correct topic per scenario is allowed.
- **Do not create gold answers with `candidate_topic/2` or by copying any baseline's ranked output.** That would be circular. If reviewer disagreement arises, document a resolution process.
- Gold labels must specify whether they judge **objective factual support**, **reasonable next reference topic**, or **true learning prerequisite**. These are different tasks.
- Use a fixed split if rules/embedding hyperparameters are tuned; do not tune on final test scenarios.

## Metrics

1. **Logic correctness (independent unit tests):** query answers, substitutions, supported multi-hop deductions, invalid/unsupported inference rate, correct proof IDs.
2. **Recommendation quality:** Hit@k/Recall@k/Precision@k against human-reviewed acceptable sets, redundant recommendations (already known, skipped or presented), evidence-backed recommendation rate, and MRR when meaningful.
3. **End-to-end:** visitor-state extraction accuracy, unsupported topic ID rate, multi-round response appropriateness.
4. **Operations:** runtime by extracted graph size, model/token cost when available, reproducibility across seeds.

Report failures separately for: missing ArtGraph fact, erroneous imported ID, overly general guidance rule, unsupported premise, language extraction error, embedding-similarity mismatch, direct-LLM hallucinated entity, and selection-policy weakness.

## Dataset manifest minimum fields

`artgraph_record`, `artgraph_version`, `artifact_name`, `download_date`, `rdf_predicates_used`, `seed_ids`, `filter_rules`, `entity_count`, `edge_count`, `candidate_types`, `license_status`, `source_uris`, `processing_script_commit`, `sample_hash`.

Do not redistribute images or bulk data until their license has been checked. The dataset record contains an RDF download but its displayed license metadata is not explicit.

## Report tables

- Number of real original facts vs inferred facts, by relation and hop count.
- Counts of successful/failed deduction/proof tests.
- Three-way comparison with confidence intervals or per-scenario paired differences where sample size allows.
- Ablation of multi-hop reasoning or guidance rules versus simpler graph-neighbor approach.
- Case studies where inference succeeds over multiple relations but similarity fails; and vice versa.

## Sources

- ArtGraph: https://zenodo.org/records/6337958
- Liu et al. (2022): https://doi.org/10.3233/FAIA220215
