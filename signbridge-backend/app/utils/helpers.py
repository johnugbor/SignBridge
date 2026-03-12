"""Utility helpers shared across agents and services."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
	"""Return a timezone-aware UTC timestamp."""

	return datetime.now(tz=timezone.utc)


def generate_session_id() -> str:
	"""Generate a random session identifier."""

	return uuid.uuid4().hex


def b64encode(data: bytes) -> str:
	"""Encode binary payloads to base64 strings suitable for JSON transport."""

	return base64.b64encode(data).decode("utf-8")


def b64decode(data: str) -> bytes:
	"""Decode base64 payloads coming from the frontend."""

	return base64.b64decode(data.encode("utf-8"))


def safe_json_loads(content: str) -> Any:
	"""Safely parse JSON content and return Python objects."""

	try:
		return json.loads(content)
	except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
		raise ValueError("Unable to parse JSON payload from Gemini response") from exc
