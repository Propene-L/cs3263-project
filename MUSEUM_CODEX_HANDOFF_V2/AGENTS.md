# AGENTS.md — CS3263 Museum Logic Guide V2

## Required reading before editing
1. `CODEX_HANDOFF_MUSEUM_V2.md` (authoritative phase plan)
2. `docs/REVISED_ARCHITECTURE.md` (semantics, input/output schemas, implementation limits)
3. `docs/EVALUATION_PROTOCOL.md` (baseline separation and labels)

## Locked choices
- Main software: Python 3.11+. Logic/rule inference: **SWI-Prolog**, not a Python rule selector.
- Museum source: **ArtGraph v1.0**. Import genuine RDF facts with source URIs and stable IDs; synthetic fixtures only for tests.
- Known-topic set + finite closed-world **recommendation** assumption, not a claim of visitor ignorance.
- Shared candidate topic IDs across three methods: symbolic, paper-inspired KG embedding/similarity, direct LLM.
- Follow-up topic selection must be based on entailed and evidence-supported relations; do not assert all graph edges are educational prerequisites.
- Prolog reasoning and derived proof steps must be inspectable. Do not call simple Python traversal "FOL deduction".
- The symbolic method cannot call the LLM for next-topic choice; LLM only extracts state and renders language.
- Baselines must not call or leak Prolog's recommendation predicate, proof traces, or gold labels.
- Build/testing is phase-gated. **Do not jump ahead from Phase 0.**

## Safety and reproducibility
- No executable code from visitor input; strict allowlists and safe JSON/prolog serialization.
- Do not store secrets, personal transcripts or downloaded bulk ArtGraph archives in Git.
- No unsupported museum history claims; quote real RDF facts/sources.
- All report metrics must come from actual executed experiment results, not fixtures or simulated scores.
- Prefer SWI-Prolog subprocess/JSON for MVP; test both `pytest` and Prolog's plunit.
- Keep per-session state isolated; reset/recompute derived tables after knowledge updates (stateless calls encouraged).
- For external dependencies, report installation blockers honestly. Do not claim packages were installed or tests passed unless verified.
- Document human development vs Codex-generated components for course academic integrity.

## End-of-phase report format
1. Files changed, interfaces frozen
2. Commands actually run and pass/fail output
3. A real minimal example including input RDF facts, unification/substitutions, derived topic and proof source IDs
4. Open limitations and data/license provenance
5. Next step — await review before advancing
