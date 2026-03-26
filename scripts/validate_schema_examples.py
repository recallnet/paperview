#!/usr/bin/env python3

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SchemaValidationError(Exception):
    pass


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(schema, value, path="$"):
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(value, dict):
            raise SchemaValidationError(f"{path}: expected object")

        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise SchemaValidationError(f"{path}: missing required key '{key}'")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise SchemaValidationError(
                    f"{path}: unexpected keys {', '.join(extras)}"
                )

        for key, child_schema in properties.items():
            if key in value:
                validate(child_schema, value[key], f"{path}.{key}")
        return

    if schema_type == "array":
        if not isinstance(value, list):
            raise SchemaValidationError(f"{path}: expected array")

        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise SchemaValidationError(
                f"{path}: expected at least {min_items} items, got {len(value)}"
            )

        if schema.get("uniqueItems"):
            seen = []
            for item in value:
                if item in seen:
                    raise SchemaValidationError(f"{path}: duplicate item '{item}'")
                seen.append(item)

        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate(item_schema, item, f"{path}[{index}]")
        return

    if schema_type == "string":
        if not isinstance(value, str):
            raise SchemaValidationError(f"{path}: expected string")

        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise SchemaValidationError(
                f"{path}: expected minimum length {min_length}, got {len(value)}"
            )

        allowed = schema.get("enum")
        if allowed is not None and value not in allowed:
            raise SchemaValidationError(f"{path}: invalid enum value '{value}'")
        return

    raise SchemaValidationError(f"{path}: unsupported schema type '{schema_type}'")


def validate_vocab_against_schema(vocab, schema, path="$"):
    if schema.get("type") != "object":
        return

    for key, property_schema in schema.get("properties", {}).items():
        if key not in vocab:
            continue

        if property_schema.get("type") == "string" and "enum" in property_schema:
            expected = property_schema["enum"]
            actual = vocab[key]
            if actual != expected:
                raise SchemaValidationError(
                    f"{path}.{key}: vocab does not match schema enum"
                )

        if property_schema.get("type") == "array":
            item_schema = property_schema.get("items", {})
            if item_schema.get("type") == "string" and "enum" in item_schema:
                expected = item_schema["enum"]
                actual = vocab[key]
                if actual != expected:
                    raise SchemaValidationError(
                        f"{path}.{key}: vocab does not match schema enum"
                    )


def main():
    extraction_schema = load_json(ROOT / "schemas" / "extraction.schema.json")
    fingerprint_schema = load_json(ROOT / "schemas" / "fingerprint.schema.json")
    vocab = load_json(ROOT / "schemas" / "normalization_vocab.json")
    extraction_example = load_json(
      ROOT / "schemas" / "examples" / "extraction.example.json"
    )
    fingerprint_example = load_json(
      ROOT / "schemas" / "examples" / "fingerprint.example.json"
    )

    validate(extraction_schema, extraction_example)
    validate(fingerprint_schema, fingerprint_example)
    validate_vocab_against_schema(vocab, extraction_schema, path="extraction")
    validate_vocab_against_schema(vocab, fingerprint_schema, path="fingerprint")

    print("schema examples valid")


if __name__ == "__main__":
    main()
