import axios, { AxiosInstance } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/health')
    return response.data
  }

  async sendMessage(message: string): Promise<{ response: string }> {
    const response = await this.client.post('/messages', { text: message })
    return response.data
  }

  async uploadAudio(audioBlob: Blob): Promise<{ transcript: string }> {
    const formData = new FormData()
    formData.append('file', audioBlob)

    const response = await this.client.post('/audio/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }

  async textToSpeech(text: string): Promise<ArrayBuffer> {
    const response = await this.client.post('/audio/synthesize', { text }, {
      responseType: 'arraybuffer'
    })
    return response.data
  }
}

export const apiClient = new APIClient()
