"""Portable commands; examples are inspected, never implicitly executed."""
import argparse
import json
from pathlib import Path
from . import markdown
from .preparation import load, prepare
from .render import render_to
from .storage import read_json, safe_root, tree
from .transactions import apply, deploy, rollback
from .validation import verify


def parser():
    root = argparse.ArgumentParser(description="Prepare and verify reviewed skill proposals; apply to a stage before authorized deployment.")
    commands = root.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Read Markdown blocks, code and source coordinates")
    inspect.add_argument("--input", type=Path, required=True)
    render = commands.add_parser("render", help="Render model-authored complete topics to a new proposal folder")
    render.add_argument("--spec", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify", help="Verify the selected owner format without changing files")
    check.add_argument("--input", type=Path, required=True)
    check.add_argument("--roots", nargs="+", default=["."], help="Explicit main/product roots, relative to input")
    prep = commands.add_parser("prepare", help="Freeze complete decisions, tasks, evidence and diffs")
    for name in ("input", "proposal", "work", "requirements", "decisions"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--evidence", type=Path)
    for verb in ("status", "apply", "deploy", "rollback"):
        sub = commands.add_parser(verb)
        sub.add_argument("--work", type=Path, required=True)
        if verb in {"deploy", "rollback"}:
            sub.add_argument("--authorization", required=True, help="Record the actual caller/owner decision; this is not authentication")
        if verb == "deploy":
            sub.add_argument("--destination", type=Path, required=True)
            sub.add_argument("--approved-digest", required=True)
    return root


def run(args):
    if args.command == "inspect":
        return {p: markdown.inspect(b.decode("utf-8")) for p, b in tree(args.input).items() if p.endswith(".md")}
    if args.command == "render":
        return render_to(read_json(args.spec), args.output)
    if args.command == "verify":
        return verify(safe_root(args.input), args.roots)
    if args.command == "prepare":
        return prepare(args.input, args.proposal, args.work, args.requirements, args.decisions, args.evidence)
    if args.command == "status":
        manifest = load(args.work)
        return {"manifest_verified": True, "tasks": len(manifest["tasks"]), "checkpoint": read_json(args.work / "checkpoint.json"), "resume": "Read REQUIREMENTS.md and the source decisions before continuing; no compaction hook is installed."}
    if args.command == "apply":
        return apply(args.work)
    if args.command == "deploy":
        return deploy(args.work, args.destination, args.approved_digest, args.authorization)
    return rollback(args.work, args.authorization)


def main():
    args = parser().parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed", True) else 1
