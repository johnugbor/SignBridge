"""Wrapper around Cloud Text-to-Speech for streaming audio responses."""

from __future__ import annotations

import asyncio
from typing import Optional

from google.cloud import texttospeech

from ..models.message_models import AudioPlaybackPayload
from ..utils import helpers


class TextToSpeechService:
	def __init__(
		self,
		language_code: str,
		voice_name: str,
		audio_encoding: str,
		sample_rate: int,
		logger,
	) -> None:
		self.language_code = language_code
		self.voice_name = voice_name
		self.audio_encoding = audio_encoding
		self.sample_rate = sample_rate
		self._client = texttospeech.TextToSpeechClient()
		self._logger = logger

	async def synthesize(self, session_id: str, text: str, emotion: Optional[str] = None) -> AudioPlaybackPayload:
		if not text:
			return AudioPlaybackPayload(
				session_id=session_id,
				audio_b64="",
				sample_rate=self.sample_rate,
			)

		synthesis_input = texttospeech.SynthesisInput(text=text)
		voice = texttospeech.VoiceSelectionParams(
			language_code=self.language_code,
			name=self.voice_name,
		)
		encoding_enum = getattr(
			texttospeech.AudioEncoding,
			self.audio_encoding,
			texttospeech.AudioEncoding.MP3,
		)
		audio_config = texttospeech.AudioConfig(
			audio_encoding=encoding_enum,
			speaking_rate=1.0,
			pitch=0.0,
		)

		response = await asyncio.to_thread(
			self._client.synthesize_speech,
			request={
				"input": synthesis_input,
				"voice": voice,
				"audio_config": audio_config,
			},
		)

		payload = AudioPlaybackPayload(
			session_id=session_id,
			audio_b64=helpers.b64encode(response.audio_content),
			sample_rate=self.sample_rate,
			mime_type="audio/mp3" if encoding_enum == texttospeech.AudioEncoding.MP3 else "audio/wav",
		)
		self._logger.debug("TTS synthesized", extra={"session_id": session_id, "emotion": emotion})
		return payload
