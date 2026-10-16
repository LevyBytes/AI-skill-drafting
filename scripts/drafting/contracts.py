"""Validate bundled input schemas without remote references or provider dependencies."""
from pathlib import Path
from jsonschema import Draft202012Validator
from .storage import read_json, require


def validate(kind, value):
    schema = read_json(Path(__file__).resolve().parents[2] / "assets" / (kind + "-schema.json"))
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    require(not errors, "Invalid " + kind + " input: " + "; ".join(f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in errors[:5]))
