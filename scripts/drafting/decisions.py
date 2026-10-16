"""Require complete human/model dispositions, then independently check protected bytes."""
from collections import Counter
from pathlib import PurePosixPath
from .contracts import validate
from .markdown import protected
from .storage import require, relative


def check(before, after, decisions, evidence):
    validate("decisions", decisions)
    for path, data in before.items():
        if PurePosixPath(path).name.casefold().split(".")[0] in {"license", "licence", "copying", "notice"}:
            require(after.get(path) == data, "Existing license/notice must retain its path and exact bytes: " + path)
    require(decisions.get("schema_version") == 1, "Unknown decision schema")
    records = decisions["sources"]
    require(set(records) == set(before), "Every input needs exactly one disposition")
    covered, preserved = set(), []
    for path, record in records.items():
        kind = record["action"]
        require(kind in {"preserve", "rewrite", "exclude"}, "Unknown source action")
        require(bool(record.get("reason", "").strip()), "Disposition reason missing: " + path)
        outputs = record["outputs"]
        require(isinstance(outputs, list) and len(outputs) == len(set(outputs)), "Invalid output list")
        require(all(p in after for p in outputs), "Mapped output missing: " + path)
        covered.update(outputs)
        if kind == "preserve":
            require(len(outputs) == 1 and before[path] == after[outputs[0]], "Preserved bytes differ: " + path)
        elif kind == "exclude":
            require(not outputs, "Excluded source cannot map to output")
        else:
            require(bool(outputs), "Rewrite needs outputs")
            try:
                count = len(before[path].decode("utf-8").splitlines())
            except UnicodeDecodeError:
                raise ValueError("Binary rewrites require a separately reviewed preserved replacement")
            spans = record.get("reviewed_ranges", [])
            cursor = 1
            for start, end in spans:
                require(start == cursor and start <= end <= count, "Incomplete/overlapping source coverage: " + path)
                cursor = end + 1
            require(cursor == count + 1, "Unreviewed source lines: " + path)
            require(record.get("code") in {"preserve", "repair"}, "Explicit code policy needed")
            if record["code"] == "repair":
                sources = record.get("evidence", [])
                require(bool(sources) and all(relative(p) in evidence for p in sources), "Code repair needs captured evidence")
                require(bool(record.get("behavior_check", "").strip()), "Code repair needs behavior evidence or explicit not-run rationale")
            else:
                preserved.append((path, outputs))
    created = decisions.get("created", {})
    require(set(created) == set(after) - covered, "Every new output needs a reason; no stale creation records")
    require(all(isinstance(v, str) and v.strip() for v in created.values()), "Creation reason missing")
    # Connected mappings allow a complete example to move between split/merged files.
    while preserved:
        source, outputs = preserved.pop()
        sources, destinations = {source}, set(outputs)
        changed = True
        while changed:
            changed = False
            for item in preserved[:]:
                if destinations.intersection(item[1]):
                    sources.add(item[0]); destinations.update(item[1]); preserved.remove(item); changed = True
        old = Counter(piece for p in sources for piece in protected(p, before[p]))
        new = Counter(piece for p in destinations for piece in protected(p, after[p]))
        require(old == new, "Protected examples changed without repair evidence: " + str(sorted(sources)))
    reviews = decisions.get("reviews", {})
    require(all(isinstance(reviews.get(k), str) and reviews[k].strip() for k in ("organization", "source_fidelity", "behavior")), "Semantic review statements required")
    return {"input_files": len(before), "output_files": len(after), "reviewed_dispositions": len(records), "limits": "Range coverage and review statements are declarations; code preservation is independently compared."}
