# Revised Architecture and Semantics

## Research problem

Given a finite ArtGraph-derived fact set `F`, a fixed documented Horn-clause
rule set `R`, a visitor goal `g`, and a known-topic set `K`, derive supported
and relevant next topics and apply a deterministic documented ranking policy.
This is a reference guide, not a psychometric diagnosis.

## Operational architecture

1. Official ArtGraph RDF is checksum-verified, audited, and converted into a
   bounded provenance-bearing fact snapshot.
2. Stable topic IDs and an identical candidate universe are shared by the
   symbolic, KG-similarity, and direct-LLM systems.
3. Validated visitor state is passed to a fresh SWI-Prolog subprocess.
4. Prolog performs unification, clause resolution, recursive/multi-rule
   deduction, and candidate derivation.
5. Python validates and ranks only entailed candidates. It does not recreate
   logical predicates with conditionals or graph traversal.
6. An optional LLM may propose allowlisted state updates or phrase grounded
   output, but never chooses the symbolic recommendation.

RDF extraction may use deterministic breadth-first traversal to create the
finite sample. This preprocessing operation is not the deduction engine.

## Frozen Phase 0 contracts

- `Topic`: `{id,type,label,source_uri,properties}` where type is one of
  `artwork|artist|movement|style|genre|medium`. Artworks may be goals; default
  recommendation candidates are the five explanatory types.
- `Fact`: `{predicate,args,source_triple_id,source_uri,provenance}`.
- `VisitorState`: session, goal, known/presented/skipped topic IDs, and recent
  turns.
- `Candidate`: stable topic ID, `RECOMMEND`, rank, method, and proof support
  containing rule IDs and imported fact IDs.
- `RecommendInput`: scenario, goal, known/skipped IDs, allowed candidate IDs,
  and context snapshot ID.
- `RecommendOutput`: method, ranked IDs, details, runtime, metadata, errors.
- `StateDelta`: allowlisted additions/removals, goal change, skips, confidence,
  and uncertainty. It cannot create rules or RDF facts.

## Semantics

Factual ArtGraph associations and educational guidance are distinct. A style,
genre, artist, movement, or medium related to an artwork is contextual evidence,
not automatically a learning prerequisite. On the finite allowed candidate set,
absence from `K` can mean “not recorded as covered” for filtering; it never
proves ignorance or a negative museum fact.

SWI-Prolog's clauses use goal-directed resolution and unification. Phase 1 may
use tabling for cycle-safe recursion. Proof output must be purpose-built from
rule IDs, substitutions, and imported `agf_*` facts—not an English summary or
the debugger trace. A fresh subprocess per state avoids stale tables and
cross-session leakage.

## Scope limits

- Function-free Horn-clause logic programming, not a general FOL/OWL reasoner.
- No claim that logical correctness establishes educational usefulness.
- No raw visitor language interpolated into Prolog.
- No frontend, LLM integration, baselines, or full recommendation policy in
  Phase 0.

