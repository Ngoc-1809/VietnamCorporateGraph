"""JSONL (de)serialization for Pydantic models."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_jsonl(path: str | Path, items: Iterable[BaseModel]) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
            n += 1
    return n


def read_jsonl(path: str | Path, model: type[T]) -> list[T]:
    out: list[T] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(model.model_validate_json(line))
    return out
