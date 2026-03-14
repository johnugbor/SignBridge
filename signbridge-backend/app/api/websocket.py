"""WebSocket endpoint responsible for low-latency multimedia exchange."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..config import Settings
from ..dependencies import (
	get_logger,
	get_session_manager,
	get_sign_conversation_agent,
	get_settings,
)
from ..models.message_models import (
	AudioChunk,
	ControlCommand,
	ErrorMessage,
	RadioAudioChunk,
	SessionAck,
	VideoFrame,
	WebSocketInboundMessage,
	WebSocketOutboundMessage,
)
from ..session.session_manager import SessionManager
from ..utils.helpers import utc_now


def create_websocket_router(settings: Settings) -> APIRouter:
	router = APIRouter()
	active_connections: dict[str, set[WebSocket]] = {}
	connection_lock = asyncio.Lock()

	async def register_connection(session_id: str, websocket: WebSocket) -> None:
		async with connection_lock:
			active_connections.setdefault(session_id, set()).add(websocket)

	async def move_connection(websocket: WebSocket, from_session: str, to_session: str) -> bool:
		if from_session == to_session:
			return False
		from_session_is_empty = False
		async with connection_lock:
			peers = active_connections.get(from_session)
			if peers:
				peers.discard(websocket)
				if not peers:
					active_connections.pop(from_session, None)
					from_session_is_empty = True
			active_connections.setdefault(to_session, set()).add(websocket)
		return from_session_is_empty

	async def unregister_connection(session_id: str, websocket: WebSocket) -> bool:
		async with connection_lock:
			peers = active_connections.get(session_id)
			if not peers:
				return True
			peers.discard(websocket)
			if peers:
				return False
			active_connections.pop(session_id, None)
			return True

	async def broadcast(session_id: str, message: WebSocketOutboundMessage) -> None:
		async with connection_lock:
			targets = list(active_connections.get(session_id, set()))

		if not targets:
			return

		payload = message.model_dump()
		stale_connections: list[WebSocket] = []
		for peer in targets:
			try:
				await peer.send_json(payload)
			except (WebSocketDisconnect, RuntimeError):
				stale_connections.append(peer)

		if stale_connections:
			async with connection_lock:
				peers = active_connections.get(session_id)
				if not peers:
					return
				for stale in stale_connections:
					peers.discard(stale)
				if not peers:
					active_connections.pop(session_id, None)

	@router.websocket(settings.websocket_route)
	async def websocket_endpoint(  # type: ignore[misc]
		websocket: WebSocket,
		agent=Depends(get_sign_conversation_agent),
		session_manager: SessionManager = Depends(get_session_manager),
		logger=Depends(get_logger),
	) -> None:
		session_id: str | None = None
		try:
			await websocket.accept()
			session_state = await session_manager.create_session()
			session_id = session_state.session_id
			await register_connection(session_id, websocket)
			await websocket.send_json(
				WebSocketOutboundMessage(
					type="session_ack", payload=SessionAck(session_id=session_id).model_dump()
				).model_dump()
			)
			logger.info("WebSocket connected", extra={"session_id": session_id})

			while True:
				try:
					raw_message = await websocket.receive_json()
					inbound = WebSocketInboundMessage(**raw_message)

					if inbound.type == "ping":
						await websocket.send_json(
							WebSocketOutboundMessage(
								type="pong", payload={"ts": utc_now().isoformat()}
							).model_dump()
						)
						continue

					if inbound.type == "start_session":
						requested_id = inbound.payload.get("session_id")
						if requested_id and requested_id != session_id:
							previous_session_id = session_id
							session_state = await session_manager.create_session(requested_id)
							session_id = session_state.session_id
							previous_is_empty = await move_connection(websocket, previous_session_id, session_id)
							if previous_is_empty:
								await session_manager.end_session(previous_session_id)
						await websocket.send_json(
							WebSocketOutboundMessage(
								type="session_ack",
								payload=SessionAck(session_id=session_id).model_dump(),
							).model_dump()
						)
						continue

					if inbound.type == "audio_chunk":
						chunk = inbound.to_audio_chunk()
						if not chunk.session_id:
							chunk.session_id = session_id
						responses = await agent.handle_audio_chunk(chunk)
						for response in responses:
							await broadcast(chunk.session_id, response)
						continue

					if inbound.type == "radio_audio_chunk":
						radio_chunk: RadioAudioChunk = inbound.to_radio_audio_chunk()
						responses = await agent.handle_radio_audio_chunk(session_id, radio_chunk)
						for response in responses:
							await websocket.send_json(response.model_dump())
						continue

					if inbound.type == "video_frame":
						frame = inbound.to_video_frame()
						if not frame.session_id:
							frame.session_id = session_id
						responses = await agent.handle_video_frame(frame)
						for response in responses:
							await broadcast(frame.session_id, response)
						continue

					if inbound.type == "control":
						command = inbound.to_command()
						response = await agent.handle_control(session_id, command)
						await broadcast(session_id, response)
						continue

					await websocket.send_json(
						WebSocketOutboundMessage(
							type="error",
							payload=ErrorMessage(
								code="unsupported_message",
								detail=f"Unsupported message type {inbound.type}",
							).model_dump(),
						).model_dump()
					)
				except Exception as message_exc:
					logger.exception(
						"WebSocket message processing failed",
						extra={"session_id": session_id},
						exc_info=message_exc,
					)
					await websocket.send_json(
						WebSocketOutboundMessage(
							type="error",
							payload=ErrorMessage(
								code="message_processing_failed",
								detail=str(message_exc),
							).model_dump(),
						).model_dump()
					)
					continue

		except WebSocketDisconnect:
			if session_id:
				is_empty = await unregister_connection(session_id, websocket)
				if is_empty:
					await session_manager.end_session(session_id)
			logger.info("WebSocket disconnected", extra={"session_id": session_id})
		except Exception as exc:  # pragma: no cover - defensive logging
			logger.exception("WebSocket error", exc_info=exc)
			try:
				await websocket.send_json(
					WebSocketOutboundMessage(
						type="error",
						payload=ErrorMessage(code="server_error", detail=str(exc)).model_dump(),
					).model_dump()
				)
			except WebSocketDisconnect:
				pass
			if session_id:
				is_empty = await unregister_connection(session_id, websocket)
				if is_empty:
					await session_manager.end_session(session_id)

	return router


def get_websocket_router() -> APIRouter:
	"""FastAPI dependency entrypoint used by main.py."""

	return create_websocket_router(get_settings())
