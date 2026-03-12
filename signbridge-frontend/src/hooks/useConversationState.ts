import { useCallback, useState } from 'react'
import { ConversationState } from '../types'

const INITIAL_CONVERSATION_STATE: ConversationState = {
  isListening: false,
  isProcessing: false,
  transcript: '',
  animation: null,
  error: null
}

export const useConversationState = () => {
  const [state, setState] = useState<ConversationState>(INITIAL_CONVERSATION_STATE)

  const setListening = useCallback((isListening: boolean) => {
    setState(prev => (prev.isListening === isListening ? prev : { ...prev, isListening }))
  }, [])

  const setProcessing = useCallback((isProcessing: boolean) => {
    setState(prev => (prev.isProcessing === isProcessing ? prev : { ...prev, isProcessing }))
  }, [])

  const setTranscript = useCallback((transcript: string) => {
    setState(prev => (prev.transcript === transcript ? prev : { ...prev, transcript }))
  }, [])

  const setAnimation = useCallback((animation: ConversationState['animation']) => {
    setState(prev => (prev.animation === animation ? prev : { ...prev, animation }))
  }, [])

  const setError = useCallback((error: string | null) => {
    setState(prev => (prev.error === error ? prev : { ...prev, error }))
  }, [])

  const reset = useCallback(() => {
    setState(INITIAL_CONVERSATION_STATE)
  }, [])

  return {
    state,
    setListening,
    setProcessing,
    setTranscript,
    setAnimation,
    setError,
    reset
  }
}
