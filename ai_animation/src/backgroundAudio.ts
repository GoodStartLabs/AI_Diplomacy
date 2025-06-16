/**
 * Background audio management for streaming mode
 */

let backgroundAudio: HTMLAudioElement | null = null;
let isAudioInitialized = false;

/**
 * Initialize background audio for streaming
 * Only loads in streaming mode to avoid unnecessary downloads
 */
export function initializeBackgroundAudio(): void {

  if (isAudioInitialized) {
    throw new Error("Attempted to init audio twice.")
  }

  isAudioInitialized = true;

  // Create audio element
  backgroundAudio = new Audio();
  backgroundAudio.loop = true;
  backgroundAudio.volume = 0.4; // 40% volume as requested

  // For now, we'll use a placeholder - you should download and convert the wave file
  // to a smaller MP3 format (aim for < 10MB) and place it in public/sounds/
  backgroundAudio.src = './sounds/background_ambience.mp3';

  // Handle audio loading
  backgroundAudio.addEventListener('canplaythrough', () => {
    console.log('Background audio loaded and ready to play');
  });

  backgroundAudio.addEventListener('error', (e) => {
    console.error('Failed to load background audio:', e);
  });
}

/**
 * Start playing background audio
 * Will only work after user interaction due to browser policies
 */
export function startBackgroundAudio(): void {
  if (!backgroundAudio) {
    console.warn('Background audio not initialized');
    return;
  }
  
  if (backgroundAudio.paused) {
    console.log('Starting background audio...');
    backgroundAudio.play().then(() => {
      console.log('Background audio started successfully');
    }).catch(err => {
      console.warn('Background audio autoplay blocked, will retry on user interaction:', err);
    });
  } else {
    console.log('Background audio already playing');
  }
}

/**
 * Stop background audio
 */
export function stopBackgroundAudio(): void {
  if (!backgroundAudio) {
    console.warn('Background audio not initialized');
    return;
  }
  
  if (!backgroundAudio.paused) {
    console.log('Stopping background audio...');
    backgroundAudio.pause();
  } else {
    console.log('Background audio already paused');
  }
}

/**
 * Set background audio volume
 * @param volume - Volume level from 0 to 1
 */
export function setBackgroundAudioVolume(volume: number): void {
  if (backgroundAudio) {
    backgroundAudio.volume = Math.max(0, Math.min(1, volume));
  }
}
