# Phase 0.75 — ArtGraph Interest-Inference Data Audit

## Scope and reproducibility

This audit uses the local checksum-verified, sanitized ArtGraph v1.0 RDF
snapshot documented in `dataset_manifest.json`: 1,518,149 unique RDF triples,
116,475 artworks, and 134,970 resource URIs. The source is ArtGraph v1.0,
Zenodo record 6337958. The record's displayed licence field remained blank at
the time of the original audit, so the bulk RDF is not committed.

`scripts/investigate_interest_inference.py` performs RDF extraction and
descriptive analysis. It does not infer visitor interests or choose
recommendations. The main machine-readable result is
`docs/interest_inference_audit.json`.

## 1. Exact `about` semantics

The bundled ArtGraph ontology declares:

```text
about: domain Artwork, range Tag
```

The populated graph agrees exactly. All 342,982 unique `about` triples have
the observed type pair `Artwork → Tag`; no other observed domain/range pair
was found. Therefore `about` directly connects artworks to `Tag` entities.

Real example:

```text
ag_38677  "Vegetables Merchant"
  -- about -->
ag_2718   "fruits-and-vegetables"

fact: agf_8357ebcca423e45cfa12
predicate: https://www.gennarovessio.com/artgraph-schema#about
```

Supporting source triple:

```text
<https://www.gennarovessio.com/artgraph-resources#38677>
<https://www.gennarovessio.com/artgraph-schema#about>
<https://www.gennarovessio.com/artgraph-resources#2718>
```

## 2. Tag coverage and distributions

| Measure | Result |
|---|---:|
| Tag entities | 5,424 |
| `about` triples | 342,982 |
| Artworks with at least one tag | 95,588 / 116,475 (82.0674%) |
| Mean tags per all artworks | 2.9447 |
| Mean tags per tagged artwork | 3.5881 |
| Median tags per tagged artwork | 3 |
| Tagged-artwork p90 / p95 / maximum | 7 / 9 / 21 |
| Median artworks per tag | 3 |
| Mean artworks per tag | 63.2341 |
| Artworks-per-tag p90 / p95 / maximum | 62 / 202 / 10,864 |
| Tags used by at least two artists | 2,929 |

The distribution is highly skewed. Some tags are extremely broad:

| Tag | Artworks | Artists | Assessment |
|---|---:|---:|---|
| `ag_2975` Tree | 10,864 | 1,115 | Very broad visual-object signal |
| `ag_2763` Lady | 9,403 | 918 | Broad and culturally/semantically noisy |
| `ag_2761` Sky | 8,923 | 948 | Broad visual-object signal |
| `ag_2893` Sketch | 7,329 | 863 | Mixes subject/appearance and work type |
| `ag_2719` Christianity | 5,179 | 211 | Potentially meaningful but broad |

Other tags are more discriminative, but frequently occur in redundant
taxonomic families. For example `ag_10472` “Study for The Cellist” has tags
including Musical instrument, String instrument, Cellist, Violone, Violin
family, Cello, Viol, Bass violin, and Bowed string instrument. Treating these
as nine independent preferences would greatly overstate the evidence.

Tag labels therefore mix:

- recognizable subjects or motifs (`Tree`, `Cellist`, `Village`);
- broad categories (`Nature`, `Human`, `Christianity`);
- taxonomy ancestors (`Felidae`, `Carnivore`, `Violin family`);
- dataset-specific hyphenated categories (`male-portraits`);
- possible visual-model outputs or noisy object labels (`Chin`, `Forehead`).

Tags are useful typed evidence, but raw tag count is not a calibrated measure
of interest strength.

## 3. Tag sharing and cross-artist overlap

The audit reports exact artwork-centric quantities. An artwork is counted
once when at least one peer satisfies the condition; it does not attempt to
materialize every possible artwork pair.

| Overlap condition | Artworks | Share of tagged artworks |
|---|---:|---:|
| At least one same-tag peer by another artist | 95,460 | 99.8661% |
| At least one peer sharing two or more tags | 72,285 | 75.6214% |
| At least one different-artist peer sharing two or more tags | 71,611 | 74.9163% |

There are 40,042 repeated two-tag groups, of which 32,845 span multiple
artists. This confirms that cross-artist retrieval is feasible. It also makes
raw overlap a strong baseline that the compositional system must outperform or
meaningfully qualify.

## 4. Typed relations are not interchangeable tags

