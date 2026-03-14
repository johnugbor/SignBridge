"""Core orchestration agent using ADK-backed Gemini services."""

from __future__ import annotations

from typing import Dict, List

from ..models.message_models import (
	AudioChunk,
	ControlCommand,
	RadioAudioChunk,
	RadioTranscriptPayload,
	Speaker,
	TranscriptMessage,
	TranscriptSegment,
	VideoFrame,
	WebSocketOutboundMessage,
)
from ..services.gemini_live_service import GeminiLiveService
from ..services.sign_animation_service import SignAnimationService
from ..services.speech_to_text_service import SpeechToTextService
from ..services.text_to_speech_service import TextToSpeechService
from ..session.session_manager import SessionManager
from ..streaming.audio_stream_handler import AudioStreamHandler
from ..streaming.video_stream_handler import VideoStreamHandler


class SignConversationAgent:
	"""Coordinates speech, sign, Gemini, and TTS services."""

	def __init__(
		self,
		speech_service: SpeechToTextService,
		gemini_service: GeminiLiveService,
		tts_service: TextToSpeechService,
		animation_service: SignAnimationService,
		session_manager: SessionManager,
		sample_rate: int,
		video_buffer: int,
		logger,
	) -> None:
		self.speech_service = speech_service
		self.gemini_service = gemini_service
		self.tts_service = tts_service
		self.animation_service = animation_service
		self.session_manager = session_manager
		self.sample_rate = sample_rate
		self.video_buffer = video_buffer
		self._logger = logger
		self._audio_handlers: Dict[str, AudioStreamHandler] = {}
		self._video_handlers: Dict[str, VideoStreamHandler] = {}
		self._radio_audio_handlers: Dict[str, AudioStreamHandler] = {}
		self._last_radio_output: Dict[str, str] = {}

	async def handle_audio_chunk(self, chunk: AudioChunk) -> List[WebSocketOutboundMessage]:
		handler = self._audio_handlers.setdefault(
			chunk.session_id, AudioStreamHandler(sample_rate=self.sample_rate)
		)
		audio_buffer = handler.add_chunk(chunk)
		if audio_buffer is None:
			return []

		session = await self.session_manager.get_session(chunk.session_id)
		transcript = await self.speech_service.transcribe(audio_buffer, chunk.language_code)
		await self.session_manager.touch(chunk.session_id)

		responses: List[WebSocketOutboundMessage] = []
		transcript_payload = TranscriptMessage(session_id=chunk.session_id, segment=transcript)
		responses.append(
			WebSocketOutboundMessage(type="transcript", payload=transcript_payload.model_dump())
		)

		if transcript.text:
			await session.conversation_memory.add(Speaker.HEARING, transcript.text)
			memory_prompt = await session.conversation_memory.as_prompt()
			gloss_plan = await self.gemini_service.generate_gloss(transcript.text, memory_prompt)
			animation_plan = await self.animation_service.build_plan(chunk.session_id, gloss_plan)
			responses.append(
				WebSocketOutboundMessage(type="animation", payload=animation_plan.model_dump())
			)
		return responses

	async def handle_radio_audio_chunk(
		self,
		socket_session_id: str,
		chunk: RadioAudioChunk,
	) -> List[WebSocketOutboundMessage]:
		if chunk.sequence_id == 0:
			self._last_radio_output.pop(socket_session_id, None)
			existing_handler = self._radio_audio_handlers.get(socket_session_id)
			if existing_handler:
				existing_handler.reset()

		handler = self._radio_audio_handlers.setdefault(
			socket_session_id,
			AudioStreamHandler(sample_rate=chunk.sample_rate, chunk_duration_ms=1500),
		)
		audio_buffer = handler.add_chunk(
			AudioChunk(
				session_id=socket_session_id,
				sequence_id=chunk.sequence_id,
				audio_b64=chunk.audio_b64,
				sample_rate=chunk.sample_rate,
				is_final=chunk.is_final,
			)
		)
		if audio_buffer is None:
			return []

		transcript = await self.speech_service.transcribe(audio_buffer)
		ambient = await self.gemini_service.interpret_ambient_audio(
			transcript_text=transcript.text,
			energy_rms=chunk.energy_rms,
		)

		category = ambient.get("category", "unclear")
		text = ambient.get("text", "").strip()

		if not transcript.text:
			if chunk.energy_rms is not None and chunk.energy_rms < 0.004:
				category = "silence"
				text = "No clear sound detected."
			elif not text:
				category = "music"
				text = "Background audio detected (possibly music), but no clear speech yet."

		last_text = self._last_radio_output.get(socket_session_id)
		if text and text == last_text and not chunk.is_final:
			return []

		if text:
			self._last_radio_output[socket_session_id] = text

		payload = RadioTranscriptPayload(
			text=text,
			category=category if category in {"speech", "music", "noise", "silence", "unclear"} else "unclear",
			is_final=chunk.is_final,
		)
		return [WebSocketOutboundMessage(type="radio_transcript", payload=payload.model_dump())]

	async def handle_video_frame(self, frame: VideoFrame) -> List[WebSocketOutboundMessage]:
		handler = self._video_handlers.setdefault(
			frame.session_id, VideoStreamHandler(max_buffer=self.video_buffer)
		)
		frames = handler.add_frame(frame)
		if frames is None:
			return []

		session = await self.session_manager.get_session(frame.session_id)
		memory_prompt = await session.conversation_memory.as_prompt()
		interpretation = await self.gemini_service.interpret_sign_frames(frames, memory_prompt)
		if interpretation:
			await session.conversation_memory.add(Speaker.DEAF, interpretation)
		await self.session_manager.touch(frame.session_id)

		transcript_segment = TranscriptSegment(
			text=interpretation,
			confidence=None,
			is_final=True,
			speaker=Speaker.DEAF,
		)
		transcript_payload = TranscriptMessage(
			session_id=frame.session_id,
			segment=transcript_segment,
		)
		audio_payload = await self.tts_service.synthesize(
			session_id=frame.session_id,
			text=interpretation,
		)

		return [
			WebSocketOutboundMessage(type="transcript", payload=transcript_payload.model_dump()),
			WebSocketOutboundMessage(type="audio", payload=audio_payload.model_dump()),
		]

	async def handle_control(self, session_id: str, command: ControlCommand) -> WebSocketOutboundMessage:
		if command.action == "interrupt":
			await self._handle_interrupt(session_id)
		elif command.action == "end_session":
			await self.session_manager.end_session(session_id)
			self._audio_handlers.pop(session_id, None)
			self._video_handlers.pop(session_id, None)
			self._radio_audio_handlers.pop(session_id, None)
			self._last_radio_output.pop(session_id, None)
		else:
			self._logger.warning(
				"Unsupported control action", extra={"action": command.action}
			)

		return WebSocketOutboundMessage(type="control", payload=command.model_dump())

	async def _handle_interrupt(self, session_id: str) -> None:
		handler = self._audio_handlers.get(session_id)
		if handler:
			handler.reset()
		video_handler = self._video_handlers.get(session_id)
		if video_handler:
			video_handler.reset()
		radio_handler = self._radio_audio_handlers.get(session_id)
		if radio_handler:
			radio_handler.reset()
		self._last_radio_output.pop(session_id, None)
		session = await self.session_manager.get_session(session_id)
		await session.conversation_memory.clear()
		self._logger.info("Stream interrupted", extra={"session_id": session_id})
