"""Pydantic models that describe avatar animation instructions."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GlossPlan(BaseModel):
	"""Structured gloss metadata returned from Gemini."""

	gloss: List[str] = Field(default_factory=list)
	facial: str = "neutral"
	emotion: str = "neutral"


class AnimationInstruction(BaseModel):
	"""Single animation clip reference to be played by the frontend avatar."""

	token: str
	clip_url: str
	order: int
	duration_ms: int = 1200
	facial: Optional[str] = None
	emotion: Optional[str] = None


class AnimationPlan(BaseModel):
	"""Full animation response sent back to the client."""

	session_id: str
	plan_id: str
	instructions: List[AnimationInstruction] = Field(default_factory=list)
	facial: str = "neutral"
	emotion: str = "neutral"
