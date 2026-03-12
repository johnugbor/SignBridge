const encodeBase64 = (binary: string) => {
  if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
    return window.btoa(binary)
  }
  throw new Error('Base64 encoding is not supported in this environment')
}

const decodeBase64 = (base64: string) => {
  if (typeof window !== 'undefined' && typeof window.atob === 'function') {
    return window.atob(base64)
  }
  throw new Error('Base64 decoding is not supported in this environment')
}

const floatTo16BitPCM = (input: Float32Array): ArrayBuffer => {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)

  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]))
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
  }

  return buffer
}

const resampleFloat32 = (
  input: Float32Array,
  inputSampleRate: number,
  targetSampleRate: number
): Float32Array => {
  if (inputSampleRate === targetSampleRate || input.length === 0) {
    return input
  }

  const ratio = inputSampleRate / targetSampleRate
  const outputLength = Math.max(1, Math.round(input.length / ratio))
  const output = new Float32Array(outputLength)

  if (ratio > 1) {
    // Downsample by averaging ranges to reduce aliasing.
    let inputIndex = 0
    for (let i = 0; i < outputLength; i += 1) {
      const nextInputIndex = Math.min(input.length, Math.round((i + 1) * ratio))
      let sum = 0
      let count = 0

      for (let j = inputIndex; j < nextInputIndex; j += 1) {
        sum += input[j]
        count += 1
      }

      output[i] = count > 0 ? sum / count : 0
      inputIndex = nextInputIndex
    }

    return output
  }

  // Upsample with linear interpolation.
  for (let i = 0; i < outputLength; i += 1) {
    const sourceIndex = i * ratio
    const lower = Math.floor(sourceIndex)
    const upper = Math.min(input.length - 1, lower + 1)
    const weight = sourceIndex - lower
    output[i] = input[lower] * (1 - weight) + input[upper] * weight
  }

  return output
}

export const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer)
  const chunk = 0x8000
  let binary = ''

  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
  }

  return encodeBase64(binary)
}

export const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
  if (!base64) {
    return new ArrayBuffer(0)
  }

  const binary = decodeBase64(base64)
  const buffer = new ArrayBuffer(binary.length)
  const bytes = new Uint8Array(buffer)

  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }

  return buffer
}

export const resampleFloat32ToPCM16Base64 = (
  samples: Float32Array,
  inputSampleRate: number,
  targetSampleRate = 16000
): { base64: string; sampleRate: number; byteLength: number } => {
  const resampled = resampleFloat32(samples, inputSampleRate, targetSampleRate)
  const pcmBuffer = floatTo16BitPCM(resampled)

  return {
    base64: arrayBufferToBase64(pcmBuffer),
    sampleRate: targetSampleRate,
    byteLength: pcmBuffer.byteLength
  }
}

let decodingContext: AudioContext | null = null

const getDecodingContext = () => {
  if (!decodingContext) {
    decodingContext = new AudioContext()
  }
  return decodingContext
}

export const resampleBlobToPCM16Base64 = async (
  blob: Blob,
  targetSampleRate = 16000
): Promise<{ base64: string; sampleRate: number; byteLength: number }> => {
  if (typeof window === 'undefined' || typeof OfflineAudioContext === 'undefined') {
    throw new Error('Offline audio context is not available in this environment')
  }

  const buffer = await blob.arrayBuffer()
  const context = getDecodingContext()
  const decoded = await context.decodeAudioData(buffer.slice(0))

  const monoBuffer = context.createBuffer(1, decoded.length, decoded.sampleRate)
  const monoData = monoBuffer.getChannelData(0)

  for (let channel = 0; channel < decoded.numberOfChannels; channel += 1) {
    const channelData = decoded.getChannelData(channel)
    for (let i = 0; i < channelData.length; i += 1) {
      monoData[i] += channelData[i] / decoded.numberOfChannels
    }
  }

  const targetLength = Math.ceil((monoBuffer.length * targetSampleRate) / monoBuffer.sampleRate)
  const offline = new OfflineAudioContext(1, targetLength, targetSampleRate)
  const source = offline.createBufferSource()
  source.buffer = monoBuffer
  source.connect(offline.destination)
  source.start(0)
  const rendered = await offline.startRendering()

  const pcmBuffer = floatTo16BitPCM(rendered.getChannelData(0))

  return {
    base64: arrayBufferToBase64(pcmBuffer),
    sampleRate: targetSampleRate,
    byteLength: pcmBuffer.byteLength
  }
}
