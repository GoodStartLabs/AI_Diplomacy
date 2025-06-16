import { gameState } from "./gameState";
import { config } from "./config";
// TODO: We need to get these pieces of audio ahead of time, instead of paying for them each time we load the front end
//  These pieces of audio are predetermined. 

// --- ElevenLabs Text-to-Speech configuration ---
let ELEVENLABS_API_KEY = '';

// Try to load from import.meta.env
try {
  // First check if we have the Vite-specific variable
  if (import.meta.env.VITE_ELEVENLABS_API_KEY) {
    ELEVENLABS_API_KEY = String(import.meta.env.VITE_ELEVENLABS_API_KEY).trim();
    // Simplified logging
  }
  // Fallback to the direct env variable (for dev environments)
  else if (import.meta.env.ELEVENLABS_API_KEY) {
    ELEVENLABS_API_KEY = String(import.meta.env.ELEVENLABS_API_KEY).trim();
  }


  // Clean and validate the key
  if (ELEVENLABS_API_KEY) {
    // Remove any unexpected characters that might have been added
    ELEVENLABS_API_KEY = ELEVENLABS_API_KEY.replace(/[^a-zA-Z0-9_\-]/g, '');
    console.log(`ElevenLabs API key: ${ELEVENLABS_API_KEY ? 'Valid' : 'Invalid'} (${ELEVENLABS_API_KEY.length} chars)`);
  }
} catch (err) {
  console.error('Error loading API key:', err);
}

const VOICE_ID = "onwK4e9ZLuTAKqWW03F9";
const MODEL_ID = "eleven_multilingual_v2";

// Test the API key validity directly but don't log unless there's an issue
testElevenLabsKey().catch(err => console.error("Key test failed:", err));

async function testElevenLabsKey() {
  if (!ELEVENLABS_API_KEY) {
    console.warn("Cannot test API key - none provided");
    return;
  }

  try {
    const response = await fetch('https://api.elevenlabs.io/v1/voices', {
      method: 'GET',
      headers: {
        'xi-api-key': ELEVENLABS_API_KEY
      }
    });

    if (response.ok) {
      console.log("✅ ElevenLabs API key is valid and ready for TTS");
    } else {
      console.error(`❌ ElevenLabs API key invalid: ${response.status}`);
    }
  } catch (error) {
    console.error("❌ ElevenLabs API connection error");
  }
}

/**
 * Call ElevenLabs TTS to speak the summary out loud.
 * Returns a promise that resolves only after the audio finishes playing (or fails).
 * Truncates text to first 100 characters for brevity and API limitations.
 * @returns Promise that resolves when audio completes or rejects on error
 */
export async function speakSummary(): Promise<void> {
  if (!config.speechEnabled) {
    console.log("Speech disabled via config, skipping TTS");
    return;
  }
  const summaryText = gameState.currentPhase.summary

  if (!summaryText || summaryText.trim() === '') {
    console.warn("No summary text provided to speakSummary function");
    return;
  }

  // Check if the summary is in JSON format and extract the actual summary text
  let textToSpeak = summaryText;
  try {
    // Check if it starts with a JSON format indicator
    if (summaryText.trim().startsWith('{') && summaryText.includes('"summary"')) {
      const parsedSummary = JSON.parse(summaryText);
      if (parsedSummary.summary) {
        textToSpeak = parsedSummary.summary;
        // clean text, drop /n
        textToSpeak = textToSpeak.replace(/\n/g, ' ');
      }
    }
  } catch (error) {
    console.warn("Failed to parse summary as JSON");
  }

  if (!ELEVENLABS_API_KEY) {
    console.warn("No ElevenLabs API key found. Skipping TTS.");
    return;
  }

  try {
    // Truncate text to first 100 characters for ElevenLabs
    let textForSpeaking;
    if (config.isDebugMode) {
      textForSpeaking = textToSpeak.substring(0, 100);
    } else {
      textForSpeaking = textToSpeak
    }
    // Hit ElevenLabs TTS endpoint with the truncated text
    const headers = {
      "xi-api-key": ELEVENLABS_API_KEY,
      "Content-Type": "application/json",
      "Accept": "audio/mpeg"
    };

    const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        text: textForSpeaking,
        model_id: MODEL_ID,
      })
    });

    if (!response.ok) {
      throw new Error(`ElevenLabs TTS error: ${response.status}`);
    }

    // Convert response into a playable blob
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    // Play the audio, pause until finished
    return new Promise((resolve, reject) => {
      const audio = new Audio(audioUrl);
      audio.play().then(() => {
        audio.onended = () => {
          console.log("Speech completed successfully");
          resolve();
        };
      }).catch(err => {
        console.error("Audio playback error");
        // Make sure to clear the flag even if there's an error
        reject(err);
      });
    });

  } catch (err) {
    console.error("Failed to generate TTS from ElevenLabs");
    // Make sure to clear the flag if there's any exception
    throw err;
  }
}


