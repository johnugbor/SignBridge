import { useRef, useEffect } from 'react'

export const useAudioPlayback = () => {
  const audioContextRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    // Initialize AudioContext on user interaction
    const initAudioContext = () => {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      }
    }

    document.addEventListener('click', initAudioContext, { once: true })
    return () => {
      document.removeEventListener('click', initAudioContext)
    }
  }, [])

  const playAudio = async (audioData: ArrayBuffer) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      }

      const audioBuffer = await audioContextRef.current.decodeAudioData(audioData)
      const source = audioContextRef.current.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContextRef.current.destination)
      source.start(0)
    } catch (error) {
      console.error('Failed to play audio:', error)
    }
  }

  return {
    playAudio,
    audioContext: audioContextRef.current
  }
}
