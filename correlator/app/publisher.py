from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Protocol

from .models import EnrichedIncident


class Publisher(Protocol):
    async def publish(self, event: EnrichedIncident) -> None:
        ...


class StdoutPublisher:
    async def publish(self, event: EnrichedIncident) -> None:
        print(json.dumps(event.model_dump(mode="json"), ensure_ascii=True))


class JsonlFilePublisher:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def publish(self, event: EnrichedIncident) -> None:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=True)
        await asyncio.to_thread(self._append_line, payload)

    def _append_line(self, payload: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(payload + "\n")


class NoopPublisher:
    async def publish(self, event: EnrichedIncident) -> None:
        _ = event
