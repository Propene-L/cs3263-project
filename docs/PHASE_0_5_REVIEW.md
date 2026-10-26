# Phase 0.5 — ArtGraph Exploration and Logical Reasoning Readiness

## Scope and method

This review uses the checksum-verified, sanitized ArtGraph v1.0 RDF described in
`dataset_manifest.json`. `scripts/explore_artgraph.py` parses the full graph and
ranks artist-centered samples using measurable structural criteria. It does
not perform museum deduction or recommendation in Python.

A candidate must contain an imported artist–movement edge, at least three
artworks, at least four entity types, at least one non-artist shared relation,
and at least three independent inference paths. Up to six artworks are selected
per artist. Ranking rewards entity-type diversity, relation diversity, shared
relationships, and independent inference paths before size. Exact nodes, edges,
fact IDs, source triples, and scores are in `phase_0_5_candidates.json`.

## 1. Predicate inventory and limitations

| RDF predicate | Domain → range | Full-graph frequency | Executed real example | Multi-step relevance | Importer status |
|---|---|---:|---|---|---|
| `hasSubject` | Artist → Subject | 21,054 | `ag_54` Jeremy Henderson → `ag_127845` “2009 deaths” | Artwork → artist → subject context. Many subjects are broad biographical categories, so educational usefulness needs review. | Added as `has_subject/3`; not an eligible recommendation type by default. |
| `hasPeriod` | Artwork → Period | 5,748 | `ag_8382` “Moon Woman” → `ag_133099` “Early works” | Shared-period artwork relations and period context. Period labels are artist-relative, not universal chronology. | Added as `has_period/3`; Period remains context-only pending review. |
| `partOf` | Artwork → Serie | 8,322 | `ag_8142` “Portrait of Eve” → `ag_133041` “Eve and the Apple, with Counterpart” | Series membership and shared-series peer deductions. | Added as `part_of_series/3`; Series remains context-only pending review. |
| `relatedToSchool` | Artist → Training | 498 | `ag_59` Giovanni Battista Piranesi → `ag_124931` “Matteo Lucchesi” | Artwork → artist → training/school context. The range is typed `Training`, but values may be people or institutions; do not phrase all values as schools without validation. | Added as `related_to_school/3`; Training remains context-only pending review. |

The populated RDF contains the above frequencies. Domain/range claims come
from the bundled ontology. The existing `madeOf`/`belongsToMovement` versus
ontology spelling mismatch remains documented. None of these factual
associations is interpreted as a learning prerequisite.

## 2. Five candidate subgraphs

All five candidates satisfy every structural filter and have a verified
Artwork → Artist → Movement path.

| Rank | Artist seed | Example artworks | Movements | Entities / relations | Types / predicates | Shared groups | Independent paths | Score |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | `ag_1210` Morris Louis | `ag_72463` Where; `ag_72464` Alpha-Pi; `ag_72465` Beta Lambda; plus 3 | `ag_124645` Washington Color School; `ag_124741` Color field; `ag_124790` Post-painterly abstraction | 23 / 47 | 10 / 9 | 6 | 8 | 265 |
| 2 | `ag_2171` Jackson Pollock | `ag_8382` Moon Woman; `ag_8383` Untitled; `ag_8384` Totem Lesson 2; plus 3 | `ag_125114` Abstract expressionism | 23 / 42 | 9 / 8 | 8 | 7 | 248 |
| 3 | `ag_2409` Pieter Bruegel the Elder | `ag_8969` Alpine Landscape; `ag_8970` Census at Bethlehem; `ag_8971` Children’s Games; plus 3 | `ag_124676` Dutch and Flemish Renaissance painting | 23 / 41 | 9 / 8 | 9 | 6 | 244 |
| 4 | `ag_456` Paul Klee | `ag_18987` A gate; `ag_18988` A kind of cat; `ag_18989` A pressure of Tegernsee; plus 3 | `ag_124670` Expressionism; `ag_124703` Surrealism; `ag_124752` Bauhaus | 24 / 33 | 9 / 8 | 5 | 7 | 236 |
| 5 | `ag_1522` Konstantin Yuon | `ag_45381` A young peasant woman in a red scarf; `ag_45382` A.S. Pushkin; `ag_45383` Adam and Eve; plus 3 | `ag_124728` Symbolism; `ag_124744` Impressionism; `ag_125151` Socialist realism | 30 / 37 | 9 / 8 | 6 | 6 | 232 |

Morris Louis ranks first because the bounded sample combines movement, school,
subject, style, genre, media, period, and series paths. It is not merely the
largest candidate. Jackson Pollock and Pieter Bruegel offer strong alternatives:
Pollock has more shared groups, while Bruegel has diverse genres and periods
but no `relatedToSchool` edge in the bounded sample.

## 3. Compositional deduction templates

The following are factual/contextual rules. `F*` variables are imported
`agf_*` source IDs.

### D1 — Artwork movement through derived artist context

```prolog
artwork_artist(W,A,[F1]) :- created_by(W,A,F1).
artist_movement(A,M,[F2]) :- belongs_to_movement(A,M,F2).
artwork_movement(W,M,[F1,F2]) :-
    artwork_artist(W,A,[F1]), artist_movement(A,M,[F2]).
```

