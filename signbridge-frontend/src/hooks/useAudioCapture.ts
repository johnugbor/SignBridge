import { useState, useCallback, useRef, useEffect } from 'react'

const AUDIO_CHUNK_INTERVAL_MS = 300
const SCRIPT_PROCESSOR_BUFFER_SIZE = 4096

type OnAudioChunk = (chunk: Float32Array, isFinal: boolean, inputSampleRate: number) => void

const getAudioContextConstructor = () => {
  if (typeof window === 'undefined') {
    return null
  }

  return (window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext) ?? null
}

export const useAudioCapture = () => {
  const [isRecording, setIsRecording] = useState(false)
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null)
  const muteGainNodeRef = useRef<GainNode | null>(null)
  const flushIntervalRef = useRef<number | null>(null)
  const pendingSamplesRef = useRef<Float32Array[]>([])
  const onAudioChunkRef = useRef<OnAudioChunk | null>(null)

  const flushPendingSamples = useCallback((isFinal: boolean) => {
    const onAudioChunk = onAudioChunkRef.current
    const audioContext = audioContextRef.current

    if (!onAudioChunk || !audioContext) {
      pendingSamplesRef.current = []
      return
    }

    const chunks = pendingSamplesRef.current
    if (!chunks.length) {
      return
    }

    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
    const merged = new Float32Array(totalLength)
    let offset = 0

    for (const chunk of chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }

    pendingSamplesRef.current = []
    onAudioChunk(merged, isFinal, audioContext.sampleRate)
  }, [])

  const stopRecording = useCallback(() => {
    if (flushIntervalRef.current !== null) {
      window.clearInterval(flushIntervalRef.current)
      flushIntervalRef.current = null
    }

    flushPendingSamples(true)

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect()
      processorNodeRef.current.onaudioprocess = null
      processorNodeRef.current = null
    }

    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect()
      sourceNodeRef.current = null
    }

    if (muteGainNodeRef.current) {
      muteGainNodeRef.current.disconnect()
      muteGainNodeRef.current = null
    }

    if (audioContextRef.current) {
      void audioContextRef.current.close()
      audioContextRef.current = null
    }

    pendingSamplesRef.current = []
    onAudioChunkRef.current = null
    setIsRecording(false)

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }, [flushPendingSamples])

  const startRecording = useCallback(
    async (onDataAvailable: OnAudioChunk) => {
      if (isRecording) {
        return
      }

      try {
        const AudioContextCtor = getAudioContextConstructor()
        if (!AudioContextCtor) {
          throw new Error('AudioContext is not available in this browser')
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        streamRef.current = stream
        onAudioChunkRef.current = onDataAvailable
        pendingSamplesRef.current = []

        const audioContext = new AudioContextCtor()
        audioContextRef.current = audioContext

        if (audioContext.state === 'suspended') {
          await audioContext.resume()
        }

        const sourceNode = audioContext.createMediaStreamSource(stream)
        sourceNodeRef.current = sourceNode

        const processorNode = audioContext.createScriptProcessor(
          SCRIPT_PROCESSOR_BUFFER_SIZE,
          1,
          1
        )
        processorNodeRef.current = processorNode

        const muteGainNode = audioContext.createGain()
        muteGainNode.gain.value = 0
        muteGainNodeRef.current = muteGainNode

        processorNode.onaudioprocess = (event: AudioProcessingEvent) => {
          const channelData = event.inputBuffer.getChannelData(0)
          const copied = new Float32Array(channelData.length)
          copied.set(channelData)
          pendingSamplesRef.current.push(copied)
        }

        sourceNode.connect(processorNode)
        processorNode.connect(muteGainNode)
        muteGainNode.connect(audioContext.destination)

        flushIntervalRef.current = window.setInterval(() => {
          flushPendingSamples(false)
        }, AUDIO_CHUNK_INTERVAL_MS)

        setIsRecording(true)
      } catch (error) {
        console.error('Failed to start recording:', error)
        setIsRecording(false)
        stopRecording()
        throw error
      }
    },
    [flushPendingSamples, isRecording, stopRecording]
  )

  useEffect(() => {
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  return {
    isRecording,
    startRecording,
    stopRecording
  }
}
