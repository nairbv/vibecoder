"""Deterministic Client for tests.

Takes a list of "turn scripts": each script is a list of ClientMessage
objects to yield from a single `_run_turn` call. The base ask() loop
will execute any ToolCall yielded and re-enter `_run_turn`, advancing
through the scripts in order.
"""

from __future__ import annotations

from typing import AsyncIterator

from vibecoder.clients.base import BaseClient
from vibecoder.clients.messages import ClientMessage


class MockClient(BaseClient):
    def __init__(self, scripts: list[list[ClientMessage]] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._scripts: list[list[ClientMessage]] = scripts or []
        self._turn_index: int = 0

    async def _run_turn(self) -> AsyncIterator[ClientMessage]:
        if self._turn_index >= len(self._scripts):
            return
        script = self._scripts[self._turn_index]
        self._turn_index += 1
        for msg in script:
            yield msg
