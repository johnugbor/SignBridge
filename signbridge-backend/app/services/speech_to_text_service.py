"""Wrapper around Cloud Speech-to-Text streaming recognition."""

from __future__ import annotations

import asyncio
from typing import Optional

from google.cloud import speech

from ..models.message_models import Speaker, TranscriptSegment


class SpeechToTextService:
	def __init__(self, language_code: str, sample_rate: int, logger) -> None:
		self.language_code = language_code
		self.sample_rate = sample_rate
		self._client = speech.SpeechClient()
		self._logger = logger

	async def transcribe(self, audio_bytes: bytes, language_code: Optional[str] = None) -> TranscriptSegment:
		if not audio_bytes:
			return TranscriptSegment(text="", is_final=False)

		config = speech.RecognitionConfig(
			encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
			language_code=language_code or self.language_code,
			sample_rate_hertz=self.sample_rate,
			enable_automatic_punctuation=True,
			model="latest_short",
		)
		audio = speech.RecognitionAudio(content=audio_bytes)

		response = await asyncio.to_thread(
			self._client.recognize,
			request={"config": config, "audio": audio},
		)

		if not response.results:
			self._logger.info("Transcription produced no results")
			return TranscriptSegment(text="", is_final=False)

		result = response.results[0]
		alternative = result.alternatives[0]
		segment = TranscriptSegment(
			text=alternative.transcript.strip(),
			confidence=alternative.confidence,
			is_final=True,
			speaker=Speaker.HEARING,
		)
		if not segment.text:
			self._logger.info("Transcription result was empty text")
			return TranscriptSegment(text="", is_final=False)
		self._logger.debug("Transcription complete", extra={"text": segment.text})
		return segment
