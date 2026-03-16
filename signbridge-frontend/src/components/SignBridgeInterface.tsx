import { useCallback, useEffect, useRef, useState } from 'react'
import { useConversationState } from '../hooks/useConversationState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAudioCapture } from '../hooks/useAudioCapture'
import { useAudioPlayback } from '../hooks/useAudioPlayback'
import { useAvatarRenderer } from '../hooks/useAvatarRenderer'
import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import {
  Camera,
  CameraOff,
  Copy,
  Ear,
  Hand,
  LogIn,
  Mic,
  MicOff,
  Plus,
  QrCode,
  Radio,
  Users
} from 'lucide-react'
import { WebSocketServerMessage } from '../types'
import { base64ToArrayBuffer, resampleFloat32ToPCM16Base64 } from '../utils/audio'
import './SignBridgeInterface.css'

const TARGET_SAMPLE_RATE = Number(import.meta.env.VITE_SPEECH_SAMPLE_RATE ?? 16000)
const VIDEO_FRAME_INTERVAL_MS = Number(import.meta.env.VITE_VIDEO_FRAME_INTERVAL_MS ?? 300)
const VIDEO_FRAME_MIME_TYPE = 'image/jpeg'
const TRANSCRIPT_RETENTION_MS = Number(import.meta.env.VITE_TRANSCRIPT_RETENTION_MS ?? 8000)
const MAX_TRANSCRIPT_HISTORY_ITEMS = Number(import.meta.env.VITE_MAX_TRANSCRIPT_HISTORY_ITEMS ?? 4)
const LAST_JOINED_SESSION_STORAGE_KEY = 'signbridge:lastJoinedSessionId'
type InteractionMode = 'hearer' | 'deaf' | 'radio'
type SessionAction = 'create' | 'join' | 'leave' | null

const MODE_CONFIG: Record<InteractionMode, { label: string; description: string; icon: LucideIcon }> = {
  hearer: {
    label: 'Hearer Mode',
    description: 'Speak and get text translation.',
    icon: Ear
  },
  deaf: {
    label: 'Deaf Mode',
    description: 'Sign and receive text transcription.',
    icon: Hand
  },
  radio: {
    label: 'Radio Mode',
    description: 'Interpret ambient audio in realtime.',
    icon: Radio
  }
}

const createSessionToken = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 16)
  }
  return Math.random().toString(36).slice(2, 18)
}

const readStoredSessionId = () => {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const storedSessionId = window.localStorage.getItem(LAST_JOINED_SESSION_STORAGE_KEY)?.trim()
    return storedSessionId || null
  } catch {
    return null
  }
}

const writeStoredSessionId = (joinedSessionId: string | null) => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    if (joinedSessionId) {
      window.localStorage.setItem(LAST_JOINED_SESSION_STORAGE_KEY, joinedSessionId)
    } else {
      window.localStorage.removeItem(LAST_JOINED_SESSION_STORAGE_KEY)
    }
  } catch {
    // Ignore storage failures (for example in restricted browsing modes).
  }
}

