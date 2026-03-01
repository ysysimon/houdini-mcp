# Roadmap: Workflow Instructions in FastMCP

## Goal

Add a routing layer to the FastMCP `instructions` string that directs Claude to read relevant workflow docs before attempting Houdini tasks. Instead of guessing how to build a scene, Claude checks the playbook first.

The pattern: **instructions tell Claude *where to look*, workflow docs tell Claude *what to do*.**

## Architecture

```
FastMCP instructions (always visible to Claude)
  ├── Existing: connection rules (1-8)
  └── New: workflow routing rules
        "Before creating geometry → read docs/workflows/geometry.md"
        "Before setting up lighting → read docs/workflows/lighting.md"
        "Before rendering with Mantra → read docs/workflows/mantra.md"
        ...

docs/workflows/
  ├── geometry.md        ← geo creation patterns, common SOPs, best practices
  ├── lighting.md        ← light types, GI/bounce, environment setup
  ├── mantra.md          ← ROP config, camera setup, render settings
  └── (future)           ← animation, simulation, USD, PDG, etc.
```

## Phase 1: Workflow Docs — Core Three

**Goal:** Hand-written workflow guides for the current use case (geometry, lighting, Mantra rendering). Grounded in Houdini docs and real patterns.

### `docs/workflows/geometry.md`
- [ ] Geometry creation from description: OBJ → GEO node → SOPs inside
- [ ] Common SOP patterns: box/sphere/tube/grid → transform → merge
- [ ] Procedural patterns: copy to points, scatter, boolean, extrude
- [ ] Naming conventions and network organization
- [ ] When to use `execute_houdini_code` vs. node creation tools
- [ ] Common mistakes Claude makes (wrong node context, missing display flag)

### `docs/workflows/lighting.md`
- [ ] Light node types in Houdini (hlight, environment, sun, area, etc.)
- [ ] Setting up GI and bounce lighting — which parameters matter
- [ ] Environment light with HDRI
- [ ] Three-point lighting setup as a baseline pattern
- [ ] Light linking basics
- [ ] Common mistakes (lights at origin, zero intensity, wrong light category)

### `docs/workflows/mantra.md`
- [ ] Mantra ROP setup: create node, set camera, set output path
- [ ] Camera creation and positioning (relating to scene bounds)
- [ ] Resolution, sampling, and quality settings
- [ ] Material assignment workflow (principled shader → assign to geo)
- [ ] Render layer basics
- [ ] Common mistakes (no camera, no output path, missing materials = grey)
- [ ] When to use `monitor_render` for long renders

**Source material:**
- Existing fetched Houdini docs (`search_docs` / `get_doc`)
- SideFX tutorials and getting-started guides
- Extracted patterns from `.hip` file ingest (once Phase 1 of ROADMAP_HIP_INGEST.md is done)

**Output:** Three markdown files in `docs/workflows/`, written for Claude (not humans) — concise, step-oriented, parameter-specific.

## Phase 2: FastMCP Instruction Routing

**Goal:** Add routing rules to the `instructions` string so Claude reads the right doc before acting.

- [ ] Add a "Workflow Reference" section to the FastMCP `instructions` in `houdini_mcp_server.py`
- [ ] Rules format — direct and specific:
  ```
  9. **Read workflow docs before complex tasks.** Before building a scene or network:
     - Geometry creation or SOP work → read docs/workflows/geometry.md
     - Lighting setup → read docs/workflows/lighting.md
     - Mantra rendering → read docs/workflows/mantra.md
     Use the search_docs tool or read the file directly. Do NOT guess workflows.
  ```
- [ ] Keep instructions concise — routing only, not the workflows themselves
- [ ] Test: verify Claude actually reads the docs when prompted with relevant tasks

**Output:** Updated `instructions` string in `houdini_mcp_server.py`.

## Phase 3: Integration with .hip Patterns

**Goal:** Connect the workflow docs to patterns extracted from real `.hip` files (from ROADMAP_HIP_INGEST.md).

- [ ] Once `.hip` ingest produces pattern docs, reference them from workflow docs
  - e.g., `geometry.md` links to extracted SOP network patterns
  - e.g., `mantra.md` links to extracted Mantra ROP configurations
- [ ] Decide format: inline the patterns into workflow docs, or keep them separate and reference by path
- [ ] Add routing rules for pattern search: "Search hip_patterns for examples of X"

**Output:** Workflow docs enriched with real-world patterns from `.hip` files.

## Phase 4: Expand Workflow Coverage

**Goal:** Add workflow docs as new use cases arise.

Candidates (in rough priority order based on user needs):
- [ ] `docs/workflows/materials.md` — shader setup, texture assignment, principled shader params
- [ ] `docs/workflows/cameras.md` — camera types, positioning strategies, DOF, motion blur
- [ ] `docs/workflows/animation.md` — keyframing, expressions, CHOPs
- [ ] `docs/workflows/simulation.md` — DOPs, pyro, FLIP, RBD basics
- [ ] `docs/workflows/usd.md` — LOPs/Solaris scene assembly
- [ ] `docs/workflows/pdg.md` — TOPs pipeline patterns
- [ ] `docs/workflows/hda.md` — digital asset creation patterns

Each follows the same template: step-by-step, parameter-specific, written for Claude.

## Phase 5: Feedback Loop

**Goal:** Improve workflow docs based on observed Claude behavior.

- [ ] When Claude makes mistakes despite having workflow docs, update the docs with explicit "do NOT" guidance
- [ ] Track which docs get read most (logging in bridge) to prioritize improvements
- [ ] User can flag bad Claude behavior → triggers doc update

## Open Questions

- Should workflow docs be readable by `search_docs` (BM25 indexed) or only via direct file path? Direct path is deterministic; BM25 is flexible but requires Claude to search.
- How verbose should workflow docs be? Terse checklists vs. explained rationale? Claude benefits from "why" but terse is faster to parse.
- Should the routing rules use `read the file` (via Read tool) or `search_docs` (via MCP tool)? The Read tool requires knowing the exact path; search_docs requires the BM25 index to include workflow docs.
