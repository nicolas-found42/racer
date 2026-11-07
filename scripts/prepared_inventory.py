"""Bounded preparation metadata shared by registration, publication and review.

Reading this format does not certify source evidence or grant player eligibility.
Callers retain their existing source/role policy and bounded selection rules.
"""
import json
import math

from install_cars import require

MAX_BYTES = 16 * 1024**2
MAX_RECORDS = 3000


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result

    def number(value):
        result = float(value)
        require(math.isfinite(result), 'nonfinite_json')
        return result

    def constant(value):
        raise ValueError('nonfinite_json')

    return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                      parse_constant=constant)


def validate(document, *, require_schema=False):
    require(isinstance(document, dict), 'inventory_schema')
    # Legacy publisher/capture fixtures and inputs omitted schema. Retain that
    # shape; explicit versions must be known, and registration still requires1.
    if require_schema or 'schema' in document:
        require(type(document.get('schema')) is int and document['schema'] == 1,
                'inventory_schema')
    rows = document.get('vehicles')
    require(isinstance(rows, list) and len(rows) <= MAX_RECORDS,
            'inventory_count')
    identities = set()
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('model_id'), str)
                and 0 < len(row['model_id']) <= 256, 'inventory_row')
        require(row['model_id'] not in identities, 'duplicate_inventory_model')
        identities.add(row['model_id'])
    return document


def decode(raw, *, require_schema=False):
    require(len(raw) <= MAX_BYTES, 'inventory_byte_budget')
    return validate(strict_json(raw), require_schema=require_schema)


def encode(document):
    validate(document, require_schema=True)
    chunks = []
    size = 1  # Final newline is part of the byte budget.
    encoder = json.JSONEncoder(indent=2, ensure_ascii=True, allow_nan=False)
    for chunk in encoder.iterencode(document):
        part = chunk.encode()
        size += len(part)
        require(size <= MAX_BYTES, 'result_inventory_budget')
        chunks.append(part)
    return b''.join(chunks) + b'\n'
