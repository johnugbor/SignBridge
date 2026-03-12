"""Application configuration objects."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Centralized runtime settings loaded from environment variables."""

	app_name: str = "SignBridge Live Backend"
	api_prefix: str = "/api"
	websocket_route: str = "/ws/signbridge"

	gcp_project_id: str = Field(..., alias="GCP_PROJECT_ID")
	gcp_region: str = Field("us-central1", alias="GCP_REGION")
	gemini_model_name: str = Field("gemini-1.5-flash", alias="GEMINI_MODEL_NAME")
	gemini_fallback_models: str = Field("gemini-2.0-flash-001", alias="GEMINI_FALLBACK_MODELS")
	gemini_temperature: float = Field(0.4, alias="GEMINI_TEMPERATURE")

	speech_language_code: str = Field("en-US", alias="SPEECH_LANGUAGE_CODE")
	speech_sample_rate: int = Field(16000, alias="SPEECH_SAMPLE_RATE")

	tts_language_code: str = Field("en-US", alias="TTS_LANGUAGE_CODE")
	tts_voice_name: str = Field("en-US-Neural2-C", alias="TTS_VOICE_NAME")
	tts_audio_encoding: str = Field("MP3", alias="TTS_AUDIO_ENCODING")

	avatar_storage_bucket: str = Field("signbridge-animations", alias="AVATAR_STORAGE_BUCKET")
	animation_manifest_path: str = Field(
		"animations/manifest.json", alias="ANIMATION_MANIFEST_PATH"
	)

	session_timeout_seconds: int = Field(120, alias="SESSION_TIMEOUT_SECONDS")
	session_max_history: int = Field(5, alias="SESSION_MAX_HISTORY")
	max_video_buffer: int = Field(10, alias="MAX_VIDEO_BUFFER")

	log_level: str = Field("INFO", alias="LOG_LEVEL")

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
	"""Return a cached settings instance so every module shares the same config."""

	return Settings()
