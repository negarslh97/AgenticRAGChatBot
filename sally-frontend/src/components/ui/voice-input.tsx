/**
 * VoiceInput Component
 * 
 * Records audio and transcribes it to text using Whisper API
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { transcriptionService } from '../../services/transcriptionService'
import { toast } from 'react-hot-toast'

interface VoiceInputProps {
  onTranscriptionComplete: (text: string) => void
  disabled?: boolean
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onTranscriptionComplete,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      
      console.log('🎤 Recording stopped')
    }
  }, [isRecording])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      stopRecording()
    }
  }, [stopRecording])

  const startRecording = async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
        
        // Create audio blob
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        console.log('🎤 Audio recorded:', {
          size: audioBlob.size,
          type: audioBlob.type,
          duration: recordingTime
        })

        // Transcribe audio
        await transcribeAudio(audioBlob)
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

      toast.success('ضبط صدا شروع شد')
      console.log('🎤 Recording started')

    } catch (error: any) {
      console.error('❌ Failed to start recording:', error)
      
      if (error.name === 'NotAllowedError') {
        toast.error('دسترسی به میکروفون رد شد')
      } else if (error.name === 'NotFoundError') {
        toast.error('میکروفون یافت نشد')
      } else {
        toast.error('خطا در شروع ضبط صدا')
      }
    }
  }

  const transcribeAudio = async (audioBlob: Blob) => {
    setIsProcessing(true)
    
    try {
      const transcription = await transcriptionService.transcribeAudio(audioBlob, 'voice-message.webm')
      
      if (transcription && transcription.trim()) {
        onTranscriptionComplete(transcription.trim())
        toast.success('صدا به متن تبدیل شد')
      } else {
        toast.error('متن قابل تشخیصی یافت نشد')
      }
    } catch (error: any) {
      console.error('❌ Transcription error:', error)
      toast.error(error.message || 'خطا در تبدیل صدا به متن')
    } finally {
      setIsProcessing(false)
      setRecordingTime(0)
    }
  }

  const handleToggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <>
      <button
        onClick={handleToggleRecording}
        disabled={disabled || isProcessing}
        className={`whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-white h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isRecording 
            ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
            : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
        }`}
        title={isRecording ? 'توقف ضبط صدا' : 'شروع ضبط صدا'}
      >
        {isProcessing ? (
          <div className="animate-spin rounded-full h-4 w-4 md:h-5 md:w-5 border-2 border-white border-t-transparent"></div>
        ) : isRecording ? (
          <MicOff className="h-4 w-4 md:h-5 md:h-5" />
        ) : (
          <Mic className="h-4 w-4 md:h-5 md:h-5" />
        )}
      </button>

      {/* Recording indicator */}
      {isRecording && (
        <div className="flex items-center gap-2 text-sm text-red-600 animate-pulse">
          <span className="h-2 w-2 rounded-full bg-red-600"></span>
          <span className="font-mono">{formatTime(recordingTime)}</span>
        </div>
      )}

      {/* Processing indicator */}
      {isProcessing && (
        <div className="text-sm text-blue-600 flex items-center gap-2">
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
          <span>در حال تبدیل به متن...</span>
        </div>
      )}
    </>
  )
}

