# Phase 2 — Python orchestration and visitor updates

This phase integrates a session-scoped command/hybrid conversation layer with
the existing corrected preference-state engine. The archive supplied for this
phase targeted commit `5fd3dec`; its Phase 2-compatible parts were adapted to
the V2 architecture rather than copied mechanically.

## Implemented boundary

- Manual mode parses a small explicit command language for offline use.
- Hybrid mode may ask a configured Responses-compatible provider to propose a
  structured state delta. The proposal is allowlist-validated before any state
  change and cannot select an action.
- A fresh SWI-Prolog process selects preference actions through the existing
  corrected preference-state rules.
- A separate fresh SWI-Prolog process traverses the small documented
  educational-guidance prerequisite graph and selects its next action.
- Python owns validation, atomic session updates, subprocess lifecycle, output
  validation, and source-bounded rendering. It does not traverse the guidance
  graph or choose a recommendation.
- Imported ArtGraph facts and educational guidance assumptions remain visibly
  distinct in rendered provenance.

The package's Python prerequisite selector was intentionally not used because
it conflicts with `AGENTS.md`. Its direct-LLM action selector, scripted
evaluation runner, and Streamlit UI belong to later phases and remain outside
this review gate.

## Offline commands

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\swipl\bin\swipl.exe --version
.\.venv\Scripts\python.exe -m museum_guide.cli --mode manual --demo
.\.venv\Scripts\python.exe -m museum_guide.cli --mode manual --json-audit
```

Manual inputs use only stable IDs from the committed bounded catalogs:

```text
like ag_8416
dislike ag_13231
interested h_expressionist_style
topic c_expressionist_portrait
know c_art_style
dont-know c_portrait
yes
no
unsure
skip
```

The session is in memory only. `reset` creates a fresh state. A validation,
provider, or solver error does not mutate the prior session.

## Optional hybrid extraction

Set `OPENAI_API_KEY` and `MUSEUM_LLM_MODEL` locally, and optionally
`MUSEUM_LLM_ENDPOINT` for a compatible endpoint, then run:

```powershell
.\.venv\Scripts\python.exe -m museum_guide.cli --mode hybrid
```

No live provider call or provider-quality result is claimed by the offline
tests. Provider credentials must remain in environment variables.

## Trust boundary

`visitor text -> proposed JSON delta -> allowlist validation -> copied session
state -> fresh Prolog solve -> validated decision/proof -> fixed renderer`

Raw visitor text is never interpolated into Prolog. Only IDs matching the safe
atom grammar and present in the relevant catalog are serialized. The bounded
educational prerequisite edges are guidance assumptions, not RDF assertions.

## Current limits and review gate

- Educational text and prerequisite choices are a small curated layer whose
  pedagogical usefulness has not been independently evaluated.
- ArtGraph's displayed v1.0 license remains unresolved; bulk RDF and images are
  not redistributed.
- Hybrid extraction still needs a separately reported live evaluation.
- Direct-LLM baseline integration, formal evaluation artifacts, and UI work are
  deliberately deferred until Phase 2 receives human review.
