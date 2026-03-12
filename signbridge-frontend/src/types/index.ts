export interface TranscriptSegment {
  text: string
  confidence?: number
  is_final: boolean
  speaker?: 'hearing' | 'deaf' | 'system'
}

export interface ConversationState {
  isListening: boolean
  isProcessing: boolean
  transcript: string
  animation: AnimationPlan | null
  error: string | null
}

export interface AudioChunkPayload {
  session_id?: string
  sequence_id: number
  audio_b64: string
  sample_rate: number
  language_code?: string
  is_final?: boolean
}

export interface RadioAudioChunkPayload {
  sequence_id: number
  audio_b64: string
  sample_rate: number
  energy_rms?: number
  is_final?: boolean
}

export interface VideoFramePayload {
  session_id?: string
  frame_id: number
  data_b64: string
  mime_type?: string
  is_final?: boolean
}

export interface ControlPayload {
  action: 'start_session' | 'end_session' | 'interrupt' | 'ping'
  target?: 'tts' | 'avatar' | 'all'
}

export interface StartSessionPayload {
  session_id?: string
}

export type WebSocketClientMessage =
  | { type: 'start_session'; payload: StartSessionPayload }
  | { type: 'audio_chunk'; payload: AudioChunkPayload }
  | { type: 'radio_audio_chunk'; payload: RadioAudioChunkPayload }
  | { type: 'video_frame'; payload: VideoFramePayload }
  | { type: 'control'; payload: ControlPayload }
  | { type: 'ping'; payload: Record<string, unknown> }

export interface SessionAckPayload {
  session_id: string
  active: boolean
}

export interface TranscriptMessagePayload {
  session_id: string
  segment: TranscriptSegment
}

export interface RadioTranscriptPayload {
  text: string
  category: 'speech' | 'music' | 'noise' | 'silence' | 'unclear'
  is_final: boolean
}

export interface AnimationInstruction {
  token: string
  clip_url: string
  order: number
  duration_ms: number
  facial?: string
  emotion?: string
}

export interface AnimationPlan {
  session_id: string
  plan_id: string
  instructions: AnimationInstruction[]
  facial: string
  emotion: string
}

export interface AudioPlaybackPayload {
  session_id: string
  audio_b64: string
  sample_rate: number
  mime_type: string
}

export interface ErrorPayload {
  code: string
  detail: string
}

export type WebSocketServerMessage =
  | { type: 'session_ack'; payload: SessionAckPayload }
  | { type: 'transcript'; payload: TranscriptMessagePayload }
  | { type: 'radio_transcript'; payload: RadioTranscriptPayload }
  | { type: 'animation'; payload: AnimationPlan }
  | { type: 'audio'; payload: AudioPlaybackPayload }
  | { type: 'control'; payload: ControlPayload }
  | { type: 'error'; payload: ErrorPayload }
  | { type: 'pong'; payload: Record<string, unknown> }
