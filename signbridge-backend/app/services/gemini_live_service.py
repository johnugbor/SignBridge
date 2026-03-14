"""Interaction layer with Gemini powered by Google ADK agents."""

from __future__ import annotations

import asyncio
import base64
import binascii
import inspect
import json
import os
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from google.adk.runners import Runner
from google.genai import types as genai_types

try:  # ADK API path compatibility across versions.
	from google.adk.agents import LlmAgent
except ImportError:  # pragma: no cover - compatibility fallback
	from google.adk.agents.llm_agent import LlmAgent

try:  # ADK API path compatibility across versions.
	from google.adk.sessions import InMemorySessionService
except ImportError:  # pragma: no cover - compatibility fallback
	from google.adk.sessions.in_memory_session_service import InMemorySessionService

from ..models.animation_models import GlossPlan
from ..utils.helpers import safe_json_loads


class GeminiLiveService:
	def __init__(
		self,
		project_id: str,
		region: str,
		model_name: str,
		fallback_model_names: Sequence[str],
		temperature: float,
		logger,
	) -> None:
		# ADK uses python-genai credentials/environment under the hood.
		os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
		os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
		os.environ.setdefault("GOOGLE_CLOUD_LOCATION", region)

		self._logger = logger
		self._model_candidates = self._build_model_candidates(model_name, fallback_model_names)
		self._model_index = 0
		self._model_switch_lock = asyncio.Lock()
		self._temperature = temperature
		self._session_service = InMemorySessionService()
		self._adk_user_id = "signbridge-backend"
		self._adk_app_name_prefix = "signbridge"
		self._gloss_app_name = f"{self._adk_app_name_prefix}-gloss"
		self._sign_app_name = f"{self._adk_app_name_prefix}-sign"
		self._ambient_app_name = f"{self._adk_app_name_prefix}-ambient"

		self._logger.info(
			"Gemini service initialized",
			extra={
				"model": self._model_candidates[self._model_index],
				"engine": "google-adk",
			},
		)
		self._translation_prompt_template = self._load_prompt_template(
			"sign_translation_prompt.txt",
			(
				"You are helping a deaf-hearing conversation. Convert the sentence into "
				"ASL gloss optimized for avatar animation. Return JSON with keys: "
				"gloss (array), facial (string), emotion (string).\n"
				"Context:\n{{MEMORY_CONTEXT}}\nSentence:\n{{TRANSCRIPT}}"
			),
		)
		self._interpretation_prompt_template = self._load_prompt_template(
			"sign_interpretation_prompt.txt",
			(
				"Interpret the provided ASL frame sequence and return strict JSON with keys: "
				"has_signing (boolean) and text (string).\n"
				"Context:\n{{MEMORY_CONTEXT}}\nFrames:\n{{FRAME_DESCRIPTIONS}}"
			),
		)
		self._ambient_prompt_template = (
			"You are interpreting ambient audio for a deaf user. Return strict JSON with keys: "
			"category (speech|music|noise|silence|unclear) and text (string).\n"
			"Rules:\n"
			"- If transcript is clear speech, category='speech' and text should be concise and natural.\n"
			"- If transcript is empty and energy is very low, category='silence' and text='No clear sound detected.'\n"
			"- If transcript is empty but energy is present, prefer category='music' or 'noise' and mention that no clear speech is detected.\n"
			"- Never invent specific spoken sentences when transcript is empty.\n"
			"Transcript candidate: {{TRANSCRIPT}}\n"
			"Energy RMS: {{ENERGY_RMS}}"
		)
		self._configure_adk_agents()

	async def generate_gloss(self, transcript: str, memory_prompt: str) -> GlossPlan:
		if not transcript:
			return GlossPlan(gloss=[], facial="neutral", emotion="neutral")
		prompt = self._build_gloss_prompt(transcript, memory_prompt)
		response_text = await self._run_with_fallback(kind="gloss", prompt=prompt)
		return self._parse_gloss_response(response_text)

	async def interpret_sign_frames(self, frames_b64: Sequence[str], memory_prompt: str) -> str:
		if not frames_b64:
			return ""
		selected_frames = self._select_sign_frames(frames_b64)
		frame_descriptions = "\n".join(
			f"Frame {idx}: [image/jpeg bytes provided]" for idx, _frame in enumerate(selected_frames)
		)
		prompt = self._build_video_prompt(frame_descriptions, memory_prompt)
		contents = self._build_video_contents(selected_frames)
		if not contents:
			self._logger.info("No decodable sign frames found")
			return ""

		response_text = await self._run_with_fallback(
			kind="sign",
			prompt=prompt,
			image_bytes=contents,
		)
		text = self._parse_sign_response(response_text)
		self._logger.debug("Gemini interpreted frames", extra={"text": text[:80]})
		return text

	async def interpret_ambient_audio(self, transcript_text: str, energy_rms: float | None) -> dict[str, str]:
		prompt = (
			self._ambient_prompt_template
			.replace("{{TRANSCRIPT}}", transcript_text.strip() or "<empty>")
			.replace("{{ENERGY_RMS}}", f"{energy_rms:.6f}" if energy_rms is not None else "unknown")
		)
		response_text = await self._run_with_fallback(kind="ambient", prompt=prompt)
		return self._parse_ambient_response(response_text)

	async def _run_with_fallback(
		self,
		kind: str,
		prompt: str,
		image_bytes: Sequence[bytes] | None = None,
	) -> str:
		while True:
			try:
				if kind == "gloss":
					return await self._run_adk_agent(
						runner=self._gloss_runner,
						app_name=self._gloss_app_name,
						prompt=prompt,
					)
				if kind == "sign":
					return await self._run_adk_agent(
						runner=self._sign_runner,
						app_name=self._sign_app_name,
						prompt=prompt,
						image_bytes=image_bytes,
					)
				if kind == "ambient":
					return await self._run_adk_agent(
						runner=self._ambient_runner,
						app_name=self._ambient_app_name,
						prompt=prompt,
					)
				raise ValueError(f"Unknown ADK invocation kind: {kind}")
			except Exception as exc:  # pragma: no cover - API compatibility / access fallback
				if not self._is_model_access_error(exc):
					raise
				if not await self._advance_model_candidate(exc):
					raise

	async def _advance_model_candidate(self, exc: Exception) -> bool:
		async with self._model_switch_lock:
			next_index = self._model_index + 1
			if next_index >= len(self._model_candidates):
				return False

			self._model_index = next_index
			next_model = self._model_candidates[self._model_index]
			self._configure_adk_agents()
			self._logger.warning(
				"Gemini model unavailable, falling back",
				extra={"model": next_model, "reason": str(exc)},
			)
			return True

	def _configure_adk_agents(self) -> None:
		model_name = self._model_candidates[self._model_index]

		self._gloss_agent = LlmAgent(
			name="signbridge_gloss_agent",
			model=model_name,
			description="Converts speech transcripts into avatar-ready ASL gloss JSON.",
			instruction=(
				"Transform hearing-side speech into concise ASL gloss and return strict JSON with keys "
				"gloss (array), facial (string), emotion (string)."
			),
			generate_content_config=genai_types.GenerateContentConfig(
				temperature=self._temperature,
				top_p=0.9,
			),
		)

		self._sign_agent = LlmAgent(
			name="signbridge_sign_interpreter_agent",
			model=model_name,
			description="Interprets image frame sequences of sign language.",
			instruction=(
				"Interpret sign frame sequences and return strict JSON with keys has_signing (boolean) and text (string)."
			),
			generate_content_config=genai_types.GenerateContentConfig(
				temperature=self._temperature,
				top_p=0.95,
			),
		)

		self._ambient_agent = LlmAgent(
			name="signbridge_ambient_audio_agent",
			model=model_name,
			description="Classifies ambient audio into speech/music/noise/silence categories.",
			instruction=(
				"Interpret ambient audio transcript candidates and return strict JSON with keys "
				"category (speech|music|noise|silence|unclear) and text (string)."
			),
			generate_content_config=genai_types.GenerateContentConfig(
				temperature=self._temperature,
				top_p=0.9,
			),
		)

		self._gloss_runner = Runner(
			agent=self._gloss_agent,
			app_name=self._gloss_app_name,
			session_service=self._session_service,
		)
		self._sign_runner = Runner(
			agent=self._sign_agent,
			app_name=self._sign_app_name,
			session_service=self._session_service,
		)
		self._ambient_runner = Runner(
			agent=self._ambient_agent,
			app_name=self._ambient_app_name,
			session_service=self._session_service,
		)

	async def _run_adk_agent(
		self,
		runner: Runner,
		app_name: str,
		prompt: str,
		image_bytes: Sequence[bytes] | None = None,
	) -> str:
		session_id = f"{app_name}-{uuid4().hex}"
		await self._create_session(app_name=app_name, session_id=session_id)

		parts: list[genai_types.Part] = [genai_types.Part(text=prompt)]
		if image_bytes:
			for payload in image_bytes:
				parts.append(
					genai_types.Part(
						inline_data=genai_types.Blob(data=payload, mime_type="image/jpeg")
					)
				)

		content = genai_types.Content(role="user", parts=parts)
		final_text = ""

		run_async_fn = getattr(runner, "run_async", None)
		if callable(run_async_fn):
			async for event in run_async_fn(
				user_id=self._adk_user_id,
				session_id=session_id,
				new_message=content,
			):
				candidate = self._extract_final_event_text(event)
				if candidate:
					final_text = candidate
		else:
			events = await asyncio.to_thread(
				runner.run,
				user_id=self._adk_user_id,
				session_id=session_id,
				new_message=content,
			)
			for event in events:
				candidate = self._extract_final_event_text(event)
				if candidate:
					final_text = candidate

		if final_text:
			return final_text

		raise RuntimeError("ADK returned no final text response")

	async def _create_session(self, app_name: str, session_id: str) -> None:
		result = self._session_service.create_session(
			app_name=app_name,
			user_id=self._adk_user_id,
			session_id=session_id,
		)
		if inspect.isawaitable(result):
			await result

	def _extract_text_from_content(self, content: Any) -> str:
		parts = getattr(content, "parts", []) or []
		chunks: list[str] = []
		for part in parts:
			text = getattr(part, "text", None)
			if isinstance(text, str) and text.strip():
				chunks.append(text.strip())
		return "\n".join(chunks).strip()

	def _extract_final_event_text(self, event: Any) -> str:
		is_final_response = False
		is_final_response_fn = getattr(event, "is_final_response", None)
		if callable(is_final_response_fn):
			is_final_response = bool(is_final_response_fn())

		if not is_final_response:
			return ""

		event_content = getattr(event, "content", None)
		if event_content is None:
			return ""

		return self._extract_text_from_content(event_content)

	def _build_model_candidates(self, primary: str, fallbacks: Sequence[str]) -> list[str]:
		candidates: list[str] = []
		for model in [primary, *fallbacks]:
			if model and model not in candidates:
				candidates.append(model)
		return candidates

	def _is_model_access_error(self, exc: Exception) -> bool:
		message = str(exc).lower()
		return (
			("publisher model" in message and ("not found" in message or "does not have access" in message))
			or ("not found" in message and "model" in message)
			or ("permission" in message and "model" in message)
		)

	def _select_sign_frames(self, frames_b64: Sequence[str], max_frames: int = 6) -> list[str]:
		if len(frames_b64) <= max_frames:
			return list(frames_b64)
		return list(frames_b64[-max_frames:])

	def _build_video_contents(self, frames_b64: Sequence[str]) -> list[bytes]:
		frame_payloads: list[bytes] = []
		for frame in frames_b64:
			try:
				frame_bytes = base64.b64decode(frame, validate=True)
			except (binascii.Error, ValueError):
				continue
			if not frame_bytes:
				continue
			frame_payloads.append(frame_bytes)
		return frame_payloads

	def _parse_sign_response(self, payload: str) -> str:
		payload = payload.strip()
		if not payload:
			return ""

		try:
			data = safe_json_loads(payload)
		except ValueError:
			data = self._fallback_parse_sign(payload)

		has_signing = bool(data.get("has_signing", False))
		text = str(data.get("text", "")).strip()
		if not has_signing:
			return ""

		normalized = text.lower().strip(" .,!?")
		if normalized in {"", "no_sign", "no sign", "none", "null"}:
			return ""
		return text

	def _parse_gloss_response(self, payload: str) -> GlossPlan:
		payload = payload or "{}"
		try:
			data = safe_json_loads(payload)
		except ValueError:
			data = self._fallback_parse_gloss(payload)
		gloss = data.get("gloss", [])
		facial = data.get("facial", "neutral")
		emotion = data.get("emotion", "neutral")
		plan = GlossPlan(gloss=gloss, facial=facial, emotion=emotion)
		self._logger.debug("Gemini gloss result", extra={"tokens": gloss})
		return plan

	def _parse_ambient_response(self, payload: str) -> dict[str, str]:
		payload = payload.strip()
		if not payload:
			return {"category": "unclear", "text": "No clear speech detected."}

		try:
			data = safe_json_loads(payload)
		except ValueError:
			data = self._fallback_parse_ambient(payload)

		category = str(data.get("category", "unclear")).strip().lower()
		if category not in {"speech", "music", "noise", "silence", "unclear"}:
			category = "unclear"

		text = str(data.get("text", "")).strip()
		if not text:
			text = "No clear speech detected."

		return {"category": category, "text": text}

	def _fallback_parse_gloss(self, payload: str) -> dict:
		try:
			start = payload.index("{")
			end = payload.rindex("}") + 1
			return json.loads(payload[start:end])
		except (ValueError, json.JSONDecodeError):  # pragma: no cover - defensive
			self._logger.warning("Gemini gloss parse failed", extra={"payload": payload})
			return {"gloss": [], "facial": "neutral", "emotion": "neutral"}

	def _fallback_parse_sign(self, payload: str) -> dict:
		try:
			start = payload.index("{")
			end = payload.rindex("}") + 1
			return json.loads(payload[start:end])
		except (ValueError, json.JSONDecodeError):  # pragma: no cover - defensive
			self._logger.warning("Gemini sign parse failed", extra={"payload": payload})
			return {"has_signing": False, "text": ""}

	def _fallback_parse_ambient(self, payload: str) -> dict:
		try:
			start = payload.index("{")
			end = payload.rindex("}") + 1
			return json.loads(payload[start:end])
		except (ValueError, json.JSONDecodeError):  # pragma: no cover - defensive
			self._logger.warning("Gemini ambient parse failed", extra={"payload": payload})
			return {"category": "unclear", "text": "No clear speech detected."}

	def _build_gloss_prompt(self, transcript: str, memory_prompt: str) -> str:
		return (
			self._translation_prompt_template
			.replace("{{MEMORY_CONTEXT}}", memory_prompt)
			.replace("{{TRANSCRIPT}}", transcript)
		)

	def _build_video_prompt(self, frame_descriptions: str, memory_prompt: str) -> str:
		return (
			self._interpretation_prompt_template
			.replace("{{MEMORY_CONTEXT}}", memory_prompt)
			.replace("{{FRAME_DESCRIPTIONS}}", frame_descriptions)
		)

	def _load_prompt_template(self, filename: str, default_template: str) -> str:
		project_root = Path(__file__).resolve().parents[2]
		prompt_path = project_root / "prompts" / filename
		try:
			content = prompt_path.read_text(encoding="utf-8").strip()
			if content:
				return content
		except OSError:
			self._logger.warning("Prompt file not found", extra={"path": str(prompt_path)})
		return default_template
