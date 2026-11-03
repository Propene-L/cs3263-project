# Phase 1 Clarification Dataset

## Selection

The dataset is a deterministic bounded extraction from the checksum-verified
ArtGraph v1.0 RDF snapshot documented in `dataset_manifest.json`. The build
selects up to twelve artist-diverse artworks for each of ten typed hypotheses,
then takes their union and retains their attributes, artists, and artist-to-
movement links.

| Measure | Value |
|---|---:|
| Artworks | 112 |
| Artists | 70 |
| RDF triples | 2,232 |
| Typed topics | 493 |
| Tags | 209 |
| Styles / genres / media | 19 / 15 / 20 |
| Movements / periods / series | 36 / 9 / 3 |

The ten hypothesis values cover four subject tags, three styles, portrait
genre, oil medium, and the indirectly derived Expressionism movement. This
avoids the Phase 0.75 limitation where every candidate shared the Musical
instrument anchor.

## Verified contrast coverage

All 45 hypothesis pairs have at least two different-artist positive-evidence
contrast examples in `clarification_dataset_report.json`. The report records
stable artwork IDs, labels, and supporting fact IDs.

Real example:

```text
Hypotheses:
  h_musical_subject      = tag ag_3236, Musical instrument
  h_expressionist_style = style ag_21, expressionism

Option A: ag_8966, The lute player
  supports musical subject via agf_8311ec557e70c76e928c

Option B: ag_8388, Untitled (Naked Man with Knife)
  supports expressionist style via agf_1736790c2cb4048d6d8a
```

Under the declared recorded-support model, the first hypothesis predicts A
and the second predicts B. Neither empty support list is treated as proof of a
negative museum fact.

The multi-round demonstration begins with `ag_10472`, Study for The Cellist.
Its genuine facts provisionally suggest musical subject, expressionist style,
portrait genre, and oil medium. An explicit nature-subject observation adds a
fifth competing hypothesis.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts\build_clarification_dataset.py `
  --input data\raw\artgraph-facts.sanitized.ttl `
  --rdf-output data\curated\artgraph_clarification.ttl `
  --catalog-output data\curated\clarification_topic_catalog.json `
  --evidence-output data\curated\clarification_evidence.json `
  --report-output docs\clarification_dataset_report.json `
  --prolog-output logic\clarification_generated_facts.pl `
  --per-hypothesis 12

.\.venv\Scripts\python.exe scripts\build_clarification_benchmark.py
```

The 20 JSONL scenarios are controlled simulations, not human judgments or
gold recommendation labels. They include two- and four-hypothesis cases,
viewed/rejected filters, a corrected hypothesis state, a single-hypothesis
stopping case, and a deliberately support-missing candidate universe.

## Limitations

- Cohort construction intentionally enriches the selected attributes and is
  not representative of all ArtGraph.
- Oil is extremely broad; tag families contain correlated taxonomy terms.
- ArtGraph records associations, not visitor preferences or visual absence.
- The response model is idealized and deterministic.
- Artwork images are not redistributed or used by this phase.
- The ArtGraph record's displayed redistribution licence remains unresolved;
  only this bounded textual snapshot is committed.
