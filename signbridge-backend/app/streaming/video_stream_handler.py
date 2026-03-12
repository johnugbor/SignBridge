"""Video frame buffering for Gemini sign interpretation."""

from __future__ import annotations

from typing import List, Optional

from ..models.message_models import VideoFrame


class VideoStreamHandler:
	"""Collects a sliding window of frames before delegating to Gemini."""

	def __init__(self, max_buffer: int = 10) -> None:
		self.max_buffer = max_buffer
		self._frames: List[str] = []

	def add_frame(self, frame: VideoFrame) -> Optional[List[str]]:
		self._frames.append(frame.data_b64)
		if frame.is_final or len(self._frames) >= self.max_buffer:
			return self.flush()
		return None

	def flush(self) -> Optional[List[str]]:
		if not self._frames:
			return None
		buffer = list(self._frames)
		self._frames.clear()
		return buffer

	def reset(self) -> None:
		self._frames.clear()
