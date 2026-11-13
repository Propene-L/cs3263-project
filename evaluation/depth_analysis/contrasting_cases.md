# Contrasting multi-round clarification cases

These are paired trajectories from the committed Phase 1.1 result artifact.
Both methods receive identical states, candidate pools, response semantics, and
visitor responses. The examples show that aggregate discrimination is useful
but does not dominate for every hidden controlled hypothesis.

## `controlled_multi_16`

Hidden controlled hypothesis: water-transport subjects (`h_water_subject`).

### Compositional Prolog

Initial active hypotheses: cubist style (`h_cubist_style`), oil medium (`h_oil_medium`), portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`).

- Round 1: selected Rapallo boats (`ag_10149`) versus A poet (`ag_19176`). Predicted partition — prefer_a: oil medium (`h_oil_medium`), water-transport subjects (`h_water_subject`); prefer_b: cubist style (`h_cubist_style`), portrait genre (`h_portrait_genre`); unknown: none. The visitor response was `prefer_a`; eliminated 2 hypothesis/hypotheses; active afterward: oil medium (`h_oil_medium`), water-transport subjects (`h_water_subject`).
- Round 2: selected A floating figure (`ag_10025`) versus Calm Sea. Landscape with fishermen (`ag_14588`). Predicted partition — prefer_a: oil medium (`h_oil_medium`); prefer_b: water-transport subjects (`h_water_subject`); unknown: none. The visitor response was `prefer_b`; eliminated 1 hypothesis/hypotheses; active afterward: water-transport subjects (`h_water_subject`).

Outcome: `correctly_resolved=true`, stop reason `resolved_unique`, 1 active hypothesis/hypotheses remaining.

### Single-rule Prolog

Initial active hypotheses: cubist style (`h_cubist_style`), oil medium (`h_oil_medium`), portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`).

- Round 1: selected A floating figure (`ag_10025`) versus A&#160;Disc in&#160;the City (`ag_14292`). Predicted partition — prefer_a: oil medium (`h_oil_medium`); prefer_b: cubist style (`h_cubist_style`); unknown: portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`). The visitor response was `unsure`; eliminated 0 hypothesis/hypotheses; active afterward: cubist style (`h_cubist_style`), oil medium (`h_oil_medium`), portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`).
- Round 2: selected A mountain (`ag_10026`) versus Castle Garden (`ag_19013`). Predicted partition — prefer_a: oil medium (`h_oil_medium`); prefer_b: cubist style (`h_cubist_style`); unknown: portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`). The visitor response was `unsure`; eliminated 0 hypothesis/hypotheses; active afterward: cubist style (`h_cubist_style`), oil medium (`h_oil_medium`), portrait genre (`h_portrait_genre`), water-transport subjects (`h_water_subject`).
- Round 3: selected Rapallo boats (`ag_10149`) versus A poet (`ag_19176`). Predicted partition — prefer_a: oil medium (`h_oil_medium`), water-transport subjects (`h_water_subject`); prefer_b: cubist style (`h_cubist_style`), portrait genre (`h_portrait_genre`); unknown: none. The visitor response was `prefer_a`; eliminated 2 hypothesis/hypotheses; active afterward: oil medium (`h_oil_medium`), water-transport subjects (`h_water_subject`).

Outcome: `correctly_resolved=false`, stop reason `round_limit`, 2 active hypothesis/hypotheses remaining.


## `phase_1_1_multi_021`

Hidden controlled hypothesis: feline subjects (`h_feline_subject`).

### Compositional Prolog

Initial active hypotheses: Expressionism movement (`h_expressionist_movement`), feline subjects (`h_feline_subject`), impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`).

- Round 1: selected A mountain (`ag_10026`) versus Boy by the Water (`ag_11014`). Predicted partition — prefer_a: Expressionism movement (`h_expressionist_movement`); prefer_b: impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`); unknown: feline subjects (`h_feline_subject`). The visitor response was `unsure`; eliminated 0 hypothesis/hypotheses; active afterward: Expressionism movement (`h_expressionist_movement`), feline subjects (`h_feline_subject`), impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`).
- Round 2: selected Rapallo boats (`ag_10149`) versus Children in a Garden at Eragny (`ag_23352`). Predicted partition — prefer_a: Expressionism movement (`h_expressionist_movement`); prefer_b: impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`); unknown: feline subjects (`h_feline_subject`). The visitor response was `unsure`; eliminated 0 hypothesis/hypotheses; active afterward: Expressionism movement (`h_expressionist_movement`), feline subjects (`h_feline_subject`), impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`).
- Round 3: selected The Tabby (`ag_11706`) versus Bennecourt (`ag_25845`). Predicted partition — prefer_a: feline subjects (`h_feline_subject`); prefer_b: impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`); unknown: Expressionism movement (`h_expressionist_movement`). The visitor response was `prefer_a`; eliminated 2 hypothesis/hypotheses; active afterward: Expressionism movement (`h_expressionist_movement`), feline subjects (`h_feline_subject`).

Outcome: `correctly_resolved=false`, stop reason `round_limit`, 2 active hypothesis/hypotheses remaining.

### Single-rule Prolog

Initial active hypotheses: Expressionism movement (`h_expressionist_movement`), feline subjects (`h_feline_subject`), impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`).

- Round 1: selected A mountain (`ag_10026`) versus The Tabby (`ag_11706`). Predicted partition — prefer_a: Expressionism movement (`h_expressionist_movement`); prefer_b: feline subjects (`h_feline_subject`); unknown: impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`). The visitor response was `prefer_b`; eliminated 1 hypothesis/hypotheses; active afterward: feline subjects (`h_feline_subject`), impressionist style (`h_impressionist_style`), nature-reserve subjects (`h_nature_subject`).
- Round 2: selected A Caucasian Study (`ag_10632`) versus Dead Cat (`ag_12564`). Predicted partition — prefer_a: impressionist style (`h_impressionist_style`); prefer_b: feline subjects (`h_feline_subject`); unknown: nature-reserve subjects (`h_nature_subject`). The visitor response was `prefer_b`; eliminated 1 hypothesis/hypotheses; active afterward: feline subjects (`h_feline_subject`), nature-reserve subjects (`h_nature_subject`).
- Round 3: selected Boy by the Water (`ag_11014`) versus Lion (`ag_17716`). Predicted partition — prefer_a: nature-reserve subjects (`h_nature_subject`); prefer_b: feline subjects (`h_feline_subject`); unknown: none. The visitor response was `prefer_b`; eliminated 1 hypothesis/hypotheses; active afterward: feline subjects (`h_feline_subject`).

Outcome: `correctly_resolved=true`, stop reason `resolved_unique`, 1 active hypothesis/hypotheses remaining.


## Interpretation

`controlled_multi_16` demonstrates the intended benefit: the compositional
selector considers all active hypothesis pairs and reaches the hidden singleton
before the three-question limit, whereas the single-rule selector does not.
`phase_1_1_multi_021` is the required counterexample. Its compositional choices
maximize aggregate pair distinction, but the hidden hypothesis produces
responses that preserve ambiguity; the single-rule trajectory happens to
resolve that particular hidden hypothesis. Neither case is evidence about
human preference behavior because the responses come from the declared
positive-support simulator.
