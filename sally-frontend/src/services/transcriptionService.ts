/**
 * Transcription Service
 * 
 * Handles audio transcription using Whisper API
 */

const WHISPER_API_URL = '/whisper'  // از proxy استفاده می‌کنه -> http://192.168.10.222:6000

export interface TranscriptionResponse {
  transcription: string
}

export interface TranscriptionError {
  error: string
}

export const transcriptionService = {
  /**
   * Transcribe audio file to text
   * @param audioBlob - Audio data as Blob
   * @param filename - Optional filename (default: audio.webm)
   * @returns Promise with transcription text
   */
  async transcribeAudio(audioBlob: Blob, filename: string = 'audio.webm'): Promise<string> {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, filename)

      console.log('🎤 Sending audio to Whisper API:', {
        url: `${WHISPER_API_URL}/transcribe`,
        size: audioBlob.size,
        type: audioBlob.type,
        filename
      })

      const response = await fetch(`${WHISPER_API_URL}/transcribe`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData: TranscriptionError = await response.json()
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const data: TranscriptionResponse = await response.json()
      console.log('✅ Transcription successful:', data.transcription)
      
      return data.transcription

    } catch (error: any) {
      console.error('❌ Transcription failed:', error)
      throw new Error(error.message || 'خطا در تبدیل صدا به متن')
    }
  },

  /**
   * Check if Whisper API is available
   * @returns Promise with health status
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${WHISPER_API_URL}/health`)
      if (!response.ok) return false
      
      const data = await response.json()
      console.log('🏥 Whisper API Health:', data)
      return data.status === 'ok'
    } catch (error) {
      console.error('❌ Whisper API not available:', error)
      return false
    }
  }
}

