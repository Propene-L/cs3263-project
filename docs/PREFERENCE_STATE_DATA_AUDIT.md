# Phase 1.2 Preference-State Data Audit

## Source and search universe

The builder uses the unchanged Phase 1 clarification evidence export:

- 112 genuine ArtGraph artworks;
- 10 reviewed typed hypotheses;
- provenance-bearing `agf_*` fact IDs;
- no downloaded bulk RDF or images added to Git.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\build_preference_state_benchmark.py
```

The machine-readable audit is in `docs/preference_state_data_audit.json`.

## Discovery results

| Family | Viable constructions found | Selected scenarios |
|---|---:|---:|
| Contrastive atomic | 333 | 12 |
| Compositional interaction | 22 | 12 |

The final benchmark has 24 scenarios: 13 development and 11 held-out. The two
user-specified flagship cases are first-class development regressions. The
remaining cases are selected deterministically from sorted real artwork and
hypothesis IDs; held-out cases are never used to change scoring parameters.

### Family A criteria

- liked and disliked artworks share at least two hypothesis attributes;
- exactly one reviewed hypothesis is recorded on the liked artwork but not the
  disliked artwork;
- a clean probe supports only that differentiating hypothesis;
- a distractor supports at least two shared hypotheses but not the
  differentiating hypothesis.

Requiring exactly one differentiating attribute prevents the controlled label
from arbitrarily choosing among equally diagnostic liked-only attributes.

### Family B criteria

- a liked artwork supports both allowed interaction components;
- two distinct disliked artworks support separate components, with the other
  component `not_recorded`;
- another artwork supports both components;
- a distractor supports only part of the conjunction;
- the observation triple derives exactly one allowed interaction pair.

The last condition prevents an arbitrary latent label when the same history
supports several interaction candidates.

## Flagship provenance

For `Albert Kollmann` (`ag_8416`), the recorded input evidence includes:

- expressionist style: `agf_8a4cce07ba2a1ca7c617`;
- portrait genre: `agf_622844512b2c37462fa9`;
- oil medium: `agf_e3001683bd7d0266a162`;
- artist/movement join: `agf_7888e12232ccab014115` and
  `agf_c642b6942e0c256567ca`.

The two disliked component examples contribute
`agf_bc28f5fe332dea18b2b7` and `agf_b9a2ae950dd18cec4bac`.
`Baby` (`ag_20804`) has conjunction support
`agf_7f54f5f65b1cedf3fe4f` and `agf_373d77fbb313b7f40e0d`.

## Biases and limitations

- The interaction benchmark is constructed from the same declared pattern the
  compositional rule implements. It tests faithful execution and consequences
  of that model; it is not an independent human validation of the model.
- Only ten reviewed attributes are visible. Unmodeled color, composition,
  iconography, familiarity, or affect cannot be recovered.
- `not_recorded` is snapshot incompleteness, never proof that an artwork lacks
  a feature.
- Clean probes may be textually or visually poor questions despite satisfying
  the controlled construction.
- The ArtGraph Zenodo record's displayed licence field was unresolved during
  Phase 0, so bulk RDF and images remain undistributed.
