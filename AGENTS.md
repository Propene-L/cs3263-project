# AGENTS.md — CS3263 Museum Logic Guide V2

## Required reading before editing

1. `CODEX_HANDOFF_MUSEUM_V2.md` (authoritative phase plan)
2. `docs/REVISED_ARCHITECTURE.md` (semantics and implementation limits)
3. `docs/EVALUATION_PROTOCOL.md` (baseline separation and labels)

V2 supersedes `CODEX_HANDOFF_MUSEUM.md` and `docs/development_spec.md`.

## Locked choices

- Python 3.11+ orchestrates; **SWI-Prolog** performs logical inference.
- Use genuine ArtGraph v1.0 RDF facts with source URIs and stable IDs.
- Synthetic RDF is test-only and must be labeled.
- Python must not reimplement the deduction/recommendation rules with `if/else`
  or graph traversal. Extraction may traverse RDF only to create a bounded
  sample; this is not inference.
- The symbolic system's LLM may extract validated state or render language but
  may not select a recommendation.
- Embedding/similarity and direct-LLM baselines remain independent from Prolog
  proofs and gold labels.
- Build and test one phase at a time. Do not proceed without human review.

## Safety and reproducibility

- Never execute visitor text as Prolog. Accept only allowlisted stable IDs.
- Preserve imported fact provenance and distinguish facts from educational
  guidance assumptions.
- Do not commit secrets, personal transcripts, downloaded bulk RDF, or images.
- Never invent museum facts, test results, or evaluation scores.
- At phase completion report files, exact commands, results, a real proof,
  limitations/licensing, and the next review gate.
