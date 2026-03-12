"""Audio buffering utilities for the WebSocket stream."""

from __future__ import annotations

from typing import Optional

from ..models.message_models import AudioChunk
from ..utils.helpers import b64decode


class AudioStreamHandler:
	"""Buffers audio chunks until there is enough data for transcription."""

	def __init__(self, sample_rate: int, chunk_duration_ms: int = 1200) -> None:
		self.sample_rate = sample_rate
		self.chunk_duration_ms = chunk_duration_ms
		self._buffer = bytearray()
		self._last_sequence = -1

	def add_chunk(self, chunk: AudioChunk) -> Optional[bytes]:
		data = b64decode(chunk.audio_b64)
		self._buffer.extend(data)
		self._last_sequence = chunk.sequence_id
		if chunk.is_final or self._buffer_duration_ms() >= self.chunk_duration_ms:
			return self.flush()
		return None

	def flush(self) -> Optional[bytes]:
		if not self._buffer:
			return None
		payload = bytes(self._buffer)
		self._buffer.clear()
		return payload

	def reset(self) -> None:
		self._buffer.clear()

	def _buffer_duration_ms(self) -> float:
		if not self.sample_rate:
			return 0
		# Assuming LINEAR16 encoding (2 bytes per sample)
		samples = len(self._buffer) / 2
		return (samples / self.sample_rate) * 1000
