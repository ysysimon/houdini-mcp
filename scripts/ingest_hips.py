#!/usr/bin/env python3
"""
Houdini .hip ingest pipeline — discover, parse, and catalog.

Usage:
    python scripts/ingest_hips.py discover                     # list .hip files
    python scripts/ingest_hips.py parse                        # discover + parse all
    python scripts/ingest_hips.py parse --hfs-dir /opt/hfs21.0
    python scripts/ingest_hips.py parse --extra-dir ~/my_hips
    python scripts/ingest_hips.py parse --output results.json  # save to custom path
"""

import argparse
import glob
import json
import os
import platform
import sys
import time


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

HIP_EXTENSIONS = {".hip", ".hipnc"}
HDA_EXTENSIONS = {".hda", ".otl"}
ALL_EXTENSIONS = HIP_EXTENSIONS | HDA_EXTENSIONS


def find_houdini_install(hfs_dir=None):
    """Return the $HFS path (Houdini install root) or None.

    Priority: hfs_dir arg > $HFS env var > platform-specific glob.
    """
    if hfs_dir:
        if os.path.isdir(hfs_dir):
            return hfs_dir
        return None

    hfs_env = os.environ.get("HFS")
    if hfs_env and os.path.isdir(hfs_env):
        return hfs_env

    system = platform.system()
    if system == "Linux":
        candidates = sorted(glob.glob("/opt/hfs*"), reverse=True)
    elif system == "Darwin":
        candidates = sorted(glob.glob("/Applications/Houdini/Houdini*"), reverse=True)
    elif system == "Windows":
        candidates = sorted(
            glob.glob(r"C:\Program Files\Side Effects Software\Houdini *"),
            reverse=True,
        )
    else:
        candidates = []

    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def _walk_for_extensions(base_dir):
    """Walk base_dir recursively and yield matching files."""
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALL_EXTENSIONS:
                continue
            full_path = os.path.join(root, fname)
            rel_dir = os.path.relpath(root, base_dir)
            file_type = "hip" if ext in HIP_EXTENSIONS else "hda"
            yield {
                "path": full_path,
                "type": file_type,
                "size": os.path.getsize(full_path),
                "rel_dir": rel_dir,
            }


# Subdirectories of $HFS to search (in priority order).
# Houdini stores examples under houdini/help/, HDAs under houdini/otls/,
# demo scenes under packages/, and sample files under toolkit/ and engine/.
_HFS_SEARCH_SUBDIRS = [
    os.path.join("houdini", "help"),
    os.path.join("houdini", "otls"),
    "packages",
    "toolkit",
    "engine",
]


def discover_hip_files(hfs_path, extra_dirs=None):
    """Walk directories and catalog .hip/.hipnc/.hda/.otl files.

    Searches known $HFS subdirectories (houdini/help, houdini/otls, packages,
    toolkit, engine) plus any --extra-dir paths.

    Returns a list of dicts: {"path", "type", "size", "rel_dir"}.
    """
    results = []

    for subdir in _HFS_SEARCH_SUBDIRS:
        full = os.path.join(hfs_path, subdir)
        if os.path.isdir(full):
            results.extend(_walk_for_extensions(full))

    for extra in extra_dirs or []:
        expanded = os.path.expanduser(extra)
        if os.path.isdir(expanded):
            results.extend(_walk_for_extensions(expanded))

    return results


def print_summary(files, hfs_path):
    """Print a summary of discovered files."""
    hip_count = sum(1 for f in files if f["type"] == "hip")
    hda_count = sum(1 for f in files if f["type"] == "hda")
    total_size = sum(f["size"] for f in files)

    print(f"Houdini install: {hfs_path}")
    print(f"Files found: {len(files)} ({hip_count} hip, {hda_count} hda)")
    print(f"Total size:  {total_size / (1024 * 1024):.1f} MB")

    # Subdirectory breakdown
    dir_counts = {}
    for f in files:
        d = f["rel_dir"]
        dir_counts[d] = dir_counts.get(d, 0) + 1

    if dir_counts:
        print("\nBy directory:")
        for d in sorted(dir_counts):
            print(f"  {d}: {dir_counts[d]} files")


def _resolve_hfs(args):
    """Resolve $HFS from args or exit with error."""
    hfs_path = find_houdini_install(hfs_dir=args.hfs_dir)
    if not hfs_path:
        print("Error: Could not find Houdini installation.", file=sys.stderr)
        print("Use --hfs-dir to specify the $HFS path.", file=sys.stderr)
        sys.exit(1)
    return hfs_path


def cmd_discover(args):
    """Handle the 'discover' subcommand."""
    hfs_path = _resolve_hfs(args)
    files = discover_hip_files(hfs_path, extra_dirs=args.extra_dir)
    if not files:
        print(f"No .hip/.hda files found under {hfs_path}")
        return
    print_summary(files, hfs_path)


def cmd_parse(args):
    """Handle the 'parse' subcommand — discover + parse all .hip files."""
    sys.path.insert(0, REPO_ROOT)
    from hip_parser import parse_hip_file

    hfs_path = _resolve_hfs(args)
    all_files = discover_hip_files(hfs_path, extra_dirs=args.extra_dir)
    hip_files = [f for f in all_files if f["type"] == "hip"]

    if not hip_files:
        print(f"No .hip files found under {hfs_path}")
        return

    print(f"Houdini install: {hfs_path}")
    print(f"Parsing {len(hip_files)} .hip files...\n")

    results = []
    total_nodes = 0
    total_conns = 0
    errors = 0
    start = time.time()

    for i, entry in enumerate(hip_files, 1):
        filepath = entry["path"]
        basename = os.path.basename(filepath)
        try:
            result = parse_hip_file(filepath)
            n_nodes = len(result["nodes"])
            n_conns = len(result["connections"])
            total_nodes += n_nodes
            total_conns += n_conns
            results.append(result)
            print(f"  [{i}/{len(hip_files)}] {basename}: {n_nodes} nodes, {n_conns} connections")
        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(hip_files)}] {basename}: ERROR — {e}")

    elapsed = time.time() - start

    # Write results to JSON
    output_path = args.output or os.path.join(REPO_ROOT, "hip_parsed.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Parsed:      {len(results)} files ({errors} errors)")
    print(f"Total nodes: {total_nodes}")
    print(f"Total conns: {total_conns}")
    print(f"Time:        {elapsed:.1f}s")
    print(f"Output:      {output_path}")


def _add_common_args(parser):
    """Add --hfs-dir and --extra-dir to a subparser."""
    parser.add_argument("--hfs-dir", default=None, help="Explicit $HFS path")
    parser.add_argument("--extra-dir", action="append", default=[], help="Additional directories to scan")


def main():
    parser = argparse.ArgumentParser(description="Houdini .hip ingest pipeline")
    subparsers = parser.add_subparsers(dest="command")

    discover_parser = subparsers.add_parser("discover", help="Find Houdini install and list .hip files")
    _add_common_args(discover_parser)

    parse_parser = subparsers.add_parser("parse", help="Discover + parse all .hip files")
    _add_common_args(parse_parser)
    parse_parser.add_argument("--output", default=None, help="Output JSON path (default: hip_parsed.json)")

    args = parser.parse_args()
    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "parse":
        cmd_parse(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
