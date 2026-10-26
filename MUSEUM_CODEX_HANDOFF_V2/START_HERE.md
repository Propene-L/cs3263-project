# Start here — Codex Handoff V2

1. Extract this archive into the `museum-logic-guide` repository root.
2. Treat `CODEX_HANDOFF_MUSEUM_V2.md` and `AGENTS.md` as authoritative over any older `CODEX_HANDOFF_MUSEUM.md`, `AGENTS_MUSEUM_TEMPLATE.md`, or `CS3263_Museum_Prototype_Development_Plan.md` in the repository.
3. Open Codex in this repository, and send the text under **Section 7 — Immediate kickoff prompt** in `CODEX_HANDOFF_MUSEUM_V2.md`.
4. Codex must implement **Phase 0 only**, then stop for review. Next phases are implementation gates, not permission to build everything at once.
5. Ensure SWI-Prolog is installed locally. `swipl --version` must work. Runtime did not have SWI-Prolog installed during handoff authoring, so no live Prolog code or command was claimed to be tested here.

**Intended architecture:** ArtGraph RDF → Python normalization → Prolog inference + visitor state → candidates / proof trace → optional LLM rendering. Compare against paper-inspired KG similarity and direct LLM using the same candidate topic universe.