Imported facts → derived `artwork_artist` and `artist_movement` → final
`artwork_movement`. This is factual under the ArtGraph assertions.

### D2 — Contextual peer through a derived shared style

```prolog
artwork_style(W,S,[F]) :- has_style(W,S,F).
shared_style_pair(W1,W2,S,[F1,F2]) :-
    artwork_style(W1,S,[F1]), artwork_style(W2,S,[F2]), dif(W1,W2).
contextual_peer(W1,W2,style(S),Proof) :-
    shared_style_pair(W1,W2,S,Proof).
```

Imported facts → two derived artwork-style relationships → derived shared
style → final contextual peer. This is factual association, not prerequisite.

### D3 — Contextual peer through a derived shared genre

```prolog
artwork_genre(W,G,[F]) :- has_genre(W,G,F).
shared_genre_pair(W1,W2,G,[F1,F2]) :-
    artwork_genre(W1,G,[F1]), artwork_genre(W2,G,[F2]), dif(W1,W2).
contextual_peer(W1,W2,genre(G),Proof) :-
    shared_genre_pair(W1,W2,G,Proof).
```

The interpretation is again factual/contextual. Whether a genre is useful to
present next is a separate guidance decision.

### D4 — Training context through artist

```prolog
artist_school(A,S,[F2]) :- related_to_school(A,S,F2).
artwork_school(W,S,[F1,F2]) :-
    artwork_artist(W,A,[F1]), artist_school(A,S,[F2]).
factual_context_topic(W,S,training,Proof) :- artwork_school(W,S,Proof).
```

This is factual under ArtGraph's `Training` typing. Natural-language rendering
must not call every value a school without checking its label/category.

### Recursive proposal — contextual reachability

```prolog
context_edge(X,Y) :- base_context_edge(X,Y).
context_edge(X,Y) :- base_context_edge(Y,X).

:- table context_reachable/2.
context_reachable(X,Y) :- context_edge(X,Y).
context_reachable(X,Z) :-
    context_edge(X,Y), context_reachable(Y,Z), dif(X,Z).
```

Recursive reachability is semantically justified for discovering whether two
entities are connected through the finite, whitelisted context graph. Tabling
terminates on cycles. Reachability alone is too broad to be a recommendation;
Phase 1 must retain typed paths and impose evidence/ranking constraints.

## 4. Actual per-candidate deduction instances

Each candidate supports D1 plus at least two shared-relation compositions.
The table lists exact imported facts that feed the intermediate predicates.

| Candidate | D1 movement chain | D2 shared-style chain | D3 second shared chain |
|---|---|---|---|
| Morris Louis | `ag_72463` → `ag_1210` (`agf_ac9cf6f7052a601f3faa`) → `ag_124645` (`agf_5105e623d3f9451b253c`) | `ag_72463`,`ag_72464` → style `ag_41` (`agf_48bcc01ef5c3d65e1cc6`,`agf_be633e3f92e271533855`) | same artworks → genre `ag_6` (`agf_460af3f86fb80412b668`,`agf_a5b98366b304e8ea31f3`) |
| Jackson Pollock | `ag_8382` → `ag_2171` (`agf_c4eaf83630b10ea3b266`) → `ag_125114` (`agf_9f29e9f0a7109f3de44a`) | `ag_8382`,`ag_8383` → style `ag_35` (`agf_8bc0c6c8c5ef8ded79db`,`agf_3ce3338c184b9c8b6d84`) | `ag_8382`,`ag_8384` → genre `ag_7` (`agf_22b35b506695c7c5b6cd`,`agf_d02cab1f26d5c9f1227d`) |
| Pieter Bruegel | `ag_8969` → `ag_2409` (`agf_0d8ce0532c9ceedd5b92`) → `ag_124676` (`agf_d7e5eea49cd06973c1ca`) | `ag_8969`,`ag_8970` → style `ag_26` (`agf_0cc656c455f60da54f5a`,`agf_12fbafeaca718a90ccdb`) | `ag_8970`,`ag_8971` → genre `ag_4` (`agf_fc068fabba9457dee07b`,`agf_137c2962239373693674`) |
| Paul Klee | `ag_18987` → `ag_456` (`agf_5e2b893186938d0d0282`) → `ag_124670` (`agf_d5ee4ac8e5c22c24cb08`) | `ag_18987`,`ag_18988` → style `ag_21` (`agf_04c93d55349a03adb896`,`agf_8c35ed3b4dff41a94fc6`) | `ag_18990`,`ag_18992` → genre `ag_9` (`agf_0c5f70cd0783e1ae3290`,`agf_8bf5d676ad760570bc6c`) |
| Konstantin Yuon | `ag_45381` → `ag_1522` (`agf_bbb3f0d38280b164bf0b`) → `ag_124728` (`agf_df3726b38e9a38a1a8b4`) | `ag_45384`,`ag_45386` → style `ag_42` (`agf_c4a83a9a19a41ca21a93`,`agf_a7981a6eac0352a387e4`) | `ag_45381`,`ag_45382` → style `ag_43` (`agf_43c412f7f48ae6694e5c`,`agf_6374d817524e0c9666e2`) |

