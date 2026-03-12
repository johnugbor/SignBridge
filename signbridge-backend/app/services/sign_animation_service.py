"""Maps gloss tokens to avatar animation clips stored in Cloud Storage."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Dict, List

from google.cloud import storage

from ..models.animation_models import AnimationInstruction, AnimationPlan, GlossPlan
from ..utils.helpers import generate_session_id


class SignAnimationService:
	def __init__(self, bucket_name: str, manifest_path: str, logger) -> None:
		self._client = storage.Client()
		self._bucket = self._client.bucket(bucket_name)
		self._manifest_path = manifest_path
		self._logger = logger
		self._manifest = self._load_manifest()

	async def build_plan(self, session_id: str, gloss_plan: GlossPlan) -> AnimationPlan:
		instructions: List[AnimationInstruction] = []
		for order, token in enumerate(gloss_plan.gloss):
			clip_uri = self._manifest.get(token.lower()) or f"animations/{token.lower()}.glb"
			clip_url = self._generate_signed_url(clip_uri)
			instructions.append(
				AnimationInstruction(
					token=token,
					clip_url=clip_url,
					order=order,
					facial=gloss_plan.facial,
					emotion=gloss_plan.emotion,
				)
			)

		plan = AnimationPlan(
			session_id=session_id,
			plan_id=generate_session_id(),
			instructions=instructions,
			facial=gloss_plan.facial,
			emotion=gloss_plan.emotion,
		)
		self._logger.debug(
			"Animation plan ready",
			extra={"session_id": session_id, "tokens": gloss_plan.gloss},
		)
		return plan

	def _load_manifest(self) -> Dict[str, str]:
		try:
			blob = self._bucket.blob(self._manifest_path)
			body = blob.download_as_text()
			data = json.loads(body)
			return {k.lower(): v for k, v in data.items()}
		except Exception:  # pragma: no cover - manifest optional in dev
			self._logger.warning("Animation manifest missing; falling back to defaults")
			return {}

	def _generate_signed_url(self, blob_path: str) -> str:
		blob = self._bucket.blob(blob_path)
		try:
			return blob.generate_signed_url(expiration=timedelta(minutes=10))
		except Exception:  # pragma: no cover - dev fallback
			self._logger.warning("Could not sign url", extra={"blob": blob_path})
			return f"https://storage.googleapis.com/{self._bucket.name}/{blob_path}"
