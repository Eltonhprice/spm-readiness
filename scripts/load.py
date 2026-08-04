# scripts/load.py
import json
import os
import re

_SIDECAR_PREFIX = "_sidecar_"


def load_all(input_dir):
    file_groups = {}
    for root, _, fnames in os.walk(input_dir):
        for fname in sorted(fnames):
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(root, fname)
            base = _base_name(fname)
            file_groups.setdefault(base, []).append(path)

    buckets = {}
    for base, paths in file_groups.items():
        paths.sort()
        if base.startswith(_SIDECAR_PREFIX):
            data = _parse_sidecar(_read(paths[0]))
            if data:
                buckets[base] = data
        else:
            records = []
            for path in paths:
                records.extend(_parse_records(_read(path)))
            if records:
                buckets[base] = records
    return buckets


def _base_name(fname):
    name = re.sub(r"\.\d{3}\.txt$", "", fname)
    name = re.sub(r"\.txt$", "", name)
    return name


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _strip_footer(text):
    lines = text.strip().splitlines()
    while lines and lines[-1].strip().startswith("//"):
        lines.pop()
    return "\n".join(lines).strip()


def _parse_records(text):
    clean = _strip_footer(text)
    if not clean or clean in ("[]", ""):
        return []
    try:
        data = json.loads(clean)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _parse_sidecar(text):
    clean = _strip_footer(text)
    if not clean or clean in ("{}", ""):
        return {}
    try:
        data = json.loads(clean)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
