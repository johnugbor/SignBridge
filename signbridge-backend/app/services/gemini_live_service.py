"""Interaction layer with Gemini Live via Vertex AI."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
from pathlib import Path
from typing import Any, Sequence

import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig, Part

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
		vertexai.init(project=project_id, location=region)
		self._logger = logger
		self._model_candidates = self._build_model_candidates(model_name, fallback_model_names)
		self._model_index = 0
		self._model = GenerativeModel(self._model_candidates[self._model_index])
		self._temperature = temperature
		self._logger.info(
			"Gemini service initialized",
			extra={"model": self._model_candidates[self._model_index]},
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

	async def generate_gloss(self, transcript: str, memory_prompt: str) -> GlossPlan:
		if not transcript:
			return GlossPlan(gloss=[], facial="neutral", emotion="neutral")
		prompt = self._build_gloss_prompt(transcript, memory_prompt)
		response = await self._generate_content(prompt, top_p=0.9)
		return self._parse_gloss_response(response)

	async def interpret_sign_frames(self, frames_b64: Sequence[str], memory_prompt: str) -> str:
		if not frames_b64:
			return ""
		selected_frames = self._select_sign_frames(frames_b64)
		frame_descriptions = "\n".join(
			f"Frame {idx}: [image/jpeg bytes provided]" for idx, _frame in enumerate(selected_frames)
		)
		prompt = self._build_video_prompt(frame_descriptions, memory_prompt)
		contents = self._build_video_contents(prompt, selected_frames)
		if not contents:
			self._logger.info("No decodable sign frames found")
			return ""

		response = await self._generate_content(contents, top_p=0.95)
		text = self._parse_sign_response(response)
		self._logger.debug("Gemini interpreted frames", extra={"text": text[:80]})
		return text

	async def interpret_ambient_audio(self, transcript_text: str, energy_rms: float | None) -> dict[str, str]:
		prompt = (
			self._ambient_prompt_template
			.replace("{{TRANSCRIPT}}", transcript_text.strip() or "<empty>")
			.replace("{{ENERGY_RMS}}", f"{energy_rms:.6f}" if energy_rms is not None else "unknown")
		)
		response = await self._generate_content(prompt, top_p=0.9)
		return self._parse_ambient_response(response)

	async def _generate_content(self, content: Any, top_p: float):  # type: ignore[no-untyped-def]
		attempt = 0
		while True:
			try:
				return await asyncio.to_thread(
					self._model.generate_content,
					content,
					generation_config=GenerationConfig(temperature=self._temperature, top_p=top_p),
				)
			except Exception as exc:  # pragma: no cover - API compatibility / access fallback
				attempt += 1
				if attempt >= len(self._model_candidates) or not self._is_model_access_error(exc):
					raise
				self._model_index += 1
				next_model = self._model_candidates[self._model_index]
				self._model = GenerativeModel(next_model)
				self._logger.warning(
					"Gemini model unavailable, falling back",
					extra={"model": next_model, "reason": str(exc)},
				)

	def _build_model_candidates(self, primary: str, fallbacks: Sequence[str]) -> list[str]:
		candidates: list[str] = []
		for model in [primary, *fallbacks]:
			if model and model not in candidates:
				candidates.append(model)
		return candidates

	def _is_model_access_error(self, exc: Exception) -> bool:
		message = str(exc).lower()
		return (
			"publisher model" in message
			and ("not found" in message or "does not have access" in message)
		)

	def _select_sign_frames(self, frames_b64: Sequence[str], max_frames: int = 6) -> list[str]:
		if len(frames_b64) <= max_frames:
			return list(frames_b64)
		return list(frames_b64[-max_frames:])

	def _build_video_contents(self, prompt: str, frames_b64: Sequence[str]) -> list[Any]:
		parts: list[Any] = [prompt]
		for frame in frames_b64:
			try:
				frame_bytes = base64.b64decode(frame, validate=True)
			except (binascii.Error, ValueError):
				continue
			if not frame_bytes:
				continue
			parts.append(Part.from_data(data=frame_bytes, mime_type="image/jpeg"))
		return parts if len(parts) > 1 else []

	def _parse_sign_response(self, response) -> str:  # type: ignore[no-untyped-def]
		payload = response.text.strip() if getattr(response, "text", None) else ""
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

	def _parse_gloss_response(self, response) -> GlossPlan:  # type: ignore[no-untyped-def]
		payload = response.text if getattr(response, "text", None) else "{}"
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

	def _parse_ambient_response(self, response) -> dict[str, str]:  # type: ignore[no-untyped-def]
		payload = response.text.strip() if getattr(response, "text", None) else ""
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
