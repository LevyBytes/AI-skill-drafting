"""Detect repeated directory concepts without stemming arbitrary prefixes."""
import re

# English inflections, not an assertion about every natural language or API name.
IRREGULAR = {
    "analysis": "analyses", "axis": "axes", "basis": "bases", "child": "children",
    "criterion": "criteria", "crisis": "crises", "datum": "data", "diagnosis": "diagnoses",
    "foot": "feet", "goose": "geese", "index": "indices", "leaf": "leaves",
    "life": "lives", "man": "men", "matrix": "matrices", "medium": "media",
    "mouse": "mice", "person": "people", "phenomenon": "phenomena", "schema": "schemata",
    "thesis": "theses", "tooth": "teeth", "vertex": "vertices", "woman": "women",
}
SHORT_PLURALS = {"id": "ids", "ip": "ips"}
NOT_REGULAR_PLURALS = {
    "news", "series", "species", "means", "physics", "mathematics", "status",
    "analysis", "axis", "basis", "crisis", "thesis", "diagnosis", "canvas", "alias",
    "atlas", "bias", "gas", "virus", "bonus", "corpus", "genus", "focus", "census", "apparatus",
}


def singular_plural(singular, plural):
    if IRREGULAR.get(singular) == plural or SHORT_PLURALS.get(singular) == plural:
        return True
    if len(singular) < 3 or not singular.isalpha() or not plural.isalpha():
        return False
    if plural in NOT_REGULAR_PLURALS:
        return False
    if singular in IRREGULAR and singular not in {"index", "matrix", "medium", "person", "schema"}:
        return False
    if singular.endswith("y") and singular[-2] not in "aeiou":
        return plural == singular[:-1] + "ies"
    if singular.endswith(("s", "x", "z", "ch", "sh")):
        return plural == singular + "es"
    return plural == singular + "s"


def equivalent(left, right):
    """Compare complete names; qualifiers and separators must also agree."""
    first = re.split(r"([-_])", left.casefold())
    second = re.split(r"([-_])", right.casefold())
    return len(first) == len(second) and all(
        a == b or singular_plural(a, b) or singular_plural(b, a)
        for a, b in zip(first, second))


def repeated_ancestors(parts):
    """Report each matching ancestor of this directory, adjacent or separated."""
    if len(parts) < 2:
        return []
    leaf = parts[-1]
    return [{"ancestor": "/".join(parts[:index + 1]),
             "relationship": "exact" if name.casefold() == leaf.casefold() else "singular_plural"}
            for index, name in enumerate(parts[:-1]) if equivalent(name, leaf)]
