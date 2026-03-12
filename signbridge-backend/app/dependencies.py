"""Dependency helpers used by FastAPI routes."""

from functools import lru_cache

from .agents.sign_conversation_agent import SignConversationAgent
from .config import get_settings
from .services.gemini_live_service import GeminiLiveService
from .services.sign_animation_service import SignAnimationService
from .services.speech_to_text_service import SpeechToTextService
from .services.text_to_speech_service import TextToSpeechService
from .session.session_manager import SessionManager
from .utils.logger import configure_logging


@lru_cache
def get_logger():
	settings = get_settings()
	return configure_logging(settings.log_level)


@lru_cache
def get_session_manager() -> SessionManager:
	settings = get_settings()
	return SessionManager(
		max_history=settings.session_max_history,
		timeout_seconds=settings.session_timeout_seconds,
		logger=get_logger(),
	)


@lru_cache
def get_speech_service() -> SpeechToTextService:
	settings = get_settings()
	return SpeechToTextService(
		language_code=settings.speech_language_code,
		sample_rate=settings.speech_sample_rate,
		logger=get_logger(),
	)


@lru_cache
def get_gemini_service() -> GeminiLiveService:
	settings = get_settings()
	fallback_models = [
		name.strip()
		for name in settings.gemini_fallback_models.split(",")
		if name.strip()
	]
	return GeminiLiveService(
		project_id=settings.gcp_project_id,
		region=settings.gcp_region,
		model_name=settings.gemini_model_name,
		fallback_model_names=fallback_models,
		temperature=settings.gemini_temperature,
		logger=get_logger(),
	)


@lru_cache
def get_tts_service() -> TextToSpeechService:
	settings = get_settings()
	return TextToSpeechService(
		language_code=settings.tts_language_code,
		voice_name=settings.tts_voice_name,
		audio_encoding=settings.tts_audio_encoding,
		sample_rate=settings.speech_sample_rate,
		logger=get_logger(),
	)


@lru_cache
def get_animation_service() -> SignAnimationService:
	settings = get_settings()
	return SignAnimationService(
		bucket_name=settings.avatar_storage_bucket,
		manifest_path=settings.animation_manifest_path,
		logger=get_logger(),
	)


@lru_cache
def get_sign_conversation_agent() -> SignConversationAgent:
	settings = get_settings()
	return SignConversationAgent(
		speech_service=get_speech_service(),
		gemini_service=get_gemini_service(),
		tts_service=get_tts_service(),
		animation_service=get_animation_service(),
		session_manager=get_session_manager(),
		sample_rate=settings.speech_sample_rate,
		video_buffer=settings.max_video_buffer,
		logger=get_logger(),
	)


__all__ = [
	"get_logger",
	"get_session_manager",
	"get_speech_service",
	"get_gemini_service",
	"get_tts_service",
	"get_animation_service",
	"get_sign_conversation_agent",
]