const SignBridgeInterface = () => {
  const { state, setListening, setProcessing, setTranscript, setAnimation, setError } = useConversationState()
  const { send, subscribe } = useWebSocket()
  const { isRecording, startRecording, stopRecording } = useAudioCapture()
  const { playAudio } = useAudioPlayback()
  const { error: avatarError } = useAvatarRenderer('avatar-container')

  const [mode, setMode] = useState<InteractionMode>('hearer')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionToJoin, setSessionToJoin] = useState('')
  const [sessionAction, setSessionAction] = useState<SessionAction>(null)
  const [isSessionJoined, setIsSessionJoined] = useState(false)
  const [showCopiedToast, setShowCopiedToast] = useState(false)
  const [isSigning, setIsSigning] = useState(false)
  const [isRadioListening, setIsRadioListening] = useState(false)
  const [isRadioStarting, setIsRadioStarting] = useState(false)
  const sequenceRef = useRef(0)
  const frameIdRef = useRef(0)
  const videoPreviewRef = useRef<HTMLVideoElement | null>(null)
  const cameraStreamRef = useRef<MediaStream | null>(null)
  const captureIntervalRef = useRef<number | null>(null)
  const frameCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const radioSequenceRef = useRef(0)
  const lastRadioResponseAtRef = useRef(0)
  const pendingJoinSessionIdRef = useRef<string | null>(null)
  const copyToastTimerRef = useRef<number | null>(null)
  const transcriptHistoryRef = useRef<string[]>([])
  const activeTranscriptRef = useRef('')
  const transcriptClearTimerRef = useRef<number | null>(null)

  const isHearer = mode === 'hearer'
  const isDeaf = mode === 'deaf'
  const isRadioStreaming = mode === 'radio' && (isRadioListening || isRecording || isRadioStarting)
  const isSessionActionPending = sessionAction !== null

  const renderBufferedTranscript = useCallback(() => {
    const chunks = [...transcriptHistoryRef.current]
    const activeTranscript = activeTranscriptRef.current.trim()
    if (activeTranscript) {
      chunks.push(activeTranscript)
    }

    setTranscript(chunks.join(' '))
  }, [setTranscript])

  const scheduleTranscriptClear = useCallback(() => {
    if (transcriptClearTimerRef.current !== null) {
      window.clearTimeout(transcriptClearTimerRef.current)
    }

    transcriptClearTimerRef.current = window.setTimeout(() => {
      transcriptHistoryRef.current = []
      activeTranscriptRef.current = ''
      setTranscript('')
      transcriptClearTimerRef.current = null
    }, TRANSCRIPT_RETENTION_MS)
  }, [setTranscript])

  const appendTranscriptSegment = useCallback(
    (text: string, isFinal: boolean) => {
      const normalized = text.trim()

      if (!isFinal) {
        if (transcriptClearTimerRef.current !== null) {
          window.clearTimeout(transcriptClearTimerRef.current)
          transcriptClearTimerRef.current = null
        }

        activeTranscriptRef.current = normalized
        renderBufferedTranscript()
        return
      }

      activeTranscriptRef.current = ''

      if (normalized) {
        const windowSize = Math.max(1, MAX_TRANSCRIPT_HISTORY_ITEMS)
        const nextHistory = [...transcriptHistoryRef.current, normalized]
        transcriptHistoryRef.current = nextHistory.slice(-windowSize)
      }

      renderBufferedTranscript()
      scheduleTranscriptClear()
    },
    [renderBufferedTranscript, scheduleTranscriptClear]
  )

  const handleServerMessage = useCallback(
    (message: WebSocketServerMessage) => {
      switch (message.type) {
        case 'session_ack': {
          const acknowledgedSessionId = message.payload.session_id
          const pendingJoinSessionId = pendingJoinSessionIdRef.current
          const hasPendingJoin = Boolean(pendingJoinSessionId)
          const isPendingJoinAck = hasPendingJoin && pendingJoinSessionId === acknowledgedSessionId

          // Ignore bootstrap/private acks while waiting for the intended join target.
          if (hasPendingJoin && !isPendingJoinAck) {
            break
          }

          setSessionId(acknowledgedSessionId)

          if (sessionAction === 'create' || isPendingJoinAck) {
            setSessionToJoin(acknowledgedSessionId)
            setIsSessionJoined(true)
            writeStoredSessionId(acknowledgedSessionId)
            pendingJoinSessionIdRef.current = null
          }
          if (sessionAction === 'leave') {
            setIsSessionJoined(false)
            setSessionToJoin('')
            writeStoredSessionId(null)
            pendingJoinSessionIdRef.current = null
          }
          setSessionAction(null)

          setError(null)
          setProcessing(false)
          sequenceRef.current = 0
          break
        }
        case 'transcript': {
          const { segment } = message.payload
          appendTranscriptSegment(segment.text, segment.is_final)
          setProcessing(!segment.is_final)
          break
        }
        case 'radio_transcript':
          lastRadioResponseAtRef.current = Date.now()
          setIsRadioStarting(false)
          if (message.payload.category === 'speech') {
            setTranscript(message.payload.text)
          } else {
            setTranscript(`[${message.payload.category.toUpperCase()}] ${message.payload.text}`)
          }
          setProcessing(false)
          break
        case 'animation':
          setAnimation(message.payload)
          setProcessing(false)
          break
        case 'audio':
          if (isHearer && message.payload.audio_b64) {
            const audioBuffer = base64ToArrayBuffer(message.payload.audio_b64)
            void playAudio(audioBuffer)
          }
          break
        case 'error':
          setSessionAction(null)
          pendingJoinSessionIdRef.current = null
          if (
            mode === 'radio' &&
            typeof message.payload.detail === 'string' &&
            message.payload.detail.includes('Unsupported message type radio_audio_chunk')
          ) {
            setError('Radio Mode backend is not updated yet. Restart/rebuild backend to enable intelligent radio captions.')
            stopRecording()
            setIsRadioListening(false)
            setIsRadioStarting(false)
          } else {
            setError(message.payload.detail || 'Unexpected server error')
          }
          setProcessing(false)
          setListening(false)
          break
        case 'control':
          if (message.payload.action === 'interrupt') {
            setProcessing(false)
            setListening(false)
          }
          break
        default:
          break
      }
    },
    [
      isHearer,
      mode,
      playAudio,
      sessionAction,
      setAnimation,
      setError,
      setListening,
      setProcessing,
      setSessionAction,
      setSessionToJoin,
      setTranscript,
      appendTranscriptSegment,
      stopRecording
    ]
  )

  useEffect(() => {
    return subscribe(handleServerMessage)
  }, [handleServerMessage, subscribe])

  const requestJoinSession = useCallback(
    (rawSessionId: string) => {
      const targetSession = rawSessionId.trim()

      if (!targetSession) {
        setError('Enter a valid session ID to join.')
        return false
      }

      setError(null)
      setSessionToJoin(targetSession)
      setSessionAction('join')
      pendingJoinSessionIdRef.current = targetSession
      send({
        type: 'start_session',
        payload: {
          session_id: targetSession
        }
      })

      return true
    },
    [send, setError]
  )

  useEffect(() => {
    const search = new URLSearchParams(window.location.search)
    const requestedSession = search.get('session')?.trim()
    const storedSession = readStoredSessionId()
    const targetSession = requestedSession || storedSession

    if (!targetSession) {
      return
    }

    requestJoinSession(targetSession)
  }, [requestJoinSession])

  const releaseCamera = useCallback(() => {
    if (captureIntervalRef.current !== null) {
      window.clearInterval(captureIntervalRef.current)
      captureIntervalRef.current = null
    }

    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      cameraStreamRef.current = null
    }

    if (videoPreviewRef.current) {
      videoPreviewRef.current.pause()
      videoPreviewRef.current.srcObject = null
    }
  }, [])

  const handleChunk = useCallback(
    async (audioChunk: Float32Array, isFinalChunk: boolean, inputSampleRate: number) => {
      try {
        if (audioChunk.length === 0) {
          return
        }

        const { base64, sampleRate } = resampleFloat32ToPCM16Base64(
          audioChunk,
          inputSampleRate,
          TARGET_SAMPLE_RATE
        )
        const sequenceId = sequenceRef.current

        if (isFinalChunk) {
          setProcessing(true)
        }

        sequenceRef.current += 1

        send({
          type: 'audio_chunk',
          payload: {
            session_id: sessionId ?? undefined,
            sequence_id: sequenceId,
            audio_b64: base64,
            sample_rate: sampleRate,
            is_final: isFinalChunk
          }
        })
      } catch (error: unknown) {
        console.error('Failed to encode audio chunk', error)

        if (!isFinalChunk) {
          return
        }

        setError('Unable to process audio. Check microphone permissions and try again.')
        setListening(false)
        setProcessing(false)
      }
    },
    [send, sessionId, setError, setListening, setProcessing]
  )

  const captureVideoFrame = useCallback(
    async (isFinal: boolean) => {
      const videoElement = videoPreviewRef.current
      if (!videoElement || videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
        return
      }

      if (!frameCanvasRef.current) {
        frameCanvasRef.current = document.createElement('canvas')
      }

      const canvas = frameCanvasRef.current
      canvas.width = videoElement.videoWidth
      canvas.height = videoElement.videoHeight

      const context = canvas.getContext('2d')
      if (!context) {
        throw new Error('Unable to capture video frame context')
      }

      context.drawImage(videoElement, 0, 0, canvas.width, canvas.height)
      const dataUrl = canvas.toDataURL(VIDEO_FRAME_MIME_TYPE, 0.8)
      const dataB64 = dataUrl.split(',')[1]

      if (!dataB64) {
        throw new Error('Captured frame is empty')
      }

      const frameId = frameIdRef.current
      frameIdRef.current += 1

      send({
        type: 'video_frame',
        payload: {
          session_id: sessionId ?? undefined,
          frame_id: frameId,
          data_b64: dataB64,
          mime_type: VIDEO_FRAME_MIME_TYPE,
          is_final: isFinal
        }
      })
    },
    [send, sessionId]
  )

  const handleStartSigning = useCallback(async () => {
    if (isSigning) {
      return
    }

    setError(null)
    setTranscript('')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      })

      cameraStreamRef.current = stream
      frameIdRef.current = 0

      const videoElement = videoPreviewRef.current
      if (!videoElement) {
        throw new Error('Video preview element is not ready')
      }

      videoElement.srcObject = stream
      await videoElement.play()

      captureIntervalRef.current = window.setInterval(() => {
        captureVideoFrame(false).catch((error: unknown) => {
          console.error('Failed to capture sign frame', error)
          setError('Unable to process sign video. Check camera permissions and try again.')
          setProcessing(false)
          setListening(false)
          setIsSigning(false)
          releaseCamera()
        })
      }, VIDEO_FRAME_INTERVAL_MS)

      setIsSigning(true)
      setListening(true)
    } catch (error: unknown) {
      console.error('Failed to start sign capture', error)
      setError('Camera access is required to capture sign language input.')
      setListening(false)
      setProcessing(false)
      setIsSigning(false)
      releaseCamera()
    }
  }, [captureVideoFrame, isSigning, releaseCamera, setError, setListening, setProcessing, setTranscript])

  const handleStopSigning = useCallback(async () => {
    if (!isSigning) {
      releaseCamera()
      setListening(false)
      return
    }

    try {
      await captureVideoFrame(true)
      setProcessing(true)
    } catch (error: unknown) {
      console.error('Failed to finalize sign capture', error)
      setError('Unable to finalize sign video. Please try again.')
      setProcessing(false)
    }

    releaseCamera()
    setIsSigning(false)
    setListening(false)
  }, [captureVideoFrame, isSigning, releaseCamera, setError, setListening, setProcessing])

  const handleStartListening = async () => {
    if (isRecording) {
      return
    }

    setError(null)

    try {
      await startRecording((audioChunk: Float32Array, isFinalChunk: boolean, inputSampleRate: number) => {
        handleChunk(audioChunk, isFinalChunk, inputSampleRate).catch((error: unknown) => {
          console.error('Chunk pipeline failed', error)
        })
      })
      setListening(true)
    } catch (error: unknown) {
      setError('Microphone access is required to capture speech input.')
      setListening(false)
    }
  }

  const handleStopListening = () => {
    if (!isRecording) {
      return
    }

    stopRecording()
    setListening(false)
  }

  const stopRadioListening = useCallback(() => {
    stopRecording()

    setIsRadioStarting(false)
    setIsRadioListening(false)
    setListening(false)
    setProcessing(false)
  }, [setListening, setProcessing, stopRecording])

  const handleRadioChunk = useCallback(
    async (audioChunk: Float32Array, isFinalChunk: boolean, inputSampleRate: number) => {
      try {
        if (audioChunk.length === 0) {
          return
        }

        const { base64, sampleRate } = resampleFloat32ToPCM16Base64(
          audioChunk,
          inputSampleRate,
          TARGET_SAMPLE_RATE
        )

        let sumSquares = 0
        for (let i = 0; i < audioChunk.length; i += 1) {
          sumSquares += audioChunk[i] * audioChunk[i]
        }
        const energyRms = Math.sqrt(sumSquares / audioChunk.length)

        const sequenceId = radioSequenceRef.current
        radioSequenceRef.current += 1
        setIsRadioStarting(false)

        setProcessing(true)

        send({
          type: 'radio_audio_chunk',
          payload: {
            sequence_id: sequenceId,
            audio_b64: base64,
            sample_rate: sampleRate,
            energy_rms: energyRms,
            is_final: isFinalChunk
          }
        })

        const now = Date.now()
        const elapsed = now - lastRadioResponseAtRef.current
        if (elapsed > 1500) {
          if (energyRms < 0.004) {
            setTranscript('[SILENCE] Listening for nearby sounds...')
          } else if (energyRms < 0.02) {
            setTranscript('[NOISE] Ambient sound detected, waiting for clearer speech...')
          } else {
            setTranscript('[MUSIC/NOISE] Strong ambient audio detected, waiting for intelligent caption...')
          }
        }
      } catch (error: unknown) {
        console.error('Failed to encode radio audio chunk', error)
        if (!isFinalChunk) {
          return
        }
        setError('Unable to process ambient audio for Radio Mode. Please try again.')
        setProcessing(false)
      }
    },
    [send, setError, setProcessing]
  )

  const handleStartRadioListening = useCallback(async () => {
    if (isRadioListening) {
      return
    }

    setIsRadioStarting(true)
    setIsRadioListening(true)
    setListening(true)
    setError(null)
    setTranscript('[LISTENING] Radio Mode is capturing ambient audio...')
    setProcessing(false)

    try {
      radioSequenceRef.current = 0
      lastRadioResponseAtRef.current = Date.now()
      await startRecording((audioChunk: Float32Array, isFinalChunk: boolean, inputSampleRate: number) => {
        handleRadioChunk(audioChunk, isFinalChunk, inputSampleRate).catch((error: unknown) => {
          console.error('Radio chunk pipeline failed', error)
        })
      })
      setIsRadioStarting(false)
    } catch (error: unknown) {
      console.error('Failed to start radio mode capture', error)
      setIsRadioStarting(false)
      setIsRadioListening(false)
      setListening(false)
      setTranscript('[ERROR] Unable to start microphone capture for Radio Mode.')
      setError('Microphone access is required for Radio Mode.')
    }
  }, [handleRadioChunk, isRadioListening, setError, setListening, setProcessing, setTranscript, startRecording])

  const handleCreateSession = () => {
    if (isSessionJoined || isSessionActionPending) {
      return
    }

    const newSessionId = createSessionToken()
    setError(null)
    setSessionAction('create')
    setSessionToJoin(newSessionId)
    send({
      type: 'start_session',
      payload: {
        session_id: newSessionId
      }
    })
  }

  const handleJoinSession = () => {
    if (isSessionActionPending) {
      return
    }

    requestJoinSession(sessionToJoin)
  }

  const handleLeaveSession = () => {
    if (!isSessionJoined || isSessionActionPending) {
      return
    }

    const privateSessionId = createSessionToken()
    setSessionAction('leave')
    setError(null)
    writeStoredSessionId(null)
    pendingJoinSessionIdRef.current = null
    send({
      type: 'start_session',
      payload: {
        session_id: privateSessionId
      }
    })
  }

  const shareSessionUrl =
    isSessionJoined && sessionId
      ? `${window.location.origin}${window.location.pathname}?session=${encodeURIComponent(sessionId)}`
      : ''
  const qrCodeImageUrl = shareSessionUrl
    ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(shareSessionUrl)}`
    : ''
  const shouldShowSessionQr = isSessionJoined && Boolean(qrCodeImageUrl) && mode !== 'radio'

  const handleCopySessionId = async () => {
    if (!sessionId || !navigator.clipboard) {
      return
    }

    try {
      await navigator.clipboard.writeText(sessionId)
      if (copyToastTimerRef.current !== null) {
        window.clearTimeout(copyToastTimerRef.current)
      }
      setShowCopiedToast(true)
      copyToastTimerRef.current = window.setTimeout(() => {
        setShowCopiedToast(false)
        copyToastTimerRef.current = null
      }, 1800)
      setError(null)
    } catch (error: unknown) {
      console.error('Failed to copy session ID', error)
      setError('Unable to copy session ID. Please copy it manually.')
    }
  }

  useEffect(() => {
    return () => {
      releaseCamera()
      stopRadioListening()
      if (copyToastTimerRef.current !== null) {
        window.clearTimeout(copyToastTimerRef.current)
      }
      if (transcriptClearTimerRef.current !== null) {
        window.clearTimeout(transcriptClearTimerRef.current)
      }
    }
  }, [releaseCamera, stopRadioListening])

  const handleSelectHearerMode = () => {
    if (isSigning) {
      void handleStopSigning()
    }
    if (isRadioListening) {
      stopRadioListening()
    }
    setMode('hearer')
  }

  const handleSelectDeafMode = () => {
    if (isRecording) {
      handleStopListening()
    }
    if (isRadioListening) {
      stopRadioListening()
    }
    setMode('deaf')
  }

  const handleSelectRadioMode = () => {
    if (isRecording) {
      handleStopListening()
    }
    if (isSigning) {
      void handleStopSigning()
    }
    setMode('radio')
  }

  const currentModeConfig = MODE_CONFIG[mode]
  const controlCardTitle = isHearer ? 'Voice input' : isDeaf ? 'Sign language input' : currentModeConfig.label
  const CurrentModeIcon = currentModeConfig.icon
  const isPrimaryActionActive = isHearer ? isRecording : isDeaf ? isSigning : isRadioStreaming
  const primaryActionLabel = isHearer
    ? isRecording
      ? 'Stop Listening'
      : 'Start Speaking'
    : isDeaf
      ? isSigning
        ? 'Stop Signing'
        : 'Start Live Sign'
      : isRadioStreaming
        ? 'Stop Radio Mode'
        : 'Start Radio Mode'

  const PrimaryActionIcon = isHearer ? (isRecording ? MicOff : Mic) : isDeaf ? (isSigning ? CameraOff : Camera) : Radio

  const handlePrimaryAction = () => {
    if (isHearer) {
      if (isRecording) {
        handleStopListening()
      } else {
        void handleStartListening()
      }
      return
    }

    if (isDeaf) {
      if (isSigning) {
        void handleStopSigning()
      } else {
        void handleStartSigning()
      }
      return
    }

    if (isRadioListening) {
      stopRadioListening()
    } else {
      void handleStartRadioListening()
    }
  }

  return (
    <div className={`signbridge-interface mode-${mode}`}>
      {showCopiedToast && <div className="copy-toast">Copied</div>}

      <div className="sb-toolbar">
        <div className="sb-mode-toggle">
          {(Object.keys(MODE_CONFIG) as InteractionMode[]).map((modeKey) => {
            const modeDetails = MODE_CONFIG[modeKey]
            const ModeIcon = modeDetails.icon
            const isActive = mode === modeKey

            return (
              <button
                key={modeKey}
                className={`sb-mode-btn ${isActive ? 'active' : ''}`}
                onClick={() => {
                  if (modeKey === 'hearer') {
                    handleSelectHearerMode()
                  } else if (modeKey === 'deaf') {
                    handleSelectDeafMode()
                  } else {
                    handleSelectRadioMode()
                  }
                }}
              >
                <ModeIcon size={16} />
                <span>{modeDetails.label}</span>
              </button>
            )
          })}
        </div>

        {mode !== 'radio' && (
          <div className="sb-session-actions">
            {!isSessionJoined ? (
              <>
                <button className="session-btn" onClick={handleCreateSession} disabled={isSessionActionPending}>
                  <Plus size={15} />
                  <span>{sessionAction === 'create' ? 'Creating...' : 'Create Session'}</span>
                </button>
                <div className="sb-join-group">
                  <input
                    type="text"
                    value={sessionToJoin}
                    onChange={(event) => setSessionToJoin(event.target.value)}
                    placeholder="Session ID"
                    className="session-input"
                  />
                  <button
                    className="session-btn secondary join-btn"
                    onClick={handleJoinSession}
                    disabled={!sessionToJoin.trim() || isSessionActionPending}
                  >
                    <LogIn size={15} />
                    <span>{sessionAction === 'join' ? 'Joining...' : 'Join'}</span>
                  </button>
                </div>
              </>
            ) : (
              <>
                <button
                  className="session-btn danger"
                  onClick={handleLeaveSession}
                  disabled={isSessionActionPending}
                >
                  <span>{sessionAction === 'leave' ? 'Leaving...' : 'Leave Session'}</span>
                </button>
                <button
                  className="session-btn secondary"
                  onClick={() => {
                    void handleCopySessionId()
                  }}
                  disabled={!sessionId}
                >
                  <Copy size={15} />
                  <span>Copy ID</span>
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <div className={`session-info ${mode === 'radio' ? 'radio-only' : ''}`}>
        {mode !== 'radio' && (
          <div className="session-status-left">
            <Users size={16} />
            <span>{`Session: ${isSessionJoined ? sessionId : 'not joined'}`}</span>
          </div>
        )}

        <div className="session-status-right">
          <CurrentModeIcon size={15} />
          <span>{currentModeConfig.description}</span>
        </div>
      </div>

      <div className="interface-container">
        <div className="avatar-column">
          {state.transcript && (
            <section className="transcript-box avatar-transcript">
              <h4>Transcription:</h4>
              <p>{state.transcript}</p>
            </section>
          )}

          {!state.transcript && (
            <section className="transcript-box avatar-transcript muted">
              <h4>Transcription:</h4>
              <p>Live transcription will appear here.</p>
            </section>
          )}

          <section className="avatar-section">
            <div className="panel-header">
              <h3>Sign Animation Avatar</h3>
              <span className="panel-chip">Live Render</span>
            </div>
            <div className="avatar-stage">
              <div id="avatar-container" className="avatar-container"></div>

              {isPrimaryActionActive && (
                <div className="live-chip">
                  <span className="dot"></span>
                  <span>Live Capture</span>
                </div>
              )}
            </div>

            {avatarError && <p className="error">{avatarError}</p>}
          </section>

          {shouldShowSessionQr && qrCodeImageUrl && (
            <section className="session-qr session-qr-mobile">
              <div className="session-qr-header">
                <QrCode size={15} />
                <h4>Session QR</h4>
              </div>
              <img src={qrCodeImageUrl} alt="Session join QR code" />
              <p>Scan to join this session quickly.</p>
            </section>
          )}
        </div>

        <aside className="controls-section">
          <section className="control-card">
            <div className="panel-header">
              <h3 className="control-card-title">{controlCardTitle}</h3>
              <span className="panel-chip">Input</span>
            </div>
            {isDeaf && <p className="control-description">{currentModeConfig.description}</p>}

            {isDeaf && (
              <video ref={videoPreviewRef} className="camera-preview" autoPlay muted playsInline />
            )}

            {isHearer ? (
              <>
                <p className="control-status-text">{isRecording ? 'Listening...' : 'Tap to start speaking'}</p>
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  className={`control-btn control-btn-round ${isRecording ? 'recording' : ''}`}
                  onClick={handlePrimaryAction}
                  aria-label={isRecording ? 'Stop listening' : 'Start speaking'}
                >
                  {isRecording && <span className="mic-pulse-ring" aria-hidden="true"></span>}
                  <PrimaryActionIcon size={30} className="mic-btn-icon" />
                </motion.button>
                <p className="control-caption hearer-caption">{isRecording ? 'Tap to stop' : 'Start Speaking'}</p>
              </>
            ) : (
              <>
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  className={`control-btn ${isPrimaryActionActive ? 'recording' : ''}`}
                  onClick={handlePrimaryAction}
                >
                  <PrimaryActionIcon size={20} />
                  <span>{primaryActionLabel}</span>
                </motion.button>
                <p className="control-caption">
                  {isPrimaryActionActive
                    ? 'Capture is active. Tap to stop.'
                    : mode === 'radio'
                      ? 'Tap to listen for audio around you'
                      : 'Tap to begin input capture.'}
                </p>
              </>
            )}
          </section>

          {shouldShowSessionQr && qrCodeImageUrl && (
            <section className="session-qr session-qr-desktop">
              <div className="session-qr-header">
                <QrCode size={15} />
                <h4>Session QR</h4>
              </div>
              <img src={qrCodeImageUrl} alt="Session join QR code" />
              <p>Scan to join this session quickly.</p>
            </section>
          )}

          {state.isProcessing && (
            <div className="processing-indicator">
              <p>Processing...</p>
            </div>
          )}

          {state.error && (
            <div className="error-box">
              <p>{state.error}</p>
            </div>
          )}

          {mode === 'radio' && (
            <div className="radio-hint-box">
              <CurrentModeIcon size={15} />
              <p>Radio mode captions nearby audio categories using Gemini intelligence.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

export default SignBridgeInterface
