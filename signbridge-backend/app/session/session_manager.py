"""Session manager that tracks per-conversation state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..utils.helpers import generate_session_id, utc_now
from .conversation_memory import ConversationMemory


@dataclass
class SessionState:
	session_id: str
	conversation_memory: ConversationMemory
	active_stream: Optional[str] = None
	last_activity: datetime = field(default_factory=utc_now)


class SessionManager:
	"""Creates and monitors live sessions with cleanup support."""

	def __init__(self, max_history: int, timeout_seconds: int, logger) -> None:
		self._max_history = max_history
		self._timeout = timedelta(seconds=timeout_seconds)
		self._sessions: Dict[str, SessionState] = {}
		self._lock = asyncio.Lock()
		self._logger = logger

	async def create_session(self, session_id: Optional[str] = None) -> SessionState:
		async with self._lock:
			new_id = session_id or generate_session_id()
			state = self._sessions.get(new_id)
			if state is not None:
				return state

			state = SessionState(
				session_id=new_id,
				conversation_memory=ConversationMemory(max_length=self._max_history),
			)
			self._sessions[new_id] = state
			self._logger.info("Session created", extra={"session_id": new_id})
			return state

	async def get_session(self, session_id: str) -> SessionState:
		async with self._lock:
			state = self._sessions.get(session_id)
			if state is not None:
				return state

		# Create outside the lock path used above to avoid nested lock acquisition.
		return await self.create_session(session_id=session_id)

	async def touch(self, session_id: str) -> None:
		async with self._lock:
			state = self._sessions.get(session_id)
			if state:
				state.last_activity = utc_now()

	async def end_session(self, session_id: str) -> None:
		async with self._lock:
			state = self._sessions.pop(session_id, None)
		if state:
			await state.conversation_memory.clear()
			self._logger.info("Session closed", extra={"session_id": session_id})

	async def cleanup_expired(self) -> None:
		now = utc_now()
		expired = []
		async with self._lock:
			for session_id, state in list(self._sessions.items()):
				if now - state.last_activity > self._timeout:
					expired.append(session_id)
					self._sessions.pop(session_id, None)
		for session_id in expired:
			self._logger.info("Session expired", extra={"session_id": session_id})
