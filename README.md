# CS3263 Logic-Driven Museum Guide — V2 Phase 0

This repository implements the Phase 0 ArtGraph-to-Prolog pilot. The current
pipeline audits the official ArtGraph v1.0 RDF archive, removes a documented
malformed appended preview, extracts a deterministic connected subgraph,
exports source-linked ground Prolog facts, and executes real Horn-clause rules
in SWI-Prolog. Python does not select recommendations or reimplement the rules.

The V2 handoff supersedes the older JSON prerequisite-selector prototype.
Frontend, LLM integration, visitor recommendation rules, and comparison
baselines are intentionally outside Phase 0.

## Dependencies

- Python 3.11+
- SWI-Prolog (verified during development with 10.0.2 for x64 Windows)
- `rdflib` and `pytest`, installed by the project extras

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
swipl --version
```

If SWI-Prolog is not on `PATH`, set `SWIPL_PATH` to its executable. The local
development run used `.tools/swipl/bin/swipl.exe`; `.tools/` is gitignored.

## Obtain and audit ArtGraph

Download only `artgraph-rdf.zip` from the official Zenodo v1.0 record into
`data/raw/` (which is gitignored):

<https://zenodo.org/records/6337958/files/artgraph-rdf.zip?download=1>

The expected MD5 is `20b5d4ed4539151b0e048758a4f9f9a1`. The Zenodo record
does not display an explicit licence; do not redistribute the bulk archive or
images until rights are clarified.

```powershell
.\.venv\Scripts\python.exe scripts\inspect_artgraph.py `
  --input data\raw\artgraph-rdf.zip `
  --sanitized-output data\raw\artgraph-facts.sanitized.ttl `
  --output docs\artgraph_audit.json

.\.venv\Scripts\python.exe scripts\extract_subgraph.py `
  --input data\raw\artgraph-facts.sanitized.ttl `
  --seed 8142 `
  --output data\curated\artgraph_v1_seed_8142.ttl `
  --catalog data\curated\topic_catalog.json `
  --max-depth 2 --max-neighbors-per-predicate 3

.\.venv\Scripts\python.exe scripts\export_prolog_facts.py `
  --input data\curated\artgraph_v1_seed_8142.ttl `
  --catalog data\curated\topic_catalog.json `
  --output logic\generated_facts.pl `
  --snapshot-id artgraph_v1_seed_8142
```

The official Turtle has a Neo4j HTTP request and ten-record preview appended at
line 3,046,817. The audit script stops at that explicit marker, records removed
line counts and hashes, and never modifies the downloaded archive.

## Run inference and tests

```powershell
.\.venv\Scripts\python.exe scripts\run_pilot_query.py --artwork ag_8142
.\.tools\swipl\bin\swipl.exe -q -s logic\tests\test_pilot.pl -g run_tests -t halt
.\.venv\Scripts\python.exe -m pytest -q
```

The real sample maps ArtGraph resource `8142` (“Portrait of Eve”) to its
imported artist, style, genre, and media facts. These are contextual factual
relations, not educational prerequisites. See `docs/dataset_manifest.json` and
`docs/rulebook.md`.

## Phase 0.5 structural exploration

```powershell
.\.venv\Scripts\python.exe scripts\explore_artgraph.py `
  --input data\raw\artgraph-facts.sanitized.ttl `
  --output-json docs\phase_0_5_candidates.json `
  --output-html docs\phase_0_5_graph_explorer.html `
  --recommended-rdf data\curated\artgraph_v1_phase_0_5_recommended.ttl `
  --recommended-catalog data\curated\phase_0_5_topic_catalog.json `
  --limit 5 --max-artworks 6

.\.venv\Scripts\python.exe scripts\export_prolog_facts.py `
  --input data\curated\artgraph_v1_phase_0_5_recommended.ttl `
  --catalog data\curated\phase_0_5_topic_catalog.json `
  --output logic\phase_0_5_generated_facts.pl `
  --snapshot-id artgraph_v1_phase_0_5_morris_louis

.\.tools\swipl\bin\swipl.exe -q `
  -s logic\tests\test_phase_0_5_pilot.pl -g run_tests -t halt
```

The interactive, self-contained graph viewer is
`docs/phase_0_5_graph_explorer.html`. It shows all five candidates, typed node
colors, predicate edges, structural statistics, stable IDs, and original RDF
triples on hover/click. The Morris Louis sample is recommended for review, not
yet adopted as the Phase 1 production knowledge base.

