# HoudiniMCP

Control **SideFX Houdini** from **Claude** using the **Model Context Protocol**.

- **45 MCP tools** — nodes, rendering, geometry, PDG/TOPs, USD/Solaris, HDAs, scene management
- **30,000+ searchable documents** — Houdini docs + patterns extracted from example files
- **Bidirectional event system** — Houdini pushes scene changes to Claude in real time

## Get Started

**Prerequisites:** git and Python 3.10+. Houdini is optional at setup time.

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/kleer001/houdini-mcp/main/bootstrap.sh | bash
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://raw.githubusercontent.com/kleer001/houdini-mcp/main/bootstrap.bat -OutFile bootstrap.bat; .\bootstrap.bat"
```

The bootstrap script clones the repo, installs [uv](https://docs.astral.sh/uv/), creates a venv, installs deps, sets up the Houdini plugin, optionally downloads offline docs, and configures your MCP client. Re-run from inside the repo at any time — it's idempotent. Full install is ~1 GB (mostly the documentation corpus).

<details>
<summary><strong>Manual setup (step by step)</strong></summary>

#### 1. Install the Houdini Plugin

```bash
# Auto-detect Houdini version and install
python scripts/install.py

# Or specify version explicitly
python scripts/install.py --houdini-version 20.5

# Preview without changing anything
python scripts/install.py --dry-run
```

This copies plugin files to your Houdini preferences directory and creates a packages JSON for auto-loading.

#### 2. Install MCP Dependencies

```bash
# Using uv (recommended)
cd /path/to/houdini-mcp
uv sync

# Or using pip
pip install "mcp[cli]"
```

#### 3. Configure Your MCP Client

**Claude Code (CLI):**
```bash
claude mcp add --transport stdio houdini -- uv --directory /path/to/houdini-mcp run python houdini_mcp_server.py
```

**Claude Desktop:** Go to **File > Settings > Developer > Edit Config** and add:

```json
{
  "mcpServers": {
    "houdini": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/houdini-mcp",
        "run",
        "python",
        "houdini_mcp_server.py"
      ]
    }
  }
}
```

**ChatGPT Desktop:** ChatGPT only supports remote (HTTP) MCP servers, not local stdio. You'll need to wrap the bridge in an HTTP transport and expose it via a tunnel:

```bash
# 1. Run the MCP server with HTTP transport (requires mcp[cli])
uv --directory /path/to/houdini-mcp run fastmcp run houdini_mcp_server.py --transport http --port 8080

# 2. Expose it with ngrok (or Cloudflare Tunnel, etc.)
ngrok http 8080
```

Then in ChatGPT: **Settings > Connectors > Create** — paste the ngrok HTTPS URL as the Connector URL.

**Ollama (local LLM):** Ollama doesn't have a built-in MCP client. Use [ollama-mcp-bridge](https://github.com/jonigl/ollama-mcp-bridge) to connect:

```bash
pip install ollama-mcp-bridge
```

Create `mcp-config.json`:

```json
{
  "mcpServers": {
    "houdini": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/houdini-mcp",
        "run",
        "python",
        "houdini_mcp_server.py"
      ]
    }
  }
}
```

```bash
ollama-mcp-bridge --config ./mcp-config.json
```

The bridge proxies Ollama's API and routes tool calls to HoudiniMCP automatically.

#### 4. Set Up Documentation Search

```bash
# Downloads Houdini docs and builds the BM25 index (~1 GB)
python scripts/fetch_houdini_docs.py
```

This enables the `search_docs` and `get_doc` tools — they work offline without a Houdini connection.

</details>

## What You Get

HoudiniMCP exposes 45 tools over MCP, organized by domain: scene management, node operations, code execution, materials, parameters, geometry, rendering, PDG/TOPs, USD/Solaris, HDA management, batch operations, events, and documentation search. The bridge runs as a separate process (`houdini_mcp_server.py`) and talks to the Houdini plugin over TCP.

```
Claude (MCP stdio) → houdini_mcp_server.py (Bridge) → TCP:9876 → server.py (Houdini Plugin) → hou API
                   ↘ houdini_rag.py (BM25 search — docs + patterns, local-only)
                   ↖ scripts/ingest_hips.py (pattern extraction from .hip files)
