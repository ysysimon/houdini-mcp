# Roadmap: .hip File Ingest & Pattern Extraction

## Goal

Build a pipeline that reads `.hip` files (readable text), extracts network patterns, node configurations, and connection graphs, and indexes them for searchable retrieval. This gives Claude concrete examples of how real Houdini scenes are built — what nodes connect to what, what parameter values produce good results, and what common network structures look like.

## Prerequisites

- A corpus of `.hip` files (tutorial scenes, SideFX examples, user work)
- Understanding of the `.hip` text format (node definitions, parameter blocks, connections)

## Phase 1: Format Discovery

**Goal:** Understand the `.hip` text format well enough to parse it reliably.

- [ ] Collect 3-5 representative `.hip` files (simple geo, lit scene, Mantra render)
- [ ] Read and annotate the structure — identify how nodes, parameters, connections, and network hierarchy are represented in the text
- [ ] Document the format patterns in `docs/hip_format.md` (node blocks, param syntax, connection syntax, network nesting)
- [ ] Identify what's useful to extract vs. noise (UI layout positions, viewport state, etc. are noise)

**Output:** Format reference doc, list of extractable fields.

## Phase 2: Parser

**Goal:** A Python module that reads a `.hip` file and returns structured data.

- [ ] Create `hip_parser.py` (stdlib only, same zero-dep philosophy as `houdini_rag.py`)
- [ ] Parse into structured output:
  - **Nodes**: type, path, name, category (SOP/OBJ/ROP/LOP/etc.)
  - **Parameters**: name-value pairs per node (skip defaults/unchanged)
  - **Connections**: input/output wiring between nodes (the network graph)
  - **Network hierarchy**: parent-child nesting (e.g., `/obj/geo1/` contains SOPs)
- [ ] Handle edge cases: expressions, channel references, string params with special chars
- [ ] Tests: parse known `.hip` files, assert expected node counts, connections, param values

**Output:** `hip_parser.py` + tests. Takes a `.hip` path, returns a dict/list structure.

## Phase 3: Pattern Extraction

**Goal:** Distill parsed scenes into reusable workflow patterns.

- [ ] Define "pattern" vocabulary:
  - **Network pattern**: a subgraph (e.g., "geo → material → light → mantra ROP")
  - **Node recipe**: a node type + its non-default parameter values (e.g., "Mantra ROP with GI settings")
  - **Connection idiom**: common wiring patterns (e.g., "merge SOPs feeding into a null output")
- [ ] Write `hip_patterns.py` — takes parser output, extracts patterns:
  - Walk the node graph, identify common subgraph shapes
  - Cluster nodes by context (OBJ-level networks, SOP-level networks, ROP networks)
  - Extract "interesting" parameter sets (non-default values that define the setup)
- [ ] Deduplicate across multiple `.hip` files — find recurring patterns

**Output:** `hip_patterns.py`. Takes parsed scene data, returns a list of named patterns with node types, connections, and key parameters.

## Phase 4: Indexing & Storage

**Goal:** Make extracted patterns searchable, similar to the existing BM25 docs index.

- [ ] Store patterns as text documents (one per pattern) in `hip_patterns/` (gitignored for user-generated content, or committed for curated patterns)
- [ ] Index with `houdini_rag.py` BM25 — extend or create a parallel index (`hip_patterns_index.json`)
- [ ] Alternatively: store as structured JSON files that Claude reads directly via the workflow doc routing (see ROADMAP_WORKFLOW_INSTRUCTIONS.md)
- [ ] Decision: BM25 search vs. direct file reads vs. both

**Output:** Indexed, searchable pattern library.

## Phase 5: Batch Ingest Agent

**Goal:** An agent workflow that processes a directory of `.hip` files overnight.

- [ ] Create `scripts/ingest_hips.py` — walks a directory, parses each `.hip`, extracts patterns, writes output
- [ ] Progress reporting (file N of M, patterns found so far)
- [ ] Output: pattern docs + index, ready for Claude to search/read
- [ ] Can run headless (no Houdini needed — pure text parsing)

**Output:** One-command batch ingest. Point at a folder of `.hip` files, get a searchable pattern library.

## Open Questions

- What `.hip` corpus to start with? SideFX ships example files with Houdini — those are a natural starting point.
- How granular should patterns be? Full scene graphs vs. focused subgraphs (e.g., just the lighting rig, just the SOP network)?
- Should the pattern library be committed to the repo (curated, versioned) or gitignored (user-generated, local)?
- Integration with existing `search_docs` / `get_doc` tools — new MCP tools, or extend existing ones?