For Morris Louis, D1, D2, a shared-series variant, D4, and recursive
reachability were executed in `test_phase_0_5_pilot.pl`. The other rows are
source-verified proposals from the generated candidate inventory; they have not
been promoted to production rules or claimed as executed proofs.

## 5. Layer A versus Layer B

### Layer A — museum factual inference

Layer A contains the imported fact predicates and rules D1–D4. Its output is a
typed relation plus rule and source-fact IDs. It does not inspect visitor state
and does not call an LLM.

### Layer B — visitor recommendation inference

Proposed guidance rule:

```prolog
eligible_topic(V,T,Reason,Proof) :-
    goal(V,G),
    factual_context_topic(G,T,Reason,Proof),
    allowed_candidate(T),
    \+ knows(V,T),
    \+ presented(V,T),
    \+ skipped(V,T).
```

Negation is evaluated only after `T` is grounded by the finite factual and
allowed-candidate predicates. It means “not recorded as covered,” never “the
visitor is proven ignorant.”

Representative proposed recommendations:

| Goal and topic | Underlying factual derivation | Guidance assumption | Why eligible | Disappears when… |
|---|---|---|---|---|
| Goal `ag_72463` Where → movement `ag_124741` Color field | `ag_72463` created by `ag_1210`; artist belongs to movement `ag_124741` | An artist movement is a useful explanatory context for an artwork. | Movement is in the shared allowed type set and has a two-fact proof. | topic becomes known, presented, skipped, removed from allowed IDs, or the goal changes. |
| Goal `ag_72464` Alpha-Pi → style `ag_41` color field painting | The goal and five peer works derive `artwork_style`, then shared-style context. | A repeatedly supported style may be useful context. | Style is allowed and supported by the goal plus peer evidence. | same filters; also disappears if the required style facts are absent from the context snapshot. |
| Goal `ag_72464` Alpha-Pi → medium `ag_2630` acrylic | `made_of` facts connect Alpha-Pi and three peers to acrylic. | A shared medium may be useful explanatory context. | Medium is allowed and evidence is not unique to one work. | same visitor filters, goal/context change, or medium removed from allowed candidates. |

Period, series, subject, and training remain context-only types. Making any of
them recommendable changes the frozen candidate contract and requires explicit
human approval plus evaluation labels.

## 6. Recommended subgraph

Adopt the Morris Louis candidate (`artist_ag_1210`) for Phase 1 development.
It has verified movement paths, six connected artworks, all four newly audited
predicates, six shared relation groups, and enough independent evidence for
movement, peer, period, series, school, subject, medium, and recursive path
tests. Its generated snapshot is
`data/curated/artgraph_v1_phase_0_5_recommended.ttl`.

The recommendation concerns structural suitability for testing. It is not a
claim about educational superiority or historical importance.

## 7. Required Phase 1 changes

1. Replace the Phase 0 pilot sample as the primary development snapshot only
   after reviewer approval; retain the original sample for regression tests.
2. Move tested factual rules into a production Layer A module with explicit
   proof terms and negative/unsupported tests.
3. Implement Layer B separately, grounding candidate IDs before closed-world
   filtering and keeping candidate eligibility independent of an LLM.
4. Decide whether Period, Series, Subject, or Training may enter the common
   candidate universe. Current code imports them but excludes them.
5. Decide a deterministic relation priority and proof-length ranking policy.
6. Constrain recursive reachability by typed paths; do not recommend arbitrary
   reachable entities.
7. Add at least one scenario whose expected usefulness labels are reviewed
   independently rather than generated from these rules.

## 8. Remaining concerns

- The Zenodo record still shows no explicit licence; no bulk RDF or images are
  redistributed. The additional committed material is a bounded 23-entity
  text snapshot plus metadata/provenance.
- ArtGraph labels originate from WikiArt/DBpedia and may contain HTML entities,
  inconsistent capitalization, broad Wikipedia categories, or contested
  classifications. This audit does not independently verify art-historical
  truth.
- `relatedToSchool` ranges over `Training`, but examples include people as well
  as institutions. Rendering needs type/label review.
- High graph connectivity can make recursive reachability logically true but
  educationally unhelpful. Proof validity and recommendation utility must be
  evaluated separately.
- Candidate ranking is an engineering audit heuristic, not an experiment
  result or a gold recommendation ranking.

## Generated review artifacts

- Machine-readable candidates: `docs/phase_0_5_candidates.json`
- Interactive viewer: `docs/phase_0_5_graph_explorer.html`
- Recommended RDF snapshot: `data/curated/artgraph_v1_phase_0_5_recommended.ttl`
- Recommended topic catalog: `data/curated/phase_0_5_topic_catalog.json`
- Provenance-bearing Prolog facts: `logic/phase_0_5_generated_facts.pl`
- Tested pilot rules: `logic/phase_0_5_pilot_rules.pl`