```

<details>
<summary><strong>All 45 MCP Tools</strong></summary>

### Scene Management
| Tool | Description |
|------|-------------|
| `ping` | Health check — verify Houdini is connected |
| `get_connection_status` | Connection info (port, command count, timing) |
| `get_scene_info` | Scene summary (file, frame, FPS, node counts) |
| `save_scene` | Save current scene, optionally to a new path |
| `load_scene` | Load a .hip file |
| `set_frame` | Set the playbar frame |

### Node Operations
| Tool | Description |
|------|-------------|
| `create_node` | Create a node (type, parent, name) |
| `modify_node` | Rename, reposition, or change parameters |
| `delete_node` | Delete a node by path |
| `get_node_info` | Inspect a node (type, parms, inputs, outputs) |
| `connect_nodes` | Wire src output → dst input |
| `disconnect_node_input` | Disconnect a specific input |
| `set_node_flags` | Set display/render/bypass flags |
| `set_node_color` | Set a node's color [r, g, b] |
| `layout_children` | Auto-layout child nodes |
| `find_error_nodes` | Scan hierarchy for cook errors |

### Code Execution
| Tool | Description |
|------|-------------|
| `execute_houdini_code` | Run Python code in Houdini (with safety guard) |

### Materials
| Tool | Description |
|------|-------------|
| `set_material` | Create or apply a material to an OBJ node |

### Parameters & Animation
| Tool | Description |
|------|-------------|
| `set_expression` | Set an HScript or Python expression on a parm |

### Geometry
| Tool | Description |
|------|-------------|
| `get_geo_summary` | Point/prim/vertex counts, bbox, attributes |
| `geo_export` | Export geometry (obj, gltf, glb, usd, ply, bgeo.sc) |

### Rendering
| Tool | Description |
|------|-------------|
| `render_single_view` | Render a single viewport (OpenGL/Karma/Mantra) |
| `render_quad_views` | Render 4 canonical views |
| `render_specific_camera` | Render from a specific camera node |
| `render_flipbook` | Render a flipbook sequence |
| `monitor_render` | Check if a Karma/Mantra render is still running |

### PDG/TOPs
| Tool | Description |
|------|-------------|
| `pdg_cook` | Start cooking a TOP network |
| `pdg_status` | Get cook status and work item counts |
| `pdg_workitems` | List work items (optionally by state) |
| `pdg_dirty` | Dirty work items for re-cooking |
| `pdg_cancel` | Cancel a running PDG cook |

### USD/Solaris (LOP)
| Tool | Description |
|------|-------------|
| `lop_stage_info` | USD stage summary (prims, layers, time) |
| `lop_prim_get` | Inspect a specific USD prim |
| `lop_prim_search` | Search prims by pattern and type |
| `lop_layer_info` | USD layer stack info |
| `lop_import` | Import USD via reference or sublayer |

### HDA Management
| Tool | Description |
|------|-------------|
| `hda_list` | List available HDA definitions |
| `hda_get` | Detailed info about an HDA |
| `hda_install` | Install an HDA file into the session |
| `hda_create` | Create an HDA from an existing node |

### Batch Operations
| Tool | Description |
|------|-------------|
| `batch` | Execute multiple operations atomically |

### Event System
| Tool | Description |
|------|-------------|
| `get_houdini_events` | Get pending Houdini events (scene/node/frame changes) |
| `subscribe_houdini_events` | Configure which event types to collect |

### Documentation Search (offline)
| Tool | Description |
|------|-------------|
| `search_docs` | BM25 search across 30,000+ documents (no Houdini needed) |
| `get_doc` | Read full content of a doc page |

</details>

## Shelf Tools

The installer adds a **HoudiniMCP** shelf with a **Toggle MCP Server** button that starts or stops the TCP server on localhost:9876.

<details>
<summary><strong>Ingest Pipeline</strong></summary>

The ingest pipeline extracts reusable patterns from Houdini's own example `.hip` files and HDA definitions, then indexes them alongside the documentation corpus for BM25 search.

```bash
# Run the full pipeline (discover → parse → extract HDAs → extract patterns → index)
python scripts/ingest_hips.py all

# Or run individual stages
python scripts/ingest_hips.py discover    # Find .hip files in Houdini install
python scripts/ingest_hips.py parse       # Parse .hip files (cpio format, no Houdini needed)
python scripts/ingest_hips.py extract-hdas # Extract HDA networks (requires hython)
python scripts/ingest_hips.py extract     # Extract patterns (scene graphs, subgraphs, recipes)
python scripts/ingest_hips.py index       # Build combined BM25 index (docs + patterns)
```

Pattern types extracted:
- **Scene graphs** — full node hierarchies from each .hip file
- **Subgraphs** — connected node clusters, deduplicated by topology
- **Recipes** — individual node configurations with parameter values

The combined index feeds the same `search_docs` and `get_doc` MCP tools used for documentation search.

</details>

<details>
<summary><strong>Documentation & Guides</strong></summary>

- [Getting Started](docs/GUIDE_GETTING_STARTED.md) — first-time setup walkthrough
- [Tools Reference](docs/GUIDE_TOOLS.md) — detailed tool documentation with examples
- [Events Guide](docs/GUIDE_EVENTS.md) — event system setup and usage
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common issues and fixes
- [.hip Format Reference](docs/hip_format.md) — cpio-based .hip file format internals

</details>

## Under the Hood

- **Zero external deps for search** — BM25 engine is pure stdlib Python, no numpy/scipy/nltk
- **Cpio parser for .hip files** — reads Houdini's binary scene format without Houdini installed
- **19,000+ patterns** extracted from Houdini's own example files, searchable alongside 11,000+ doc pages
- **Event deduplication** collapses rapid-fire callbacks (same type + path within 100ms)
- **Undo groups** wrap all mutating commands, dangerous code patterns blocked by default
- **227 tests**, all run without a Houdini instance

## Acknowledgements

HoudiniMCP builds on the work of several open-source projects:

- [blender-mcp](https://github.com/ahujasid/blender-mcp) by ahujasid — architectural inspiration (MCP bridge + TCP socket pattern)
- [capoomgit/houdini-mcp](https://github.com/capoomgit/houdini-mcp) by capoomgit — first full-featured Houdini MCP implementation
- [eetumartola/houdini-mcp](https://github.com/eetumartola/houdini-mcp) by eetumartola — early Houdini MCP implementation
- [Houdini21MCP](https://github.com/orrzxz/Houdini21MCP) by orrzxz — documentation search engine

## License

MIT
