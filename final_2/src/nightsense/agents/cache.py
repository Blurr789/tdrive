from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AgentCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.load().get(key)
        return value if isinstance(value, dict) else None

    def set(self, key: str, value: dict[str, Any]) -> None:
        data = self.load()
        data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

