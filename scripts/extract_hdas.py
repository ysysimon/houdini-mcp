#!/usr/bin/env hython
"""
Extract HDA networks via hython — produces hda_parsed.json.

Must be run with hython (Houdini's Python interpreter), not regular Python.

Usage:
    hython scripts/extract_hdas.py                          # auto-detect $HFS
    hython scripts/extract_hdas.py --hfs-dir /opt/hfs21.0
    hython scripts/extract_hdas.py --output hda_parsed.json
    hython scripts/extract_hdas.py --extra-dir ~/my_hdas

The output JSON has the same shape as hip_parsed.json:
    [{"source", "nodes", "connections", "sticky_notes", "netboxes"}, ...]
"""

import argparse
import glob
import json
import os
import sys
import time


def _find_hdas(hfs_path, extra_dirs=None):
    """Find all .hda/.otl files under $HFS/houdini/help and extra dirs."""
    results = []
    search_dirs = [
        os.path.join(hfs_path, "houdini", "help"),
        os.path.join(hfs_path, "houdini", "otls"),
    ]
    for extra in extra_dirs or []:
        expanded = os.path.expanduser(extra)
        if os.path.isdir(expanded):
            search_dirs.append(expanded)

    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".hda", ".otl"):
                    results.append(os.path.join(root, fname))
    return results


# Map hou node category names to parent context paths for createNode
_CATEGORY_PARENTS = {
    "Object": "/obj",
    "Sop": None,       # needs geo container
    "Dop": None,       # needs dopnet container
    "Top": None,       # needs topnet container
    "Lop": "/stage",
    "Driver": "/out",
    "Cop2": "/img",
    "CopNet": "/img",
    "Chop": "/ch",
    "ChopNet": "/ch",
    "Shop": "/shop",
    "Vop": None,       # needs vop container
}


def _create_parent(hou, category_name):
    """Create an appropriate parent node for the given HDA category."""
    direct = _CATEGORY_PARENTS.get(category_name)
    if direct:
        return hou.node(direct)

    obj = hou.node("/obj")
    if category_name == "Sop":
        return obj.createNode("geo")
    if category_name == "Dop":
        return obj.createNode("dopnet")
    if category_name == "Top":
        return obj.createNode("topnet")
    if category_name == "Vop":
        geo = obj.createNode("geo")
        return geo.createNode("attribvop")

    # Fallback: try /obj
    return obj


def _extract_one(hou, hda_path):
    """Extract a single HDA file → list of result dicts (one per definition)."""
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hda.installFile(hda_path)
    defs = hou.hda.definitionsInFile(hda_path)

    results = []
    for defn in defs:
        cat_name = defn.nodeTypeCategory().name()
        parent = _create_parent(hou, cat_name)
        node = parent.createNode(defn.nodeTypeName())
        node.allowEditingOfContents()

        result = {
            "source": hda_path,
            "nodes": [],
            "connections": [],
            "sticky_notes": [],
            "netboxes": [],
        }

        # Walk all sub-children
        for child in node.allSubChildren():
            parms = {}
            for p in child.parms():
                try:
                    if not p.isAtDefault():
                        val = p.eval()
                        if isinstance(val, (int, float, str)):
                            parms[p.name()] = str(val)
                except Exception:
                    pass

            node_dict = {
                "type": child.type().name(),
                "path": child.path(),
                "name": child.name(),
                "category": child.type().category().name().upper(),
                "parameters": parms,
                "children": [c.path() for c in child.children()],
            }

            comment = child.comment()
            if comment:
                node_dict["comment"] = comment

            result["nodes"].append(node_dict)

            # Connections
            for conn in child.inputConnections():
                result["connections"].append({
                    "src_path": conn.inputNode().path(),
                    "src_output": conn.outputIndex(),
                    "dst_path": child.path(),
                    "dst_input": conn.inputIndex(),
                })

        # Sticky notes and network boxes at every level
        for container in [node] + list(node.allSubChildren()):
            try:
                for sn in container.stickyNotes():
                    text = sn.text().strip()
                    if text:
                        result["sticky_notes"].append({
                            "context": container.path(),
                            "name": sn.name(),
                            "text": text,
                        })
            except Exception:
                pass

            try:
                for nb in container.networkBoxes():
                    label = nb.comment()
                    if label:
                        result["netboxes"].append({
                            "context": container.path(),
                            "name": nb.name(),
                            "label": label,
                        })
            except Exception:
                pass

        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract HDA networks via hython")
    parser.add_argument("--hfs-dir", default=None, help="Explicit $HFS path")
    parser.add_argument("--extra-dir", action="append", default=[],
                        help="Additional directories to scan for HDAs")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: hda_parsed.json)")
    args = parser.parse_args()

    # Resolve $HFS
    hfs = args.hfs_dir or os.environ.get("HFS")
    if not hfs or not os.path.isdir(hfs):
        print("Error: Could not find Houdini installation.", file=sys.stderr)
        print("Use --hfs-dir or set $HFS.", file=sys.stderr)
        sys.exit(1)

    import hou

    hda_files = _find_hdas(hfs, extra_dirs=args.extra_dir)
    if not hda_files:
        print(f"No .hda/.otl files found under {hfs}")
        return

    print(f"Houdini install: {hfs}")
    print(f"Extracting {len(hda_files)} HDAs...\n")

    all_results = []
    total_nodes = 0
    total_stickies = 0
    total_comments = 0
    total_netboxes = 0
    errors = 0
    start = time.time()

    for i, hda_path in enumerate(hda_files, 1):
        basename = os.path.basename(hda_path)
        try:
            results = _extract_one(hou, hda_path)
            for r in results:
                n_nodes = len(r["nodes"])
                n_stickies = len(r["sticky_notes"])
                n_comments = sum(1 for n in r["nodes"] if "comment" in n)
                n_netboxes = len(r["netboxes"])
                total_nodes += n_nodes
                total_stickies += n_stickies
                total_comments += n_comments
                total_netboxes += n_netboxes
                all_results.append(r)
            print(f"  [{i}/{len(hda_files)}] {basename}: "
                  f"{sum(len(r['nodes']) for r in results)} nodes, "
                  f"{sum(len(r['sticky_notes']) for r in results)} stickies")
        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(hda_files)}] {basename}: ERROR — {e}")

    elapsed = time.time() - start

    # Write output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = args.output or os.path.join(repo_root, "hda_parsed.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Extracted:     {len(all_results)} HDA definitions ({errors} errors)")
    print(f"Total nodes:   {total_nodes}")
    print(f"Sticky notes:  {total_stickies}")
    print(f"Node comments: {total_comments}")
    print(f"Network boxes: {total_netboxes}")
    print(f"Time:          {elapsed:.1f}s")
    print(f"Output:        {output_path}")


if __name__ == "__main__":
    main()
