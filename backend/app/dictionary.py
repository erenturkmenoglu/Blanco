"""Veri sözlüğü yükleyici — docs/data_dictionary.yaml tek kaynaktır."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "docs" / "data_dictionary.yaml",   # repo düzeni
    Path(__file__).resolve().parents[1] / "docs" / "data_dictionary.yaml",   # docker imajı (backend/docs)
]


@lru_cache(maxsize=1)
def load() -> dict:
    for p in _CANDIDATES:
        if p.exists():
            with p.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh)
    raise FileNotFoundError("data_dictionary.yaml bulunamadı")


def metric_index() -> dict[str, dict]:
    d = load()
    out = {m["code"]: m for m in d["metrics"]}
    for m in d["derived"]:
        out.setdefault(m["code"], {**m, "kind": "derived"})
    return out


def metric_codes() -> set[str]:
    return set(metric_index())


def is_cumulative_flow(code: str) -> bool:
    m = metric_index().get(code, {})
    return bool(m.get("cumulative_ytd"))