| Predicate | Observed/declared semantics | Frequency | Interest use |
|---|---|---:|---|
| `about` | Artwork → Tag | 342,982 | Subject/object/theme evidence; noisy and hierarchical |
| `hasStyle` | Artwork → Style | 116,475 | Curated categorical style; exactly one per artwork in this data |
| `hasGenre` | Artwork → Genre | 116,475 | Curated categorical genre; broad but interpretable |
| `createdBy` | Artwork → Artist | 116,475 | Provenance and intermediate relation, not a tag |
| `belongsToMovement` | Artist → Movement | 1,056 | Indirect artwork movement via artist; multi-step provenance |
| `madeOf` | Artwork → Media | 83,824 | Material/medium; often common and weak alone |
| `partOf` | Artwork → Serie | 8,322 | Series membership; specific but sparse |
| `hasPeriod` | Artwork → Period | 5,748 | Artist-relative period; not a universal chronology |
| `hasSubject` | Artist → Subject | 21,054 | Biographical/category context for artists, not artwork tags |

The proof-of-concept imports Tag, Style, Genre, Media, Series, Period, and the
derived Artwork → Artist → Movement path as distinct attribute types. It does
not flatten all relations into a generic tag namespace. `hasSubject` remains
outside the default interest representation because it describes artists and
often contains broad biographical categories.

## 5. Single- and multiple-artwork evidence

### Single artwork

For real artwork `ag_10472` “Study for The Cellist,” the development universe
contains 187 other artworks sharing at least one attribute, 163 sharing at
least two, 122 sharing at least three, 78 sharing at least four, and 43 sharing
at least five. The closest cross-artist record is `ag_37634` “The Cellist
(Serevitsch),” sharing 12 typed attributes.

This demonstrates high recall but weak discrimination for a single tagged
artwork. A one-tag rule would admit almost the entire 188-artwork universe.

### Multiple artworks

For `ag_10472` and `ag_37634` together:

- union attributes: 14;
- intersection/repeated attributes: 12;
- 162 unobserved candidates share at least two union attributes;
- the leading unobserved candidate, `ag_70351` “The Cello Player,” matches ten
  repeatedly evidenced attributes and twelve union attributes.

Repeated occurrence therefore changes the evidence profile even where the
candidate set remains broad. Intersection is useful for confidence ordering;
union retains diverse interests but increases weak matches. Neither operation
is a probability model.

## 6. Five multi-artist candidate universes

Each universe is all real artworks carrying the named anchor tag. Candidates
were restricted to 50–200 artworks, at least ten artists, then ranked by typed
coverage and exact cross-artist multi-attribute opportunities. Highly
overlapping anchors were removed deterministically.

| Rank | Anchor | Artworks | Artists | Typed values | Attribute links | Links/artwork | Cross-artist multi-attribute coverage |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `ag_3236` Musical instrument | 188 | 138 | 263 | 1,704 | 9.0638 | 188 (100%) |
| 2 | `ag_3679` Nature reserve | 199 | 78 | 207 | 2,875 | 14.4472 | 199 (100%) |
| 3 | `ag_3579` Water transportation | 188 | 114 | 200 | 2,025 | 10.7713 | 188 (100%) |
| 4 | `ag_3392` Felidae | 198 | 78 | 195 | 1,778 | 8.9798 | 198 (100%) |
| 5 | `ag_3302` Village | 197 | 89 | 158 | 1,489 | 7.5584 | 197 (100%) |

All five contain seven attribute types: genre, medium, movement, period,
series, style, and tag. Their density is partly inflated by taxonomy-related
tags. “Nature reserve” is especially redundant: example artworks share Forest,
Nature, Natural environment, Natural landscape, Woodland, Wilderness, and
other nearby taxonomy terms.

### Recommended development universe

Use the 188-artwork Musical instrument universe for the next reviewed phase:

- it has the most artists (138), reducing same-artist shortcuts;
- it includes portrait, genre, and still-life works rather than one style;
- it has 24 styles, 13 genres, 17 media values, and 41 movements;
- real cello examples provide strong multi-attribute paths while weaker
  instrument examples test ranking discrimination;
- its redundant instrument taxonomy is an explicit stress case for the raw
  overlap ablation.

The recommendation is about structural research utility, not artistic merit.
The six-work Morris Louis snapshot remains valuable for regression tests but
is not the cross-artist development universe.

## 7. Data limitations

- ArtGraph tags are assertions in the dataset, not verified visitor interests.
- Tags have no hierarchy predicate in the imported graph; taxonomy redundancy
  is visible in labels but cannot safely be collapsed without an additional
  curated mapping.
- Broad and specific tags need specificity controls based on observed
  frequency, not intuition alone.
- Artist movement is an indirect contextual attribute and can overgeneralize
  an artist's entire oeuvre.
- Medium values are often common; matching oil and canvas alone is weak.
- The bounded tag-anchor selection biases every candidate toward one shared
  tag and must be compared with less homogeneous universes later.
- No human relevance labels or benchmark scores were created in this phase.

