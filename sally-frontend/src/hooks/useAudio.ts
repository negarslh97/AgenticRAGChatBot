import { useCallback, useRef } from 'react';

/**
 * Custom hook for playing audio files
 * @param audioSrc - The source path to the audio file
 * @returns An object with play function and audio ref
 */
export const useAudio = (audioSrc: string) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const play = useCallback(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio(audioSrc);
    }
    
    // Reset audio to beginning and play
    audioRef.current.currentTime = 0;
    audioRef.current.play().catch(error => {
      console.error('Failed to play audio:', error);
    });
  }, [audioSrc]);

  return { play, audioRef };
};