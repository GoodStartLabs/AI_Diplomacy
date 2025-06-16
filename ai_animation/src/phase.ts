import { gameState } from "./gameState";
import { logger } from "./logger";
import { updatePhaseDisplay, playBtn, prevBtn, nextBtn } from "./domElements";
import { initUnits } from "./units/create";
import { updateSupplyCenterOwnership, updateMapOwnership as _updateMapOwnership, updateMapOwnership } from "./map/state";
import { updateChatWindows, addToNewsBanner } from "./domElements/chatWindows";
import { createAnimationsForNextPhase } from "./units/animate";
import { speakSummary } from "./speech";
import { config } from "./config";
import { debugMenuInstance } from "./debug/debugMenu";
import { showTwoPowerConversation, closeTwoPowerConversation } from "./components/twoPowerConversation";
import { closeVictoryModal, showVictoryModal } from "./components/victoryModal";
import { notifyPhaseChange } from "./webhooks/phaseNotifier";
import { updateLeaderboard } from "./components/leaderboard";
import { updateRotatingDisplay } from "./components/rotatingDisplay";
import { startBackgroundAudio, stopBackgroundAudio } from "./backgroundAudio";

const MOMENT_THRESHOLD = 8.0
// If we're in debug mode or instant mode, show it quick, otherwise show it for 30 seconds
const MOMENT_DISPLAY_TIMEOUT_MS = config.isDebugMode ? 100 : config.momentDisplayTimeout

// FIXME: Going to previous phases is borked. Units do not animate properly, map doesn't update.
export function _setPhase(phaseIndex: number) {
  if (phaseIndex < 0) {
    throw new Error(`Provided invalid phaseIndex, cannot setPhase to ${phaseIndex} - game has ${gameState.gameData.phases.length} phases`)
  }
  if (phaseIndex >= gameState.gameData.phases.length - 1) {
    gameState.phaseIndex = gameState.gameData.phases.length - 1
    displayFinalPhase()
    return
  }

  // Store the old phase index at the very beginning
  const oldPhaseIndex = gameState.phaseIndex;

  if (config.isDebugMode) {
    debugMenuInstance.updateTools()
  }


  // Validate that the phaseIndex is within the bounds of the game length.
  if (phaseIndex - gameState.phaseIndex != 1) {
    // We're moving more than one Phase forward, or any number of phases backward, to do so clear the board and reInit the units on the correct phase
    gameState.unitAnimations = [];
    initUnits(phaseIndex)
    gameState.phaseIndex = phaseIndex
    displayPhase(true)
  } else {
    if (gameState.isPlaying) {
      gameState.eventQueue.start();
    }

    // Advance the phase index
    gameState.phaseIndex++;
    if (config.isDebugMode && gameState.gameData) {
      console.log(`Moving to phase ${gameState.gameData.phases[gameState.phaseIndex].name}`);
    }

    displayPhase()
  }

  // Finally, update the gameState with the current phaseIndex
  gameState.phaseIndex = phaseIndex

  // Send webhook notification for phase change
  notifyPhaseChange(oldPhaseIndex, phaseIndex);
}

// --- PLAYBACK CONTROLS ---
/**
 * Updates the gameState.isPlaying variable, toggling it from current position. Updates UI Elements to indicate current state.
 *
 * @param explicitSet - If you need to set the state to playing or not, use this with the bool of what you want the state to be.
 *
 */
export function togglePlayback(explicitSet: boolean | undefined = undefined) {
  // If the game doesn't have any data, or there are no phases, return;
  if (!gameState.gameData || gameState.gameData.phases.length <= 0) {
    alert("This game file appears to be broken. Please reload the page and load a different game.")
    throw Error("Bad gameState, exiting.")
  };

  // TODO: Likely not how we want to handle the speaking section of this. 
  //   Should be able to pause the other elements while we're speaking
  if (gameState.isSpeaking) return;

  gameState.isPlaying = !gameState.isPlaying;
  if (typeof explicitSet === "boolean") {
    gameState.isPlaying = explicitSet
  }

  if (gameState.isPlaying) {
    playBtn.textContent = "⏸ Pause";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    logger.log("Starting playback...");

    // Start background audio when playback starts
    startBackgroundAudio();

    // Start event queue for deterministic animations
    gameState.eventQueue.start();

    if (gameState.cameraPanAnim) gameState.cameraPanAnim.getAll()[1].start()

    // First, show the messages of the current phase if it's the initial playback
    if (gameState.currentPhase.messages && gameState.currentPhase.messages.length) {
      // Show messages with stepwise animation
      logger.log(`Playing ${gameState.currentPhase.messages.length} messages from phase ${gameState.phaseIndex + 1}/${gameState.gameData.phases.length}`);
      displayPhase()
    } else {
      // No messages, go straight to unit animations
      logger.log("No messages for this phase, proceeding to animations");
    }
  } else {
    if (gameState.cameraPanAnim) gameState.cameraPanAnim.getAll()[0].pause();
    playBtn.textContent = "▶ Play";
    // (playbackTimer is replaced by event queue system)

    // Stop background audio when pausing
    stopBackgroundAudio();

    // Ensure any open two-power conversations are closed when pausing
    closeTwoPowerConversation(true); // immediate = true

    // Stop and reset event queue when pausing with cleanup
    gameState.eventQueue.stop();
    gameState.eventQueue.reset(() => {
      // Ensure proper state cleanup when events are canceled
      gameState.messagesPlaying = false;
      gameState.isAnimating = false;
    });

    gameState.messagesPlaying = false;
    prevBtn.disabled = false;
    nextBtn.disabled = false;
  }
}


