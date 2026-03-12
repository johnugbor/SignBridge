"""Conversation memory buffer used to supply Gemini with context."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque, List

from ..models.message_models import Speaker


@dataclass
class MemoryEntry:
	speaker: Speaker
	text: str


class ConversationMemory:
	"""Keeps the last N conversation entries for prompt priming."""

	def __init__(self, max_length: int = 5) -> None:
		self._buffer: Deque[MemoryEntry] = deque(maxlen=max_length)
		self._lock = asyncio.Lock()

	async def add(self, speaker: Speaker, text: str) -> None:
		async with self._lock:
			self._buffer.append(MemoryEntry(speaker=speaker, text=text))

	async def clear(self) -> None:
		async with self._lock:
			self._buffer.clear()

	async def snapshot(self) -> List[MemoryEntry]:
		async with self._lock:
			return list(self._buffer)

	async def as_prompt(self) -> str:
		"""Return a formatted prompt describing the recent conversation."""

		entries = await self.snapshot()
		lines = [f"{entry.speaker.value.upper()}: {entry.text}" for entry in entries]
		return "\n".join(lines)
