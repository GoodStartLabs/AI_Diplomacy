import * as dotenv from 'dotenv';
import { OpenAI } from 'openai'; // Using the OpenAI SDK

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Configuration
const OPENAI_MODEL_NAME = process.env.AI_DIPLOMACY_NARRATIVE_MODEL || "gpt-3.5-turbo"; // Changed default
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  logger.warn("OPENAI_API_KEY not set – narrative summaries will be stubbed.");
}

// Placeholder for diplomacy Game and PhaseData types
// These would be imported from the actual 'diplomacy' library if a TS version exists
interface DiplomacyGame {
  _generate_phase_summary(phase_key: string, summary_callback?: any): string; // Original method signature
  get_phase_from_history(phase_key: string): DiplomacyPhaseData | null;
  // Assuming phase_summaries is a new property added by this module or elsewhere
  phase_summaries: Record<string, string>;
  // Other Game methods and properties...
}

interface DiplomacyPhaseData {
  summary: string; // Standard summary property
  statistical_summary?: string; // New property to store original summary
  // Other PhaseData properties...
}

let openaiClient: OpenAI | null = null;
if (OPENAI_API_KEY) {
  openaiClient = new OpenAI({ apiKey: OPENAI_API_KEY });
}

async function callOpenaiTs(statistical_summary: string, phase_key: string): Promise<string> {
  if (!openaiClient) {
    return "(Narrative generation disabled – missing API key or OpenAI client failed to initialize).";
  }

  const system_prompt =
    "You are an energetic e-sports commentator narrating a game of Diplomacy. " +
    "Turn the provided phase recap into a concise, thrilling story (max 4 sentences). " +
    "Highlight pivotal moves, supply-center swings, betrayals, and momentum shifts.";
  const user_prompt = `PHASE ${phase_key}\n\nSTATISTICAL SUMMARY:\n${statistical_summary}\n\nNow narrate this phase for spectators.`;

  try {
    const response = await openaiClient.chat.completions.create({
      model: OPENAI_MODEL_NAME,
      messages: [
        { role: "system", content: system_prompt },
        { role: "user", content: user_prompt },
      ],
    });
    if (response.choices && response.choices[0] && response.choices[0].message) {
      return response.choices[0].message.content?.trim() || "(Narrative generation returned empty content)";
    }
    return "(Narrative generation failed to produce a choice)";
  } catch (exc: any) {
    logger.error(`Narrative generation failed for phase ${phase_key}: ${exc.message}`, exc);
    return `(Narrative generation failed for phase ${phase_key})`;
  }
}

// Store the original _generate_phase_summary method
let original_generate_phase_summary: ((phase_key: string, summary_callback?: any) => string) | null = null;

// Patched function
async function patched_generate_phase_summary(this: DiplomacyGame, phase_key: string, summary_callback?: any): Promise<string> {
  if (!original_generate_phase_summary) {
    logger.error("Original _generate_phase_summary not found. Cannot generate narrative summary.");
    // Attempt to call 'super' or a non-patched version if available, or just return error.
    // This part is tricky without knowing the exact structure of the DiplomacyGame class.
    // For now, let's assume if original is not captured, we can't proceed.
    return "(Error: Original summary function not available for narrative patch)";
  }

  // 1) Call original implementation → statistical summary
  // Since the original is synchronous and this patched version is async due to callOpenaiTs,
  // we first get the statistical summary.
  const statistical: string = original_generate_phase_summary.call(this, phase_key, summary_callback);
  logger.debug(`[${phase_key}] Original summary returned: '${statistical}'`);

  // 2) Persist statistical summary separately
  let phase_data: DiplomacyPhaseData | null = null;
  try {
    phase_data = this.get_phase_from_history(phase_key.toString()); // Ensure phase_key is string
    if (phase_data) {
      phase_data.statistical_summary = statistical;
      logger.debug(`[${phase_key}] Assigning to phase_data.statistical_summary: '${statistical}'`);
    } else {
      logger.warn(`[${phase_key}] phase_data object not found for key ${phase_key}.`);
    }
  } catch (exc: any) {
    logger.warn(`Could not retrieve phase_data or store statistical_summary for ${phase_key}: ${exc.message}`);
  }

  // 3) Generate narrative summary
  const narrative = await callOpenaiTs(statistical, phase_key);

  // 4) Save narrative as the canonical summary
  try {
    if (phase_data) {
      phase_data.summary = narrative;
      if (!this.phase_summaries) { // Initialize if it doesn't exist
          this.phase_summaries = {};
      }
      this.phase_summaries[phase_key.toString()] = narrative;
      logger.debug(`[${phase_key}] Narrative summary stored successfully.`);
    } else {
      logger.warn(`[${phase_key}] Cannot store narrative summary because phase_data is None.`);
    }
  } catch (exc: any) {
    logger.warn(`Could not store narrative summary for ${phase_key}: ${exc.message}`);
  }

  return narrative; // The new summary is the narrative one
}

// Function to apply the patch
export function applyNarrativePatch(gameClass: any): void {
  if (gameClass && gameClass.prototype && gameClass.prototype._generate_phase_summary) {
    if (typeof gameClass.prototype._generate_phase_summary === 'function') {
        original_generate_phase_summary = gameClass.prototype._generate_phase_summary;
        gameClass.prototype._generate_phase_summary = patched_generate_phase_summary;
        logger.info("Game.prototype._generate_phase_summary patched with narrative generation.");
    } else {
        logger.error("Failed to apply narrative patch: _generate_phase_summary is not a function.");
    }
  } else {
    logger.error("Failed to apply narrative patch: Game class or _generate_phase_summary method not found or structured as expected.");
  }
}

// To use this, you would import applyNarrativePatch and the Diplomacy Game class
// in your main game setup file, and then call:
// import { Game as DiplomacyGameFromLib } from 'diplomacy'; // Hypothetical import
// import { applyNarrativePatch } from './narrative';
// applyNarrativePatch(DiplomacyGameFromLib);

// Note: The actual effectiveness of this monkey-patching depends on the structure
// and mutability of the 'diplomacy' library's Game class in its JS/TS form.
// This example assumes it's a class whose prototype can be modified.
// Also, the original method is synchronous, while the patched one is async.
// This changes the contract of _generate_phase_summary, which could have downstream effects
// if other parts of the system expect it to be synchronous.
// A more robust solution might involve a wrapper class or different integration pattern
// if the library doesn't lend itself well to this kind of patching or if async behavior is an issue.
