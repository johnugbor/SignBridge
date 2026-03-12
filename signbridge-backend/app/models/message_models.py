"""Message models shared by the WebSocket API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class Speaker(str, Enum):
	"""Supported conversation speakers."""

	HEARING = "hearing"
	DEAF = "deaf"
	SYSTEM = "system"


class TranscriptSegment(BaseModel):
	"""Represents Cloud Speech-to-Text transcript segments."""

	text: str
	confidence: Optional[float] = None
	is_final: bool = True
	speaker: Speaker = Speaker.HEARING


class AudioChunk(BaseModel):
	"""Audio chunk sent by the browser over WebSocket."""

	session_id: str = ""
	sequence_id: int = Field(ge=0)
	audio_b64: str
	sample_rate: int
	language_code: Optional[str] = None
	is_final: bool = False


class RadioAudioChunk(BaseModel):
	"""Ambient audio chunk sent by Radio Mode for sessionless interpretation."""

	sequence_id: int = Field(ge=0)
	audio_b64: str
	sample_rate: int
	energy_rms: Optional[float] = Field(default=None, ge=0)
	is_final: bool = False


class VideoFrame(BaseModel):
	"""Video frame payload originating from the deaf user."""

	session_id: str = ""
	frame_id: int = Field(ge=0)
	data_b64: str
	mime_type: str = "image/jpeg"
	is_final: bool = False


class ControlCommand(BaseModel):
	"""Control actions sent by the frontend (interruptions, session end, etc)."""

	action: Literal["start_session", "end_session", "interrupt", "ping"]
	target: Optional[Literal["tts", "avatar", "all"]] = None


class WebSocketInboundMessage(BaseModel):
	"""Generic inbound message envelope with explicit type checking."""

	type: Literal[
		"start_session",
		"audio_chunk",
		"radio_audio_chunk",
		"video_frame",
		"control",
		"ping",
	]
	payload: Dict[str, Any] = Field(default_factory=dict)

	def to_audio_chunk(self) -> AudioChunk:
		return AudioChunk(**self.payload)

	def to_radio_audio_chunk(self) -> RadioAudioChunk:
		return RadioAudioChunk(**self.payload)

	def to_video_frame(self) -> VideoFrame:
		return VideoFrame(**self.payload)

	def to_command(self) -> ControlCommand:
		return ControlCommand(**self.payload)


class SessionAck(BaseModel):
	"""Acknowledgement payload sent once a session is ready."""

	session_id: str
	active: bool = True


class TranscriptMessage(BaseModel):
	"""Transcript updates streaming back to the client."""

	session_id: str
	segment: TranscriptSegment


class RadioTranscriptPayload(BaseModel):
	"""Ambient audio interpretation payload returned to Radio Mode clients."""

	text: str
	category: Literal["speech", "music", "noise", "silence", "unclear"] = "unclear"
	is_final: bool = True


class ErrorMessage(BaseModel):
	"""Represents recoverable errors that should be surfaced to the UI."""

	code: str
	detail: str


class AudioPlaybackPayload(BaseModel):
	"""TTS playback payload delivered to the hearing user."""

	session_id: str
	audio_b64: str
	sample_rate: int
	mime_type: str = "audio/mp3"


class WebSocketOutboundMessage(BaseModel):
	"""Generic outbound envelope used by the websocket endpoint."""

	type: Literal[
		"session_ack",
		"transcript",
		"radio_transcript",
		"animation",
		"audio",
		"control",
		"error",
		"pong",
	]
	payload: Dict[str, Any]