export function scheduleNextPhase() {
  gameState.eventQueue.scheduleDelay(0, nextPhase)
}

export function scheduleSummarySpeech() {
  // Delay speech in streaming mode
  gameState.eventQueue.scheduleDelay(config.speechDelay, () => {
    // Speak the summary and advance after
    speakSummary()
  }, `speech-delay-${Date.now()}`);
}

/** Handels all the end-of-phase items before calling _setPhase().
 *
 */
export function nextPhase() {
  let moment = gameState.checkPhaseHasMoment(gameState.gameData.phases[gameState.phaseIndex].name)
  if (moment !== null && moment.interest_score >= MOMENT_THRESHOLD && moment.powers_involved.length >= 2) {

    const power1 = moment.powers_involved[0];
    const power2 = moment.powers_involved[1];

    showTwoPowerConversation({
      power1: power1,
      power2: power2,
      moment: moment,
      onClose: () => {
        // Schedule the speaking of the summary after the conversation closes
        scheduleSummarySpeech();
        if (gameState.isPlaying) _setPhase(gameState.phaseIndex + 1)
      }
    })
  } else {
    // No conversation to show, proceed with normal flow
    scheduleSummarySpeech();
    _setPhase(gameState.phaseIndex + 1)
  }
}

export function previousPhase() {
  _setPhase(gameState.phaseIndex - 1)
}

/**
 * Unified function to display a phase with proper transitions
 * Handles both initial display and animated transitions between phases
 * @param skipMessages Whether to skip message animations (used for initial load)
 */
export function displayPhase(skipMessages = false) {
  let index = gameState.phaseIndex
  if (index >= gameState.gameData.phases.length) {
    // FIXME: Calling this here as well as in nextPhase is unneeded

    displayFinalPhase()
    logger.log("Displayed final phase.")
    return;
  }
  if (!gameState.gameData || !gameState.gameData.phases ||
    index < 0) {
    logger.log("Invalid phase index.");
    return;
  }

  // Handle the special case for the first phase (index 0)
  const isFirstPhase = index === 0;
  const currentPhase = gameState.gameData.phases[index];

  // Only get previous phase if not the first phase
  const prevIndex = isFirstPhase ? null : (index > 0 ? index - 1 : null);
  const previousPhase = prevIndex !== null ? gameState.gameData.phases[prevIndex] : null;


  // Update supply centers
  if (currentPhase.state?.centers) {
    updateSupplyCenterOwnership(currentPhase.state.centers);
  }


  // Update UI elements with smooth transitions
  updateRotatingDisplay(gameState.gameData, gameState.phaseIndex, gameState.currentPower, true);
  _updateMapOwnership();

  // Add phase info to news banner if not already there
  const phaseBannerText = `Phase: ${currentPhase.name}: ${currentPhase.summary}`;
  addToNewsBanner(phaseBannerText);

  // Log phase details to console only, don't update info panel with this
  const phaseInfo = `Phase: ${currentPhase.name}\nSCs: ${currentPhase.state?.centers ? JSON.stringify(currentPhase.state.centers) : 'None'}\nUnits: ${currentPhase.state?.units ? JSON.stringify(currentPhase.state.units) : 'None'}`;
  console.log(phaseInfo); // Use console.log instead of logger.log

  // Update leaderboard with power information
  updateLeaderboard();

  // Show messages with animation or immediately based on skipMessages flag
  updateChatWindows(true, scheduleNextPhase);

  // Only animate if not the first phase and animations are requested
  if (!isFirstPhase && !skipMessages) {
    if (previousPhase) {
      try {
        // Don't create animations immediately if messages are still playing
        // The main loop will handle this when messages finish
        createAnimationsForNextPhase();
      } catch (error) {
        console.warn(`Caught below error when attempting to create animations. Moving on without them.`)
        console.warn(error)
        initUnits(gameState.phaseIndex)

      }
    }
  } else {
    logger.log("No animations for this phase transition");
  }

}

/**
 * Display the initial phase without animations
 * Used when first loading a game
 */
export function displayInitialPhase() {
  initUnits(0);
  displayPhase(true);
}

/**
 * Display a phase with animations
 * Used during normal gameplay
 */
export function displayPhaseWithAnimation() {
  displayPhase(false);
}


function displayFinalPhase() {
  if (!gameState.gameData || !gameState.gameData.phases || gameState.gameData.phases.length === 0) {
    return;
  }

  // Get the final phase to determine the winner
  const finalPhase = gameState.gameData.phases[gameState.gameData.phases.length - 1];

  if (!finalPhase.state?.centers) {
    logger.log("No supply center data available to determine winner");
    return;
  }

  // Find the power with the most supply centers
  let winner = '';
  let maxCenters = 0;

  for (const [power, centers] of Object.entries(finalPhase.state.centers)) {
    const centerCount = Array.isArray(centers) ? centers.length : 0;
    if (centerCount > maxCenters) {
      maxCenters = centerCount;
      winner = power;
    }
  }

  // Display victory message
  if (winner && maxCenters > 0) {
    // Create final standings
    const finalStandings = Object.entries(finalPhase.state.centers)
      .map(([power, centers]) => ({
        power,
        centers: Array.isArray(centers) ? centers.length : 0
      }))
      .sort((a, b) => b.centers - a.centers);

    // Show victory modal
    showVictoryModal({
      winner,
      maxCenters,
      finalStandings,
    });
    gameState.eventQueue.scheduleDelay(config.victoryModalDisplayMs, () => {
      gameState.loadNextGame(true)
    }, `victory-modal-timeout-${Date.now()}`)

  } else {
    logger.log("Could not determine game winner");
  }
}
